import subprocess
import tempfile
import os
import logging
import sys
import re
import ast
import json
from github_utils import GitHubManager
from state import AgentState

logger = logging.getLogger(__name__)

# Self-correction cap: after this many consecutive failed backtests the issue is
# escalated to a human (status:blocked) instead of looping back to the engineer.
MAX_BACKTEST_RETRIES = 3


def validate_interface(code: str) -> list[str]:
    """
    Uses static analysis to verify the strategy follows the required interface.
    Returns a list of error messages (empty if valid).
    """
    errors = []
    try:
        tree = ast.parse(code)
        functions = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        }

        # Check for generate_signals
        if "generate_signals" not in functions:
            errors.append("Missing required function: `generate_signals(data)`")
        else:
            sig = functions["generate_signals"]
            if len(sig.args.args) != 1:
                errors.append(
                    "`generate_signals` must accept exactly one argument: `data`"
                )

        # Check for run_backtest
        if "run_backtest" not in functions:
            errors.append("Missing required function: `run_backtest()`")
        else:
            sig = functions["run_backtest"]
            if len(sig.args.args) != 0:
                errors.append("`run_backtest` must accept no arguments.")

        # Check if run_backtest is actually called
        calls = [
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and hasattr(node.func, "id")
        ]
        if "run_backtest" not in calls:
            errors.append("The code defines `run_backtest` but never calls it.")

        # Check for results saving attempt
        if "BACKTEST_RESULTS_PATH" not in code:
            errors.append(
                "The code must use `os.environ['BACKTEST_RESULTS_PATH']` to save backtest metrics to a JSON file."
            )

    except SyntaxError as e:
        errors.append(f"Syntax Error in generated code: {e}")
    except Exception as e:
        errors.append(f"Interface validation failed with error: {str(e)}")

    return errors


