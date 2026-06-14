from llm import get_llm, load_prompt
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

    template = load_prompt("engineer.md")
    prompt = template.format(
        title=issue.title,
        body=issue.body,
        thread_context=thread_context,
        issue_number=state["issue_number"],
    )

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
        body=(
            f"## Implementation Details\n{content}\n\n"
            f"Closes #{state['issue_number']}"
        ),
        head=branch_name,
    )

    # Post a concise update to the issue
    comment_body = (
        f"### 🛠️ Implementation Started\n"
        f"I have implemented the strategy in branch `{branch_name}` and opened a Pull Request for validation: {pr.html_url}"
    )
    github.post_comment(state["issue_number"], comment_body)

    # Transition to the backtester status
    github.set_status(state["issue_number"], "backtester")

    return {
        "messages": [
            f"Engineer generated implementation for issue #{state['issue_number']}"
        ]
    }
