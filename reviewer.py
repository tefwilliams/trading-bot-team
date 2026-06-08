from llm import get_llm
from github_utils import GitHubManager
from state import AgentState


def reviewer_node(state: AgentState):
    """
    Critiques the current state of the strategy (spec or code) and decides
    whether to approve or request changes.
    """
    llm = get_llm("reviewer")
    github = GitHubManager()
    issue = github.get_issue(state["issue_number"])

    # Get all comments to see what the Researcher or Engineer posted
    comments = list(issue.get_comments())
    thread_context = "\n\n".join(
        [f"--- Comment by {c.user.login} ---\n{c.body}" for c in comments]
    )

    # Fetch PR context if an implementation exists
    pr = github.get_related_pr(state["issue_number"])
    if pr:
        diff, reviews = github.get_pr_context(pr.number)
        thread_context += f"\n\n--- PULL REQUEST DIFF (#{pr.number}) ---\n{diff}\n\n--- PR REVIEW COMMENTS ---\n{reviews}"

    prompt = f"""
    You are a Senior Quantitative Reviewer. Your goal is to ensure quality and rigor.
    You are reviewing a task in a trading bot development pipeline.

    ISSUE OVERVIEW:
    Title: {issue.title}
    Original Objective: {issue.body}

    CONVERSATION HISTORY:
    {thread_context}

    YOUR TASK:
    1. Determine if you are reviewing a "Strategy Specification" (from Researcher) or "Python Code" (from Engineer).
    2. Critique the work for:
       - Strategy: Logical flaws, look-ahead bias, unrealistic assumptions, or vague rules.
       - Code/PR: Review the implementation (linked PR if available). Check for syntax errors, inefficient pandas usage, missing risk metrics (Sharpe, Drawdown), or divergence from the spec.
    3. Provide a clear 'DECISION': [APPROVED] or [REJECTED].
    4. Aim for progress. If a strategy is 90% there and the flaws are minor, provide suggestions but consider [APPROVED].

    If REJECTED, specify exactly what needs to be fixed.
    If APPROVED, provide a brief summary of why it's ready for the next stage.
    """

    response = llm.invoke(prompt)
    content = response.content
    if isinstance(content, list):
        content = "\n".join(
            [part["text"] for part in content if part["type"] == "text"]
        )

    # Post the critique to GitHub
    github.post_comment(state["issue_number"], f"### 🧐 Reviewer Feedback\n\n{content}")

    # Determine routing based on the decision and the current content
    if "[APPROVED]" in content.upper():
        # If we approved a spec, it goes to Engineer. If we approved code, it goes to Backtest/Manager.
        is_code = (
            pr is not None or "```python" in thread_context or "```python" in content
        )
        next_role = "risk_manager" if is_code else "engineer"
        next_stage = "stage:review" if is_code else "stage:approved-spec"

        github.transition_role(state["issue_number"], next_role, next_stage)
    else:
        # Rejected: Kick back to whoever did the work
        # We check the thread to see who to blame
        is_code = "```python" in thread_context
        next_role = "engineer" if is_code else "researcher"
        next_stage = "stage:implementation" if is_code else "stage:proposal"
        github.transition_role(state["issue_number"], next_role, next_stage)

    return {
        "messages": [
            f"Reviewer processed issue #{state['issue_number']}. Decision posted."
        ]
    }
