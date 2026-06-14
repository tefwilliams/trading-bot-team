from llm import get_llm, load_prompt
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

    template = load_prompt("reviewer.md")
    prompt = template.format(
        title=issue.title, body=issue.body, thread_context=thread_context
    )

    response = llm.invoke(prompt)
    content = response.content
    if isinstance(content, list):
        content = "\n".join(
            [part["text"] for part in content if part["type"] == "text"]
        )

    is_researcher_fail = "[RESEARCHER]" in content.upper()

    # Post the critique. If it's a failed strategy, ensure it's on the main issue for the Researcher.
    # Otherwise, post to the PR if one exists.
    target_id = state["issue_number"] if is_researcher_fail or not pr else pr.number
    github.post_comment(target_id, f"### 🧐 Reviewer Feedback\n\n{content}")

    # Determine routing based on the decision and the current content
    if "[APPROVED]" in content.upper():
        labels = [l.name for l in issue.get_labels()]
        if "status:reviewer" in labels and pr:
            next_role = "risk_manager"
        else:
            next_role = "engineer"

        github.set_status(state["issue_number"], next_role)
    else:
        # Determine if we blame the Engineer (bad code) or Researcher (bad strategy)
        if is_researcher_fail:
            next_role = "researcher"
        else:
            next_role = "engineer" if "```python" in thread_context else "researcher"

        github.set_status(state["issue_number"], next_role)

    return {
        "messages": [
            f"Reviewer processed issue #{state['issue_number']}. Decision posted."
        ]
    }
