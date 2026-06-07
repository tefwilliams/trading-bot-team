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

    # Parse metrics from the backtester's comment
    comments = list(issue.get_comments())
    metrics = {"Total Return": "N/A", "Max Drawdown": "N/A", "Sharpe Ratio": "N/A"}

    for comment in reversed(comments):
        if "### 📊 Backtest Execution Report" in comment.body:
            # Extract values from the markdown table
            for key in metrics.keys():
                match = re.search(rf"\| {key} \| \*\*(.*?)\*\* \|", comment.body)
                if match:
                    metrics[key] = match.group(1)
            break

    manifest_path = "strategies/performance_manifest.csv"
    new_entry = {
        "issue": issue_number,
        "date": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "title": issue.title,
        "return": metrics["Total Return"],
        "mdd": metrics["Max Drawdown"],
        "sharpe": metrics["Sharpe Ratio"],
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
        f"### 📝 Historian Logged\nStrategy metrics ({metrics['Sharpe Ratio']} Sharpe) have been archived to the performance manifest.",
    )

    return {"messages": [f"Historian logged performance for issue #{issue_number}"]}
