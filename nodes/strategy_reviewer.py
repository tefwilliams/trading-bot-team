import logging

from llm import get_llm, load_prompt
from github_utils import GitHubManager
from state import AgentState
from nodes.review_common import ReviewDecision, build_review_context, apply_rejection

logger = logging.getLogger(__name__)


def strategy_reviewer_node(state: AgentState):
    """
    Owns the *strategy* side of quality. Reviews the spec (before implementation) and,
    after the Code Reviewer has cleared the implementation, judges whether the backtested
    strategy actually has an edge. Runs on the strong (Pro) model. Rejections always go
    back to the Researcher (a flawed hypothesis); approvals advance the pipeline.
    """
    github = GitHubManager()
    issue = github.get_issue(state["issue_number"])
    thread_context, pr = build_review_context(github, issue)

    # A PR exists only once the Code Reviewer has passed the implementation, so its
    # presence tells us whether we're judging the spec or the backtested edge.
    review_mode = "edge" if pr else "spec"

    template = load_prompt("strategy_reviewer.md")
    prompt = template.format(
        title=issue.title,
        body=issue.body,
        thread_context=thread_context,
        review_mode=review_mode.upper(),
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

    # Post to the issue so the Researcher sees the critique even when a PR exists.
    github.post_comment(
        state["issue_number"], f"### 🧠 Strategy Review ({review_mode})\n\n{verdict.review_markdown}"
    )

    if verdict.decision == "approved":
        next_role = "done" if pr else "engineer"
        github.set_status(state["issue_number"], next_role)
        return {
            "messages": [
                f"Strategy reviewer APPROVED #{state['issue_number']} ({review_mode}); -> {next_role}"
            ]
        }

    # Rejected -> back to the Researcher (cumulative cap may escalate to status:blocked).
    new_rejections = apply_rejection(github, state, state["issue_number"], "researcher")
    return {
        "messages": [
            f"Strategy reviewer REJECTED #{state['issue_number']} ({review_mode}); rejection #{new_rejections}"
        ],
        "review_rejections": new_rejections,
    }
