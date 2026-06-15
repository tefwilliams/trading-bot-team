import logging

from llm import get_llm, load_prompt
from github_utils import GitHubManager
from state import AgentState
from nodes.review_common import ReviewDecision, build_review_context, apply_rejection

logger = logging.getLogger(__name__)


def strategy_reviewer_node(state: AgentState):
    """
    Reviews the strategy *specification* for soundness before any code is written — the
    hardest reasoning task in the pipeline, so it runs on the strong (Pro) model. It fires
    once per research iteration (at the spec gate), which keeps Pro usage comfortable.
    Approvals advance to the Engineer; rejections go back to the Researcher.
    (Edge/performance is judged later by the Performance Reviewer.)
    """
    github = GitHubManager()
    issue = github.get_issue(state["issue_number"])
    thread_context, _pr = build_review_context(github, issue)

    template = load_prompt("strategy_reviewer.md")
    prompt = template.format(
        title=issue.title, body=issue.body, thread_context=thread_context
    )

    llm = get_llm("strategy_reviewer", structured_output=ReviewDecision)
    try:
        verdict: ReviewDecision = llm.invoke(prompt)
    except Exception as e:
        # Fail safe: never auto-approve on a model/parse error. Send back to the Researcher.
        logger.error(f"Strategy reviewer failed for #{state['issue_number']}: {e}")
        github.post_comment(
            state["issue_number"],
            f"### 🧠 Strategy Review Error\nCould not produce a verdict: `{e}`\nRouting back to the researcher.",
        )
        github.set_status(state["issue_number"], "researcher")
        return {"messages": [f"Strategy reviewer errored on issue #{state['issue_number']}"]}

    github.post_comment(
        state["issue_number"], f"### 🧠 Strategy Review (spec)\n\n{verdict.review_markdown}"
    )

    if verdict.decision == "approved":
        github.set_status(state["issue_number"], "engineer")
        return {
            "messages": [f"Strategy reviewer APPROVED spec #{state['issue_number']}; -> engineer"]
        }

    # Rejected -> back to the Researcher (cumulative cap may escalate to status:blocked).
    new_rejections = apply_rejection(github, state, state["issue_number"], "researcher")
    return {
        "messages": [
            f"Strategy reviewer REJECTED spec #{state['issue_number']}; rejection #{new_rejections}"
        ],
        "review_rejections": new_rejections,
    }
