from llm import get_llm
from github_utils import GitHubManager
from state import AgentState


def product_manager_node(state: AgentState):
    """
    Analyzes the current state of the repo and proposes new features or improvements.
    """
    llm = get_llm("product_manager")
    github = GitHubManager()
    issue = github.get_issue(state["issue_number"])

    # In a real scenario, we might pass the file tree or a summary of existing strategies here.
    # For now, we use the issue context as the starting point for analysis.
    comments = list(issue.get_comments())
    thread_context = "\n\n".join([f"{c.user.login}: {c.body}" for c in comments])
    labels = [l.name for l in issue.get_labels()]

    prompt = f"""
    You are a Strategic Product Manager. Your goal is to oversee the product lifecycle and analyze results.

    CURRENT CONTEXT:
    Issue: #{issue.number}
    Title: {issue.title}
    Initial Request: {issue.body}
    
    CONVERSATION HISTORY:
    {thread_context}

    DECISION LOGIC:
    - If this is a 'final-review' (implementation is finished), evaluate if the 'Initial Request' was met.
    - If the objective is met, conclude with [READY_FOR_MERGE] and a summary of performance.
    - If improvements are needed or a new feature is inspired by this result, conclude with [NEW_ISSUE] followed by a title and description.
    - If this is 'ideation', propose 1-2 concrete features.

    Format your response clearly. Use [ISSUE_COMPLETE] or [NEW_ISSUE] as headers if taking those actions.
    """

    response = llm.invoke(prompt)
    content = response.content
    if isinstance(content, list):
        content = "\n".join(
            [part["text"] for part in content if part["type"] == "text"]
        )

    # Post the PM's synthesis
    github.post_comment(
        state["issue_number"], f"### 💡 Product Manager Proposal\n\n{content}"
    )

    # Logic for closing/opening issues
    if "[READY_FOR_MERGE]" in content.upper():
        github.update_labels(
            state["issue_number"],
            add=["role:manager", "stage:done"],
            remove=["role:product_manager", "stage:final-review"],
        )

    if "[NEW_ISSUE]" in content.upper():
        # Basic parsing of the LLM's suggested new issue
        # In a production scenario, we'd use Structured Output/Pydantic here
        github.create_issue(
            title=f"Next Step: {issue.title} (Follow-up)",
            body=f"Generated follow-up from Issue #{state['issue_number']}\n\n{content}",
            labels=["role:researcher", "stage:proposal"],
        )

    # If not completed, it likely needs human manager intervention or moves back to ideation
    if (
        "[READY_FOR_MERGE]" not in content.upper()
        and "[NEW_ISSUE]" not in content.upper()
    ):
        github.update_labels(
            state["issue_number"],
            add=["role:manager", "stage:review"],
            remove=["role:product_manager"],
        )

    return {
        "messages": [
            f"Product Manager proposed new features for issue #{state['issue_number']}"
        ]
    }
