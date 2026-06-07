import time
import logging
from langgraph.graph import StateGraph, START, END
from github_utils import GitHubManager
from state import AgentState
from researcher import researcher_node
from engineer import engineer_node
from reviewer import reviewer_node
from risk_manager import risk_manager_node

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

    # Route to the correct node based on the current role in state
    workflow.add_conditional_edges(
        START,
        lambda state: state["current_role"],
        {
            "researcher": "researcher",
            "engineer": "engineer",
            "reviewer": "reviewer",
            "risk_manager": "risk_manager",
        },
    )

    workflow.add_edge("researcher", END)
    workflow.add_edge("engineer", END)
    workflow.add_edge("reviewer", END)
    workflow.add_edge("risk_manager", END)

    return workflow.compile()


def run_orchestrator():
    """Main execution loop that polls GitHub for work."""
    github = GitHubManager()
    app = create_graph()

    logger.info("🤖 Trading Bot Team is active and polling for GitHub issues...")

    while True:
        try:
            # Fetch issues that need attention from the Researcher
            researcher_tasks = github.get_role_issues("researcher")
            engineer_tasks = github.get_role_issues("engineer")
            reviewer_tasks = github.get_role_issues("reviewer")
            risk_tasks = github.get_role_issues("risk_manager")

            for issue in researcher_tasks:
                logger.info(f"Processing Task: [#{issue.number}] {issue.title}")

                # Prepare the initial state for LangGraph
                initial_state = {
                    "issue_number": issue.number,
                    "messages": [
                        f"System: Commencing workflow for issue #{issue.number}"
                    ],
                    "current_role": "researcher",
                }

                # Execute the graph
                app.invoke(initial_state)
                logger.info(f"Successfully processed issue #{issue.number}")

            for issue in engineer_tasks:
                logger.info(
                    f"Processing Engineering Task: [#{issue.number}] {issue.title}"
                )

                initial_state = {
                    "issue_number": issue.number,
                    "messages": [
                        f"System: Commencing engineering workflow for issue #{issue.number}"
                    ],
                    "current_role": "engineer",
                }

                app.invoke(initial_state)
                logger.info(f"Successfully processed engineering issue #{issue.number}")

            for issue in reviewer_tasks:
                logger.info(f"Processing Review Task: [#{issue.number}] {issue.title}")

                initial_state = {
                    "issue_number": issue.number,
                    "messages": [
                        f"System: Commencing review workflow for issue #{issue.number}"
                    ],
                    "current_role": "reviewer",
                }

                app.invoke(initial_state)
                logger.info(f"Successfully processed review issue #{issue.number}")

            for issue in risk_tasks:
                logger.info(f"Processing Risk Task: [#{issue.number}] {issue.title}")

                initial_state = {
                    "issue_number": issue.number,
                    "messages": [
                        f"System: Commencing risk review for issue #{issue.number}"
                    ],
                    "current_role": "risk_manager",
                }

                app.invoke(initial_state)
                logger.info(f"Successfully processed risk issue #{issue.number}")

        except Exception as e:
            logger.error(f"Error in orchestrator loop: {e}")

        # Poll every minute to stay within GitHub API rate limits
        time.sleep(60)


if __name__ == "__main__":
    run_orchestrator()
