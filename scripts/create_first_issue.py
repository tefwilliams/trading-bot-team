import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from github_utils import GitHubManager


def create_initial_issue():
    github = GitHubManager()

    title = "Adaptive RSI Mean Reversion (ARMR) for QQQ"

    body = """
## Strategy Objective
Exploit short-term overextended conditions in the NASDAQ-100 (QQQ) by identifying high-probability mean reversion points that align with the long-term trend.

## Hypothesis
Mean reversion strategies in equities have a higher win rate when trading in the direction of the primary trend. By using an extremely sensitive RSI (RSI-2) to identify "rubber band" stretches, we can capture quick pullbacks.

## Initial Constraints
- **Universe:** QQQ (NASDAQ-100 ETF)
- **Timeframe:** Daily (1d)
- **Regime Filter:** Price must be above its 200-day Simple Moving Average (SMA200).
- **Entry:** RSI(2) falls below 10 (Deep Oversold).
- **Exit:** RSI(2) rises above 70 or a 5-day time-based stop is reached.
- **Position Sizing:** 100% equity for initial testing.

**Role/Stage:** Please transition this to the `researcher` to formalize the specification.
"""

    labels = ["status:researcher", "type:strategy"]
    issue = github.create_issue(title, body, labels)
    print(f"✅ Issue #{issue.number} created: {issue.html_url}")


if __name__ == "__main__":
    create_initial_issue()
