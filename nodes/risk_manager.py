from llm import get_llm, load_prompt
from github_utils import GitHubManager
from state import AgentState


def risk_manager_node(state: AgentState):
    """
    Evaluates the strategy and code specifically for risk-management failures.
    """
    # We use the 'reviewer' profile to get temperature=0 for consistency
    llm = get_llm(
        "risk_manager",
        system_instruction="You are a Professional Risk Manager. Your job is NOT to see if the strategy makes money, but to see if it will lose money safely.",
    )
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

    template = load_prompt("risk_manager.md")
    prompt = template.format(thread_context=thread_context)

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
