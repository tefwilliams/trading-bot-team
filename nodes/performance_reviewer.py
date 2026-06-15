import logging

from llm import get_llm, load_prompt
from github_utils import GitHubManager
from state import AgentState
from nodes.review_common import ReviewDecision, build_review_context, apply_rejection

logger = logging.getLogger(__name__)


def performance_reviewer_node(state: AgentState):
    """
    Judges whether a backtested strategy actually has an *edge* — does it beat its buy-and-hold
    benchmark on a risk-adjusted basis? Runs after the Code Reviewer has cleared the implementation,
    on the cheaper gemini-3-flash model (the judgment is largely numeric). Approvals reach
    status:done (human merges); rejections go back to the Researcher (the hypothesis has no edge).
    """
    github = GitHubManager()
    issue = github.get_issue(state["issue_number"])
    thread_context, pr = build_review_context(github, issue)

    if not pr:
        # Should not happen (reached only after the engineer/backtester/code-reviewer run).
        logger.warning(f"Performance reviewer found no PR for #{state['issue_number']}; routing to engineer")
        github.set_status(state["issue_number"], "engineer")
        return {"messages": [f"Performance reviewer: no PR for #{state['issue_number']}"]}

    template = load_prompt("performance_reviewer.md")
    prompt = template.format(
        title=issue.title, body=issue.body, thread_context=thread_context
    )

    llm = get_llm("performance_reviewer", structured_output=ReviewDecision)
    try:
        verdict: ReviewDecision = llm.invoke(prompt)
    except Exception as e:
        # Fail safe: never auto-approve on a model/parse error. Send back to the Researcher.
        logger.error(f"Performance reviewer failed for #{state['issue_number']}: {e}")
        github.post_comment(
            state["issue_number"],
            f"### 📊 Performance Review Error\nCould not produce a verdict: `{e}`\nRouting back to the researcher.",
        )
        github.set_status(state["issue_number"], "researcher")
        return {"messages": [f"Performance reviewer errored on issue #{state['issue_number']}"]}

    # Post to the issue so the Researcher sees the edge critique on rejection.
    github.post_comment(
        state["issue_number"], f"### 📊 Performance Review\n\n{verdict.review_markdown}"
    )

    if verdict.decision == "approved":
        github.set_status(state["issue_number"], "done")
        return {
            "messages": [f"Performance reviewer APPROVED #{state['issue_number']}; -> done"]
        }

    # Rejected -> back to the Researcher (cumulative cap may escalate to status:blocked).
    new_rejections = apply_rejection(github, state, state["issue_number"], "researcher")
    return {
        "messages": [
            f"Performance reviewer REJECTED #{state['issue_number']}; rejection #{new_rejections}"
        ],
        "review_rejections": new_rejections,
    }
