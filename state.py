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
