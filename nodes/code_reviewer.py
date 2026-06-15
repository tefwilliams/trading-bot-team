import logging

from llm import get_llm, load_prompt
from github_utils import GitHubManager
from state import AgentState
from nodes.review_common import ReviewDecision, build_review_context, apply_rejection

logger = logging.getLogger(__name__)


def code_reviewer_node(state: AgentState):
    """
    Owns the *implementation* side of quality. Runs after a successful backtest, on the
    cheap (flash-lite) model, checking correctness/contract/look-ahead-in-code — the
    mechanical work. It shields the expensive Strategy Reviewer from the bug-fix churn
    loop: rejections go back to the Engineer; approvals advance to the Strategy Reviewer.
    """
    github = GitHubManager()
    issue = github.get_issue(state["issue_number"])
    thread_context, pr = build_review_context(github, issue)

    if not pr:
        # Should not happen (a PR exists after the engineer/backtester run). Be defensive.
        logger.warning(f"Code reviewer found no PR for #{state['issue_number']}; routing to engineer")
        github.set_status(state["issue_number"], "engineer")
        return {"messages": [f"Code reviewer: no PR for #{state['issue_number']}"]}

    template = load_prompt("code_reviewer.md")
    prompt = template.format(
        title=issue.title, body=issue.body, thread_context=thread_context
    )

    llm = get_llm("code_reviewer", structured_output=ReviewDecision)
    try:
        verdict: ReviewDecision = llm.invoke(prompt)
    except Exception as e:
        # Fail safe: never auto-pass on a model/parse error. Send back to the Engineer.
        logger.error(f"Code reviewer failed for #{state['issue_number']}: {e}")
        github.post_comment(
            pr.number,
            f"### 🔧 Code Review Error\nCould not produce a verdict: `{e}`\nRouting back to the engineer.",
        )
        github.set_status(state["issue_number"], "engineer")
        return {"messages": [f"Code reviewer errored on issue #{state['issue_number']}"]}

    github.post_comment(pr.number, f"### 🔧 Code Review\n\n{verdict.review_markdown}")

    if verdict.decision == "approved":
        # Implementation is sound -> hand to the Strategy Reviewer to judge edge.
        github.set_status(state["issue_number"], "strategy_reviewer")
        return {
            "messages": [
                f"Code reviewer APPROVED #{state['issue_number']}; -> strategy_reviewer"
            ]
        }

    # Rejected -> back to the Engineer (cumulative cap may escalate to status:blocked).
    new_rejections = apply_rejection(github, state, pr.number, "engineer")
    return {
        "messages": [
            f"Code reviewer REJECTED #{state['issue_number']}; rejection #{new_rejections}"
        ],
        "review_rejections": new_rejections,
    }
