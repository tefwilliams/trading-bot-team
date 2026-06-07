from llm import get_llm
from github_utils import GitHubManager
from state import AgentState


def engineer_node(state: AgentState):
    """
    Translates an approved trading strategy into runnable Python code.
    """
    llm = get_llm("engineer")
    github = GitHubManager()

    issue = github.get_issue(state["issue_number"])

    prompt = f"""
    You are an expert Quantitative Software Engineer. Your task is to implement the following trading strategy spec into a runnable Python script.
    
    STRATEGY SPECIFICATION:
    Title: {issue.title}
    Details: {issue.body}
    
    REQUIREMENTS:
    1. Use `yfinance` to fetch historical data for the specified universe.
    2. Use `pandas` for data manipulation and signal generation.
    3. Implement the Entry and Exit rules exactly as described.
    4. Implement the Position Sizing logic.
    5. Include a backtesting loop that calculates performance metrics: Total Return, Max Drawdown, and Sharpe Ratio.
    6. Ensure the code is clean, commented, and standalone.
    
    Output ONLY the Python code inside a markdown block.
    """

    # The thinking model will generate the reasoning logic before the final code block
    response = llm.invoke(prompt)

    # Post the implementation as a structured comment
    comment_body = (
        f"### 🤖 Engineer implementation generated\n\n"
        f"I have translated the strategy specification into code:\n\n"
        f"{response.content}\n\n"
        f"**Next Steps:** This implementation is ready for review and backtest validation."
    )
    github.post_comment(state["issue_number"], comment_body)

    # Transition the ticket: Engineer -> Reviewer
    github.update_labels(
        state["issue_number"],
        add=["role:reviewer", "stage:review"],
        remove=["role:engineer", "stage:implementation"],
    )

    return {
        "messages": [
            f"Engineer generated implementation for issue #{state['issue_number']}"
        ]
    }
