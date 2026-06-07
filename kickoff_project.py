from github_utils import GitHubManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def kickoff_first_strategy():
    github = GitHubManager()

    title = "[STRAT] RSI Mean Reversion for NASDAQ-100"
    body = (
        "## Objective\n"
        "Develop a robust mean reversion strategy targeting highly liquid tech stocks (e.g., QQQ components).\n\n"
        "## Details\n"
        "The strategy should identify short-term overbought/oversold conditions using RSI. "
        "I am interested in seeing how it handles regime detection to avoid 'catching a falling knife' during strong trends."
    )
    labels = ["role:researcher", "stage:proposal", "type:strategy"]

    issue = github.create_issue(title, body, labels)
    logger.info(f"🚀 Project kicked off! First issue created at: {issue.html_url}")


if __name__ == "__main__":
    kickoff_first_strategy()
