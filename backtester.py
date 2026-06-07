import subprocess
import tempfile
import os
import logging
import sys
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
        tmp.write(code)
        tmp_path = tmp.name

    try:
        # Execute the code. Timeout after 120s to prevent hanging.
        result = subprocess.run(
            [sys.executable, tmp_path], capture_output=True, text=True, timeout=120
        )

        report = "### 📊 Backtest Results\n\n"
        if result.stdout:
            report += f"**Output:**\n```\n{result.stdout}\n```\n"
        if result.stderr:
            report += f"**Errors/Warnings:**\n```\n{result.stderr}\n```"

        github.post_comment(issue_number, report)

        # Successful run: Hand over to Product Manager for final synthesis
        github.transition_role(issue_number, "product_manager", "stage:final-review")

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
