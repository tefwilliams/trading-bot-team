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

    # Post the critique to the PR if it exists, otherwise the Issue
    target_id = pr.number if pr else state["issue_number"]
    github.post_comment(target_id, f"### 🧐 Reviewer Feedback\n\n{content}")

    # Determine routing based on the decision and the current content
    if "[APPROVED]" in content.upper():
        # Check current label to determine if we are moving from Spec -> Implementation
        # or from Backtest -> Risk/Manager
        labels = [l.name for l in issue.get_labels()]
        if "status:reviewer" in labels and pr:
            next_role = "risk_manager"
        else:
            next_role = "engineer"

        github.set_status(state["issue_number"], next_role)
    else:
        # Rejected: Kick back to whoever did the work
        # We check the thread to see who to blame
        is_code = "```python" in thread_context
        next_role = "engineer" if is_code else "researcher"
        github.set_status(state["issue_number"], next_role)

    return {
        "messages": [
            f"Reviewer processed issue #{state['issue_number']}. Decision posted."
        ]
    }
