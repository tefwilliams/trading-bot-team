import logging
from typing import Literal, Optional

from pydantic import BaseModel, Field

from llm import get_llm, load_prompt
from github_utils import GitHubManager
from state import AgentState

logger = logging.getLogger(__name__)

# Cap on reviewer rejections per issue before escalating to a human. Bounds both
# the Researcher <-> Reviewer (spec) loop and the Engineer <-> Reviewer (code) loop.
MAX_REVIEW_REJECTIONS = 3


class ReviewDecision(BaseModel):
    """Structured verdict from the Reviewer, used for deterministic routing."""

    review_mode: Literal["spec", "code"] = Field(
        description="Whether a strategy specification or Python code is being reviewed."
    )
    decision: Literal["approved", "rejected"] = Field(
        description="The overall verdict."
    )
    blame: Optional[Literal["researcher", "engineer"]] = Field(
        default=None,
        description=(
            "Required when rejected: who must fix it. 'researcher' if the core "
            "strategy/hypothesis is flawed; 'engineer' if the implementation is."
        ),
    )
    review_markdown: str = Field(
        description=(
            "The full human-readable review: which checklist items passed/failed "
            "and, if rejected, the precise fixes required."
        )
    )


def reviewer_node(state: AgentState):
    """
    Critiques the current state of the strategy (spec or code) and decides
    whether to approve or request changes. Returns a structured verdict so the
    routing does not depend on fragile string matching.
    """
    github = GitHubManager()
    issue = github.get_issue(state["issue_number"])

    # Get all comments to see what the Researcher or Engineer posted
    comments = list(issue.get_comments())
    thread_context = "\n\n".join(
        [f"--- Comment by {c.user.login} ---\n{c.body}" for c in comments]
    )

    # Fetch PR context if an implementation exists. Its presence determines the
    # review mode deterministically, rather than asking the model to guess.
    pr = github.get_related_pr(state["issue_number"])
    if pr:
        diff, reviews = github.get_pr_context(pr.number)
        thread_context += f"\n\n--- PULL REQUEST DIFF (#{pr.number}) ---\n{diff}\n\n--- PR REVIEW COMMENTS ---\n{reviews}"
    review_mode = "code" if pr else "spec"

    template = load_prompt("reviewer.md")
    prompt = template.format(
        title=issue.title,
        body=issue.body,
        thread_context=thread_context,
        review_mode=review_mode.upper(),
    )

    llm = get_llm("reviewer", structured_output=ReviewDecision)
    try:
        verdict: ReviewDecision = llm.invoke(prompt)
    except Exception as e:
        # Fail safe: never auto-approve on a parse/model error. Route the fix back
        # to whoever owns the current stage so a human can intervene if it persists.
        logger.error(f"Reviewer structured output failed for #{state['issue_number']}: {e}")
        github.post_comment(
            state["issue_number"],
            f"### 🧐 Reviewer Error\nCould not produce a structured verdict: `{e}`\nRouting back for another attempt.",
        )
        github.set_status(state["issue_number"], "engineer" if pr else "researcher")
        return {"messages": [f"Reviewer errored on issue #{state['issue_number']}"]}

    approved = verdict.decision == "approved"
    rejections = state.get("review_rejections", 0) or 0

    # Post the human-readable critique. Failed strategies go to the main issue so
    # the Researcher sees them; otherwise prefer the PR thread when one exists.
    blame_researcher = verdict.blame == "researcher"
    target_id = (
        state["issue_number"] if (blame_researcher or not pr) else pr.number
    )
    github.post_comment(target_id, f"### 🧐 Reviewer Feedback\n\n{verdict.review_markdown}")

    if approved:
        # Code approved by the sole AI gate -> human merges; spec approved -> implement.
        next_role = "done" if pr else "engineer"
        github.set_status(state["issue_number"], next_role)
        return {
            "messages": [
                f"Reviewer APPROVED issue #{state['issue_number']} ({review_mode}); -> {next_role}"
            ],
            "review_rejections": 0,
        }

    # Rejected: enforce the review-loop cap before routing back.
    new_rejections = rejections + 1
    if new_rejections >= MAX_REVIEW_REJECTIONS:
        github.post_comment(
            target_id,
            (
                f"### 🚫 Review Limit Reached\n"
                f"The Reviewer has rejected this issue **{new_rejections}** times "
                f"(cap: {MAX_REVIEW_REJECTIONS}). Moving to `status:blocked` for a human."
            ),
        )
        github.set_status(state["issue_number"], "blocked")
        return {
            "messages": [
                f"Reviewer REJECTED #{state['issue_number']} — cap reached, escalated to status:blocked"
            ],
            "review_rejections": new_rejections,
        }

    # Route the fix to the blamed role, defaulting by stage if the model omitted it.
    if verdict.blame:
        next_role = "researcher" if blame_researcher else "engineer"
    else:
        next_role = "engineer" if pr else "researcher"
    github.set_status(state["issue_number"], next_role)

    return {
        "messages": [
            f"Reviewer REJECTED #{state['issue_number']} ({review_mode}); -> {next_role}"
        ],
        "review_rejections": new_rejections,
    }
