from llm import get_llm
from github_utils import GitHubManager
from state import AgentState


def researcher_node(state: AgentState):
    llm = get_llm("researcher")
    github = GitHubManager()

    issue = github.get_issue(state["issue_number"])

    prompt = f"""
    You are a Quantitative Researcher. Your task is to respond to the following objective 
    and propose a formal trading strategy using the Strategy Proposal template.
    
    Objective from Manager:
    Title: {issue.title}
    Description: {issue.body}
    
    Please output your proposal in Markdown, following the sections:
    - Hypothesis
    - Entry Rule
    - Exit Rule
    - Universe
    - Timeframe
    - Position Sizing
    - Risks and Assumptions
    """

    # Thinking model will generate reasoning + response
    response = llm.invoke(prompt)

    # Post the proposal as a comment
    github.post_comment(state["issue_number"], response.content)

    # Transition the ticket: Researcher -> Reviewer
    github.update_labels(
        state["issue_number"],
        add=["role:reviewer", "stage:review"],
        remove=["role:researcher", "stage:proposal"],
    )

    return {
        "messages": [
            f"Researcher generated strategy proposal for issue #{state['issue_number']}"
        ]
    }
