import logging

from llm import get_llm, load_prompt
from github_utils import GitHubManager
from state import AgentState
from nodes.review_common import ReviewDecision

logger = logging.getLogger(__name__)

# Number of research cycles (distinct strategies tried) before escalating to a human.
MAX_RESEARCH_CYCLES = 3


def performance_reviewer_node(state: AgentState):
    """
    Judges whether a backtested strategy actually has an *edge* — does it beat its buy-and-hold
    benchmark on a risk-adjusted basis? Runs after the Code Reviewer has cleared the implementation,
    on the cheaper gemini-3-flash model (the judgment is largely numeric). Approvals reach
    status:done (human merges); rejections go back to the Researcher (the hypothesis has no edge).
    """
    github = GitHubManager()
    issue = github.get_issue(state["issue_number"])

    # Reads the PR only (the backtest metrics + code); it distils its verdict back to the issue.
    pr = github.get_related_pr(state["issue_number"])
    if not pr:
        # Should not happen (reached only after the engineer/backtester/code-reviewer run).
        logger.warning(f"Performance reviewer found no PR for #{state['issue_number']}; routing to engineer")
        github.set_status(state["issue_number"], "engineer")
        return {"messages": [f"Performance reviewer: no PR for #{state['issue_number']}"]}
    thread_context = github.get_pr_context(pr.number)

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

    if verdict.decision == "approved":
        # Edge confirmed -> the PR is ready for the human to merge, so post the verdict there.
        github.post_comment(pr.number, f"### 📊 Performance Review\n\n{verdict.review_markdown}")
        github.set_status(state["issue_number"], "done")
        return {
            "messages": [f"Performance reviewer APPROVED #{state['issue_number']}; -> done"]
        }

    # Rejected: this strategy has no edge. Distil the verdict to the issue for the
    # Researcher (who works at the strategy level and won't read the PR).
    issue_number = state["issue_number"]
    github.post_comment(issue_number, f"### 📊 Performance Review\n\n{verdict.review_markdown}")

    new_cycles = (state.get("research_cycles", 0) or 0) + 1
    if new_cycles >= MAX_RESEARCH_CYCLES:
        # Out of research attempts. Escalate to a human and LEAVE THE PR OPEN for inspection.
        github.post_comment(
            issue_number,
            f"### 🚫 Research Cycle Limit Reached\n{new_cycles} strategies have been tried "
            f"without a demonstrated edge (cap: {MAX_RESEARCH_CYCLES}). Moving to "
            f"`status:blocked` for a human. The latest PR is left open for inspection.",
        )
        github.set_status(issue_number, "blocked")
        return {
            "messages": [
                f"Performance reviewer REJECTED #{issue_number} — research cap reached, status:blocked"
            ],
            "research_cycles": new_cycles,
        }

    # Start a fresh research cycle: close + delete this dead-end PR/branch (so the next
    # spec gets a clean PR), then route to the Researcher with a fresh churn budget.
    github.post_comment(
        pr.number,
        "### 📊 Performance Review: No Edge\nClosing this PR — the strategy does not "
        "demonstrate an edge. See the issue for the summary and next steps.",
    )
    github.close_pr(pr.number)
    github.delete_branch(f"strat/issue-{issue_number}")
    github.set_status(issue_number, "researcher")
    return {
        "messages": [
            f"Performance reviewer REJECTED #{issue_number} (PR closed); research cycle {new_cycles}"
        ],
        "research_cycles": new_cycles,
        "review_rejections": 0,
    }
