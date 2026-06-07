import time
import logging
from langgraph.graph import StateGraph, START, END
from github_utils import GitHubManager
from state import AgentState
from researcher import researcher_node
from engineer import engineer_node
from reviewer import reviewer_node
from risk_manager import risk_manager_node
from product_manager import product_manager_node
from backtester import backtester_node

# Configure logging for professional visibility into agent actions
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_graph():
    """Builds the LangGraph workflow orchestration."""
    workflow = StateGraph(AgentState)

    # Add the nodes currently defined in the system
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("engineer", engineer_node)
    workflow.add_node("reviewer", reviewer_node)
    workflow.add_node("risk_manager", risk_manager_node)
    workflow.add_node("product_manager", product_manager_node)
    workflow.add_node("backtester", backtester_node)

    # Route to the correct node based on the current role in state
    workflow.add_conditional_edges(
        START,
        lambda state: state["current_role"],
        {
            "researcher": "researcher",
            "engineer": "engineer",
            "reviewer": "reviewer",
            "risk_manager": "risk_manager",
            "product_manager": "product_manager",
            "backtester": "backtester",
        },
    )

    workflow.add_edge("researcher", END)
    workflow.add_edge("engineer", END)
    workflow.add_edge("reviewer", END)
    workflow.add_edge("risk_manager", END)
    workflow.add_edge("product_manager", END)
    workflow.add_edge("backtester", END)

    return workflow.compile()


def run_orchestrator():
    """Main execution loop that polls GitHub for work."""
    github = GitHubManager()
    app = create_graph()

    logger.info("🤖 Trading Bot Team is active and polling for GitHub issues...")

    while True:
        try:
            # Process each role in a standardized loop
            roles = [
                "product_manager",
                "backtester",
                "researcher",
                "engineer",
                "reviewer",
                "risk_manager",
            ]

            for role in roles:
                tasks = github.get_role_issues(role)
                for issue in tasks:
                    logger.info(
                        f"Processing {role.upper()} Task: [#{issue.number}] {issue.title}"
                    )

                    initial_state = {
                        "issue_number": issue.number,
                        "messages": [f"System: Starting node for {role}"],
                        "current_role": role,
                    }

                    try:
                        app.invoke(initial_state)
                        logger.info(f"Successfully processed issue #{issue.number}")
                        # Small breather for the API
                        time.sleep(1)
                    except Exception as e:
                        logger.error(f"Failed to process issue #{issue.number}: {e}")

        except Exception as e:
            logger.error(f"Error in orchestrator loop: {e}")

        # Poll every minute to stay within GitHub API rate limits
        time.sleep(60)


if __name__ == "__main__":
    run_orchestrator()
