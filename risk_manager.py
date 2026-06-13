from llm import get_llm
from github_utils import GitHubManager
from state import AgentState


def risk_manager_node(state: AgentState):
    """
    Evaluates the strategy and code specifically for risk-management failures.
    """
    llm = get_llm("reviewer")  # Uses the stable Pro model
    github = GitHubManager()
    issue = github.get_issue(state["issue_number"])

    comments = list(issue.get_comments())
    thread_context = "\n\n".join(
        [f"--- {c.user.login} ---\n{c.body}" for c in comments]
    )

    # Fetch PR context for code-level risk assessment
    pr = github.get_related_pr(state["issue_number"])
    if pr:
        diff, reviews = github.get_pr_context(pr.number)
        thread_context += f"\n\n--- PULL REQUEST DIFF (#{pr.number}) ---\n{diff}\n\n--- PR REVIEW COMMENTS ---\n{reviews}"

    prompt = f"""
    You are a Professional Risk Manager. Your job is NOT to see if the strategy makes money, 
    but to see if it will lose money safely.

    REVIEW CRITERIA:
    1. Position Sizing: Is it defined? Is it too aggressive?
    2. Stop Losses: Does the code/spec include a hard exit to prevent ruin?
    3. Slippage/Liquidity: Does the strategy assume it can trade unlimited volume at mid-price?
    4. Overfitting: Does the logic seem too specific to past data?

    CONTEXT:
    {thread_context}

    Provide a 'RISK ASSESSMENT': [SAFE] or [UNSAFE].
    If UNSAFE, list the specific risk violations.
    """

    response = llm.invoke(prompt)
    content = response.content
    if isinstance(content, list):
        content = "\n".join(
            [part["text"] for part in content if part["type"] == "text"]
        )

    github.post_comment(
        state["issue_number"], f"### 🛡️ Risk Manager Assessment\n\n{content}"
    )

    if "[SAFE]" in content.upper():
        # Approval: Performance was already validated, move to Historian for final logging
        github.set_status(state["issue_number"], "historian")
    else:
        # Back to the Engineer or Researcher
        is_code = "```python" in thread_context
        next_role = "engineer" if is_code else "researcher"
        github.set_status(state["issue_number"], next_role)

    return {"messages": [f"Risk Manager evaluated issue #{state['issue_number']}"]}
