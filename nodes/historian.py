import pandas as pd
import os
import re
from github_utils import GitHubManager
from state import AgentState


def historian_node(state: AgentState):
    """
    Logs the final approved backtest results into a central manifest.
    This helps the Manager see all integrated strategies in one view.
    """
    github = GitHubManager()
    issue_number = state["issue_number"]
    issue = github.get_issue(issue_number)

    # Retrieve structured metrics from state
    metrics_data = state.get("backtest_metrics") or {}

    total_return = (
        f"{metrics_data.get('total_return', 0) * 100:.2f}%"
        if "total_return" in metrics_data
        else "N/A"
    )
    max_drawdown = (
        f"{metrics_data.get('max_drawdown', 0) * 100:.2f}%"
        if "max_drawdown" in metrics_data
        else "N/A"
    )
    sharpe_ratio = (
        f"{metrics_data.get('sharpe_ratio', 0):.2f}"
        if "sharpe_ratio" in metrics_data
        else "N/A"
    )

    manifest_path = "strategies/performance_manifest.csv"
    new_entry = {
        "issue": issue_number,
        "date": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "title": issue.title,
        "return": total_return,
        "mdd": max_drawdown,
        "sharpe": sharpe_ratio,
        "status": "Integrated",
        "path": f"strategies/strategy_{issue_number}.py",
        "pr": (
            github.get_related_pr(issue_number).html_url
            if github.get_related_pr(issue_number)
            else "N/A"
        ),
    }

    # Simple local CSV management for now
    if os.path.exists(manifest_path):
        df = pd.read_csv(manifest_path)
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    else:
        df = pd.DataFrame([new_entry])

    df.to_csv(manifest_path, index=False)

    github.post_comment(
        issue_number,
        f"### 📝 Historian Logged\nStrategy metrics ({sharpe_ratio} Sharpe) have been archived to the performance manifest.",
    )

    # Final transition to Manager for PR merge
    github.set_status(issue_number, "manager")

    return {"messages": [f"Historian logged performance for issue #{issue_number}"]}
