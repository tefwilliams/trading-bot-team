from typing import TypedDict, Annotated, List, Optional, Dict, Any
from operator import add


class AgentState(TypedDict):
    # The GitHub issue number we are currently processing
    issue_number: int
    # History of thoughts and internal dialogue
    messages: Annotated[List[str], add]
    # The current role acting on the state
    current_role: str
    # Structured metrics from the backtester
    backtest_metrics: Optional[Dict[str, Any]]
    # Consecutive backtest failures, used to enforce the self-correction retry cap.
    # Reset to 0 on a successful backtest; when it hits MAX_BACKTEST_RETRIES the
    # issue is escalated to a human (status:blocked).
    backtest_retries: int
    # Cumulative reviewer rejections, used to bound the Engineer/Researcher <-> Reviewer
    # loop. Reset to 0 on an approval; when it hits MAX_REVIEW_REJECTIONS the issue is
    # escalated to a human (status:blocked).
    review_rejections: int
