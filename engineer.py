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

    # Fetch conversation history so the engineer can see the strategy proposal and feedback
    comments = list(issue.get_comments())
    thread_context = "\n\n".join(
        [f"--- Comment from {c.user.login} ---\n{c.body}" for c in comments]
    )

    prompt = f"""
    You are an expert Quantitative Software Engineer. Your task is to implement the following trading strategy spec into a runnable Python script.
    
    STRATEGY SPECIFICATION & CONTEXT:
    Title: {issue.title}
    Original Objective: {issue.body}

    CONVERSATION HISTORY (Contains the Strategy Proposal and Reviewer Feedback):
    {thread_context}
    
    REQUIREMENTS:
    1. Use `yfinance` to fetch historical data for the specified universe.
    2. Use `pandas` for data manipulation and signal generation.
    3. Implement the Entry and Exit rules exactly as described.
    4. Implement the Position Sizing logic.
    5. Include a backtesting loop that calculates performance metrics: Total Return, Max Drawdown, and Sharpe Ratio.
    6. Ensure the code is clean, commented, and standalone.
    7. Use vectorized operations where possible for performance.
    
    IMPORTANT: Save the strategy to `strategies/strategy_{state["issue_number"]}.py`.
    IMPORTANT: If there is previous feedback or a rejected implementation in the history, you MUST address the specific critiques and fix the bugs identified.

    Output ONLY the Python code inside a markdown block.
    """

    # The thinking model will generate the reasoning logic before the final code block
    response = llm.invoke(prompt)
    content = response.content
    if isinstance(content, list):
        content = "\n".join(
            [part["text"] for part in content if part["type"] == "text"]
        )

    # Extract code and create a Pull Request
    clean_code = github.extract_code(content)
    branch_name = f"strat/issue-{state['issue_number']}"
    github.ensure_branch(branch_name)

    file_path = f"strategies/strategy_{state['issue_number']}.py"
    github.create_or_update_file(
        file_path,
        f"Implement strategy for issue #{state['issue_number']}",
        clean_code,
        branch_name,
    )

    pr = github.create_pull_request(
        title=f"Strategy: {issue.title}",
        body=f"This PR implements the strategy described in issue #{state['issue_number']}.\n\nCloses #{state['issue_number']}",
        head=branch_name,
    )

    # Post the implementation as a structured comment
    comment_body = (
        f"### 🤖 Engineer implementation generated\n\n"
        f"I have implemented the code in branch `{branch_name}` and opened a Pull Request: {pr.html_url}\n\n"
        f"**Implementation Details:**\n{content}\n"
    )
    github.post_comment(state["issue_number"], comment_body)

    # Transition the ticket: Engineer -> Reviewer for AI code review
    github.transition_role(state["issue_number"], "reviewer", "stage:review")

    return {
        "messages": [
            f"Engineer generated implementation for issue #{state['issue_number']}"
        ]
    }
