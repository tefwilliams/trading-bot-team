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
    1. **CRITICAL DATA ACCESS**: Use `yfinance` to fetch historical data using explicit `start` and `end` dates.
       - You MUST explicitly set `interval='1d'` in the `yf.download()` call.
       - DO NOT use intraday intervals (1m, 5m, 15m, 60m) as they will fail for any backtest period longer than 60 days.
       - If the user asks for "intraday" or "15m", politely explain that we are restricted to Daily data for now and implement using `1d`.
    2. Use `pandas` for data manipulation and signal generation.
    3. Implement the Entry and Exit rules exactly as described.
    4. Implement the Position Sizing logic.
    5. **INTERFACE REQUIREMENT**: The code must be modular for a multi-strategy engine.
       - Provide a `generate_signals(data: pd.DataFrame) -> pd.Series` function.
       - This function must return a Series of signals (1 for Long, 0 for Flat, -1 for Short) indexed by timestamp.
       - All indicator calculations (RSI, SMA, etc.) must be contained or called within this function.
       - Provide a `run_backtest()` function (with no arguments) that loads data and calls `generate_signals`.
    6. Include a backtesting loop that calculates performance metrics: Total Return, Max Drawdown, and Sharpe Ratio.
    7. Ensure the code is clean, commented, and standalone.
    8. **ROBUST DATA HANDLING**: You MUST verify that the downloaded DataFrame is not None and not empty (`df is not None and not df.empty`) before calculating indicators or running the backtest loop. If data is missing, the script should print a clear error and exit gracefully rather than crashing.
    9. Use vectorized operations where possible for performance.
    
    IMPORTANT: Save the strategy to `strategies/strategy_{state["issue_number"]}.py`.
    IMPORTANT: If there is previous feedback or a rejected implementation in the history, you MUST address the specific critiques and fix the bugs identified.
    IMPORTANT: Your code will be automatically validated for structural integrity (AST) and executed in a sandbox. Ensure strict compliance with function signatures.

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
