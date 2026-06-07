import subprocess
import tempfile
import os
import logging
import sys
import re
from github_utils import GitHubManager
from state import AgentState

logger = logging.getLogger(__name__)


def backtester_node(state: AgentState):
    """
    Automated node that extracts the strategy code, runs it, and reports results.
    This is a deterministic node, not an LLM.
    """
    github = GitHubManager()
    issue_number = state["issue_number"]

    code = github.get_latest_code_block(issue_number)

    if not code:
        github.post_comment(
            issue_number,
            "### ❌ Backtest Failed\nCould not find a Python code block to execute.",
        )
        github.transition_role(issue_number, "engineer", "stage:implementation")
        return {"messages": ["Backtester failed: No code found"]}

    github.post_comment(
        issue_number,
        "### ⚙️ Running Automated Backtest...\nExtracted code and executing in a sub-process.",
    )

    with tempfile.NamedTemporaryFile(
        suffix=".py", delete=False, mode="w", encoding="utf-8"
    ) as tmp:
        # Setup environment for headless/automated execution
        tmp.write("import matplotlib\nmatplotlib.use('Agg')\n")
        # Disable yfinance persistent cache to avoid SQLite 'database is locked' errors
        tmp.write("import yfinance as yf\n")
        tmp.write(
            "try:\n    yf.set_tz_cache_location(None)\nexcept Exception:\n    pass\n"
        )

        tmp.write(code)
        tmp_path = tmp.name

    try:
        # Execute the code. Timeout after 120s to prevent hanging.
        result = subprocess.run(
            [sys.executable, tmp_path], capture_output=True, text=True, timeout=120
        )

        # Parse metrics from stdout using regex
        metrics = {
            "Total Return": re.search(r"Total Return:\s+([\d\.-]+%)", result.stdout),
            "Max Drawdown": re.search(r"Max Drawdown:\s+([\d\.-]+%)", result.stdout),
            "Sharpe Ratio": re.search(r"Sharpe Ratio:\s+([\d\.-]+)", result.stdout),
        }

        report = "### 📊 Backtest Execution Report\n\n"
        report += "| Metric | Value |\n| :--- | :--- |\n"
        for label, match in metrics.items():
            val = match.group(1) if match else "Not Found"
            report += f"| {label} | **{val}** |\n"

        if result.stdout:
            report += f"\n<details>\n<summary>View Full Console Output</summary>\n\n```\n{result.stdout}\n```\n</details>\n"
        if result.stderr:
            report += f"\n#### ⚠️ Standard Error/Warnings\n```\n{result.stderr}\n```"

        github.post_comment(issue_number, report)

        # Transition to Manager for final sign-off and PR merge
        github.transition_role(issue_number, "manager", "stage:review")

    except subprocess.TimeoutExpired:
        github.post_comment(
            issue_number,
            "### ❌ Backtest Timed Out\nThe strategy execution exceeded the 120s limit.",
        )
        github.transition_role(issue_number, "engineer", "stage:implementation")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return {"messages": [f"Backtester executed code for issue #{issue_number}"]}
