from llm import get_llm
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

    prompt = f"""
    You are a Quantitative Researcher. Your task is to respond to the following objective 
    and propose a formal trading strategy using the Strategy Proposal template.
    
    Objective from Manager:
    Title: {issue.title}
    Description: {issue.body}

    CONVERSATION HISTORY / PREVIOUS FEEDBACK:
    {thread_context}
    
    Please output your proposal in Markdown, following the sections:
    - Hypothesis
    - Entry Rule
    - Exit Rule
    - Universe
    - Timeframe
    - Position Sizing
    - Risks and Assumptions

    IMPORTANT: If there is previous feedback, you MUST address the specific critiques and improve the strategy accordingly.
    """

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
