from llm import get_llm, load_prompt
from github_utils import GitHubManager
from references import load_references
from state import AgentState


def researcher_node(state: AgentState):
    llm = get_llm("researcher")
    github = GitHubManager()

    issue = github.get_issue(state["issue_number"])

    # The researcher works at the strategy level — it reads only the issue thread.
    # Implementation-side outcomes reach it as the Performance Reviewer's distilled summary.
    thread_context = github.get_issue_context(issue)

    # Curated reference material (references/) so proposals are grounded in proven
    # approaches rather than the model's parametric memory alone.
    reference_material = load_references() or "(no reference material provided)"

    template = load_prompt("researcher.md")
    prompt = template.format(
        title=issue.title,
        body=issue.body,
        thread_context=thread_context,
        reference_material=reference_material,
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

    # Transition the ticket: Researcher -> Strategy Reviewer (spec review)
    github.set_status(state["issue_number"], "strategy_reviewer")

    return {
        "messages": [
            f"Researcher generated strategy proposal for issue #{state['issue_number']}"
        ]
    }