def backtester_node(state: AgentState):
    """
    Automated node that extracts the strategy code, runs it, and reports results.
    This is a deterministic node, not an LLM.
    """
    github = GitHubManager()
    issue_number = state["issue_number"]
    retries = state.get("backtest_retries", 0) or 0

    pr = github.get_related_pr(issue_number)
    target_id = pr.number if pr else issue_number
    results_path = os.path.join(os.getcwd(), f"backtest_results_{issue_number}.json")

    def fail(report: str, log_msg: str):
        """Post the failure report and route back to the engineer, unless the
        self-correction retry cap is reached — then escalate to a human."""
        new_retries = retries + 1
        github.post_comment(target_id, report)

        if new_retries >= MAX_BACKTEST_RETRIES:
            github.post_comment(
                target_id,
                (
                    f"### 🚫 Self-Correction Limit Reached\n"
                    f"The Engineer ⇄ Backtester loop has failed **{new_retries}** times "
                    f"(cap: {MAX_BACKTEST_RETRIES}). Automatic retries are exhausted.\n\n"
                    f"This issue has been moved to `status:blocked` and will not be "
                    f"retried automatically. A human needs to investigate."
                ),
            )
            github.set_status(issue_number, "blocked")
            log_msg = f"{log_msg} — retry cap reached, escalated to status:blocked"
        else:
            github.set_status(issue_number, "engineer")

        return {"messages": [log_msg], "backtest_retries": new_retries}

    code = github.get_latest_code_block(issue_number)

    if not code:
        return fail(
            "### ❌ Backtest Failed\nCould not find a Python code block to execute in the PR or comments.",
            "Backtester failed: No code found",
        )

    # Step 1: Structural Validation
    interface_errors = validate_interface(code)
    if interface_errors:
        error_msg = "### ❌ Interface Validation Failed\n"
        error_msg += (
            "The generated code does not follow the required modular interface:\n\n"
        )
        for err in interface_errors:
            error_msg += f"- {err}\n"
        error_msg += "\n**Note to Engineer:** Please ensure your code includes the required `generate_signals` and `run_backtest` functions."

        return fail(error_msg, "Backtester failed interface validation")

    github.post_comment(
        target_id,
        "### ⚙️ Running Automated Backtest...\nExtracted code and executing in a sub-process.",
    )

    with tempfile.NamedTemporaryFile(
        suffix=".py", delete=False, mode="w", encoding="utf-8"
    ) as tmp:
        # Setup environment for headless/automated execution
        tmp.write("import matplotlib\nimport os\nmatplotlib.use('Agg')\n")
        # Disable yfinance persistent cache to avoid SQLite 'database is locked' errors
        tmp.write("import yfinance as yf\nimport tempfile\n")
        tmp.write(
            "try:\n    yf.set_tz_cache_location(tempfile.gettempdir())\nexcept Exception:\n    pass\n"
        )

        # Inject the unique results path into the script environment
        tmp.write(f"os.environ['BACKTEST_RESULTS_PATH'] = r'{results_path}'\n")
        tmp.write(code)

        tmp_path = tmp.name
    try:
        # Execute the code. Timeout after 120s to prevent hanging.
        result = subprocess.run(
            [sys.executable, tmp_path], capture_output=True, text=True, timeout=120
        )

        # Save the failing code to a local file for easier manual debugging
        if result.returncode != 0 or "Failed download" in result.stdout:
            debug_path = "debug_failed_strategy.py"
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(code)
            logger.info(
                f"Failing strategy code saved to {debug_path} for manual debugging."
            )

        # Detect runtime crashes
        if result.returncode != 0:
            error_report = "### ❌ Backtest Runtime Error\n"
            error_report += (
                f"The strategy script crashed with exit code {result.returncode}.\n\n"
            )
            error_report += f"**Standard Error:**\n```\n{result.stderr}\n```\n"
            error_report += f"**Standard Output:**\n```\n{result.stdout}\n```"
            return fail(
                error_report,
                f"Backtester failed: Runtime error in issue #{issue_number}",
            )

        # Detect silent yfinance download failures
        full_output = result.stdout + result.stderr
        if any(
            msg in full_output
            for msg in ["Failed download", "possibly delisted", "data not available"]
        ):
            error_report = "### ⚠️ Backtest Data Failure\nyfinance failed to download data for one or more tickers. This usually happens due to invalid date ranges for intraday data or delisted tickers.\n\n"
            if "15m data not available" in full_output:
                error_report += "**Specific Fix Required:** The request for 15m data failed because the range exceeds 60 days. You MUST switch to `interval='1d'` for this backtest window.\n\n"

            error_report += f"**Console Output:**\n```\n{result.stdout}\n```"
            return fail(
                error_report,
                f"Backtester failed: Data download failure in issue #{issue_number}",
            )

        # Parse metrics from the sidecar JSON file
        metrics_data = {}

        if os.path.exists(results_path):
            try:
                with open(results_path, "r") as f:
                    metrics_data = json.load(f)
                os.remove(results_path)  # Clean up
            except (json.JSONDecodeError, IOError) as e:
                logger.error(
                    f"Failed to read backtest_results.json for issue #{issue_number}: {e}"
                )

        # 1. Check if file was even created
        if not metrics_data:
            error_msg = "### ❌ Missing Backtest Results\n"
            error_msg += "The script executed but did not write to `BACKTEST_RESULTS_PATH`. You MUST include this at the end of your `run_backtest`:\n\n"
            error_msg += "```python\nimport json, os\nresults = {'total_return': float(ret), 'max_drawdown': float(dd), 'sharpe_ratio': float(sr), 'total_trades': int(len(trades))}\nwith open(os.environ['BACKTEST_RESULTS_PATH'], 'w') as f:\n    json.dump(results, f)\n```"
            return fail(
                error_msg,
                f"Backtester failed: No JSON output for issue #{issue_number}",
            )

        # 2. Check for zero-signal strategies
        total_trades = metrics_data.get("total_trades", 0)
        if total_trades == 0:
            error_msg = "### ⚠️ Strategy Inactive\nThe backtest finished with **0 trades**.\n\n**Action Required:** Please simplify entry logic or check if indicators have enough warm-up data."
            return fail(
                error_msg,
                f"Backtester: Zero trades detected for issue #{issue_number}",
            )

        # 3. Success: Parse and report metrics
        display_metrics = {
            "Total Return": (
                f"{metrics_data.get('total_return', 0) * 100:.2f}%"
                if "total_return" in metrics_data
                else "N/A"
            ),
            "Max Drawdown": (
                f"{metrics_data.get('max_drawdown', 0) * 100:.2f}%"
                if "max_drawdown" in metrics_data
                else "N/A"
            ),
            "Sharpe Ratio": (
                f"{metrics_data.get('sharpe_ratio', 0):.2f}"
                if "sharpe_ratio" in metrics_data
                else "N/A"
            ),
        }

        report = "### 📊 Backtest Execution Report\n\n"
        report += "| Metric | Value |\n| :--- | :--- |\n"
        for label, val in display_metrics.items():
            if val == "N/A":
                logger.warning(
                    f"Metric {label} missing from JSON output for issue #{issue_number}"
                )
            report += f"| {label} | **{val}** |\n"

        if result.stdout:
            report += f"\n<details>\n<summary>View Full Console Output</summary>\n\n```\n{result.stdout}\n```\n</details>\n"
        if result.stderr:
            report += f"\n#### ⚠️ Standard Error/Warnings\n```\n{result.stderr}\n```"

        github.post_comment(target_id, report)

        # Self-Correction Success: Transition to Reviewer for qualitative analysis.
        # Reset the retry counter so the next correction loop (if any) starts fresh.
        github.set_status(issue_number, "reviewer")
        return {
            "messages": [f"Backtester executed code for issue #{issue_number}"],
            "backtest_metrics": metrics_data,
            "backtest_retries": 0,
        }

    except subprocess.TimeoutExpired:
        return fail(
            "### ❌ Backtest Timed Out\nThe strategy execution exceeded the 120s limit.",
            f"Backtester failed: Timeout in issue #{issue_number}",
        )
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
