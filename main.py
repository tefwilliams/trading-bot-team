import time
import logging
import sqlite3
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from github_utils import GitHubManager
from state import AgentState
from nodes.researcher import researcher_node
from nodes.engineer import engineer_node
from nodes.strategy_reviewer import strategy_reviewer_node
from nodes.code_reviewer import code_reviewer_node
from nodes.performance_reviewer import performance_reviewer_node
from nodes.backtester import backtester_node

# Configure logging for professional visibility into agent actions
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_graph(checkpointer):
    """Builds the LangGraph workflow orchestration."""
    workflow = StateGraph(AgentState)

    # Add the nodes currently defined in the system
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("engineer", engineer_node)
    workflow.add_node("strategy_reviewer", strategy_reviewer_node)
    workflow.add_node("code_reviewer", code_reviewer_node)
    workflow.add_node("performance_reviewer", performance_reviewer_node)
    workflow.add_node("backtester", backtester_node)

    # Route to the correct node based on the current role in state
    workflow.add_conditional_edges(
        START,
        lambda state: state["current_role"],
        {
            "researcher": "researcher",
            "engineer": "engineer",
            "strategy_reviewer": "strategy_reviewer",
            "code_reviewer": "code_reviewer",
            "performance_reviewer": "performance_reviewer",
            "backtester": "backtester",
        },
    )

    workflow.add_edge("researcher", END)
    workflow.add_edge("engineer", END)
    workflow.add_edge("strategy_reviewer", END)
    workflow.add_edge("code_reviewer", END)
    workflow.add_edge("performance_reviewer", END)
    workflow.add_edge("backtester", END)

    return workflow.compile(checkpointer=checkpointer)


def run_orchestrator():
    """Main execution loop that polls GitHub for work."""
    github = GitHubManager()

    # Initialize SQLite connection for persistence
    conn = sqlite3.connect("checkpoints.sqlite", check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    app = create_graph(checkpointer)

    logger.info("🤖 Trading Bot Team is active and polling for GitHub issues...")

    while True:
        try:
            # Process each active role in a standardized loop.
            # `done` and `blocked` are terminal human-owned states (no node).
            roles = [
                "backtester",
                "researcher",
                "engineer",
                "code_reviewer",
                "performance_reviewer",
                "strategy_reviewer",
            ]

            for role in roles:
                tasks = github.get_status_issues(role)
                for issue in tasks:
                    logger.info(
                        f"Processing {role.upper()} Task: [#{issue.number}] {issue.title}"
                    )

                    initial_state = {
                        "issue_number": issue.number,
                        "messages": [f"System: Resuming session for {role}"],
                        "current_role": role,
                    }

                    # config establishes the thread persistence link
                    config = {"configurable": {"thread_id": str(issue.number)}}

                    try:
                        app.invoke(initial_state, config=config)
                        logger.info(f"Successfully processed issue #{issue.number}")
                        # Small breather for the API
                        time.sleep(1)
                    except Exception as e:
                        logger.error(f"Failed to process issue #{issue.number}: {e}")

        except Exception as e:
            logger.error(f"Error in orchestrator loop: {e}")

        # Poll every 15 seconds for a better feedback loop while staying within rate limits
        time.sleep(15)


if __name__ == "__main__":
    run_orchestrator()
