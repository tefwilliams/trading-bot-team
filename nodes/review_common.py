"""Shared helpers for the Strategy Reviewer and Code Reviewer nodes."""

import logging
from typing import Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Cumulative cap on reviewer rejections per issue, across all three reviewers. It is not
# reset on approval, so an issue is guaranteed to reach status:done or status:blocked
# within a bounded number of rejections (no infinite review churn).
MAX_REVIEW_REJECTIONS = 5


class ReviewDecision(BaseModel):
    """Structured verdict used for deterministic routing. Blame is structural — each
    reviewer routes rejections to a single owner — so no blame field is needed."""

    decision: Literal["approved", "rejected"] = Field(description="The overall verdict.")
    review_markdown: str = Field(
        description=(
            "The full human-readable review: each checklist item marked PASS/FAIL/N/A "
            "with a one-line reason, and, if rejected, the precise fixes required."
        )
    )


def build_review_context(github, issue):
    """Concatenate the issue thread and, if a PR exists, its diff + review comments.
    Returns (thread_context, pr) where pr is None when no implementation exists yet."""
    comments = list(issue.get_comments())
    thread_context = "\n\n".join(
        f"--- Comment by {c.user.login} ---\n{c.body}" for c in comments
    )

    pr = github.get_related_pr(issue.number)
    if pr:
        diff, reviews = github.get_pr_context(pr.number)
        thread_context += (
            f"\n\n--- PULL REQUEST DIFF (#{pr.number}) ---\n{diff}"
            f"\n\n--- PR REVIEW COMMENTS ---\n{reviews}"
        )
    return thread_context, pr


def apply_rejection(github, state, target_id, next_role):
    """Increment the cumulative review counter, then route to `next_role` or escalate
    to status:blocked when the cap is reached. Returns the new counter value."""
    issue_number = state["issue_number"]
    new_rejections = (state.get("review_rejections", 0) or 0) + 1

    if new_rejections >= MAX_REVIEW_REJECTIONS:
        github.post_comment(
            target_id,
            (
                f"### 🚫 Review Limit Reached\n"
                f"This issue has been rejected **{new_rejections}** times across the "
                f"reviewers (cap: {MAX_REVIEW_REJECTIONS}). Moving to `status:blocked` "
                f"for a human to investigate."
            ),
        )
        github.set_status(issue_number, "blocked")
    else:
        github.set_status(issue_number, next_role)

    return new_rejections
