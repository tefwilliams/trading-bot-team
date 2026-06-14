from llm import get_llm, load_prompt
from github_utils import GitHubManager
from state import AgentState


def researcher_node(state: AgentState):
    llm = get_llm("researcher")
    github = GitHubManager()

    issue = github.get_issue(state["issue_number"])

    # Fetch conversation history so the researcher can see previous feedback
    comments = list(issue.get_comments())
    thread_context = "\n\n".join(
        [f"--- Feedback from {c.user.login} ---\n{c.body}" for c in comments]
    )

    template = load_prompt("researcher.md")
    prompt = template.format(
        title=issue.title, body=issue.body, thread_context=thread_context
    )

    # Thinking model will generate reasoning + response
    response = llm.invoke(prompt)
    content = response.content
    if isinstance(content, list):
        content = "\n".join(
            [part["text"] for part in content if part["type"] == "text"]
        )

    # Post the proposal as a comment
    github.post_comment(state["issue_number"], content)

    # Transition the ticket: Researcher -> Reviewer
    github.set_status(state["issue_number"], "reviewer")

    return {
        "messages": [
            f"Researcher generated strategy proposal for issue #{state['issue_number']}"
        ]
    }
