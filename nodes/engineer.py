import logging

from pydantic import BaseModel, Field

from llm import get_llm, load_prompt
from github_utils import GitHubManager
from state import AgentState

logger = logging.getLogger(__name__)

# Consecutive Engineer model/output failures before escalating to a human.
MAX_ENGINEER_FAILURES = 3


class EngineerOutput(BaseModel):
    """Structured engineer output so each channel gets the right granularity."""

    pr_description: str = Field(
        description="The current state of the implementation, as the PR description (Markdown)."
    )
    change_summary: str = Field(
        description="What changed in THIS iteration (Markdown), posted as a PR comment."
    )
    code: str = Field(description="The complete Python strategy module. No markdown fences.")


def engineer_node(state: AgentState):
    """
    Translates an approved strategy into runnable Python. Communicates on the PR (the
    implementation channel): it keeps the PR description current and posts a change summary
    each iteration. It does NOT post to the issue — the issue stays at the strategy level,
    and the Code Reviewer posts the high-level "implemented" note there on approval.
    """
    github = GitHubManager()
    issue = github.get_issue(state["issue_number"])

    # Full context: the spec (issue) plus any backtest/code-review feedback (PR) that
    # routed it back here.
    thread_context, _pr = github.get_full_context(issue)

    template = load_prompt("engineer.md")
    prompt = template.format(
        title=issue.title,
        body=issue.body,
        thread_context=thread_context,
        issue_number=state["issue_number"],
    )

    llm = get_llm("engineer", structured_output=EngineerOutput)
    try:
        result: EngineerOutput = llm.invoke(prompt)
    except Exception as e:
        # Model/parse error. Retry on the next poll, but cap consecutive failures so a
        # persistently-failing issue escalates to a human instead of looping forever.
        failures = (state.get("engineer_failures", 0) or 0) + 1
        logger.error(f"Engineer failed for #{state['issue_number']} ({failures}x): {e}")
        if failures >= MAX_ENGINEER_FAILURES:
            github.post_comment(
                state["issue_number"],
                f"### 🚫 Engineer Stuck\nThe Engineer failed to produce valid output "
                f"{failures} times (cap: {MAX_ENGINEER_FAILURES}). Moving to `status:blocked`.",
            )
            github.set_status(state["issue_number"], "blocked")
        return {
            "messages": [f"Engineer errored on issue #{state['issue_number']}"],
            "engineer_failures": failures,
        }

    branch_name = f"strat/issue-{state['issue_number']}"
    github.ensure_branch(branch_name)

    # Defensive: strip markdown fences in case the model wrapped the code field.
    clean_code = github.extract_code(result.code)
    file_path = f"strategies/strategy_{state['issue_number']}.py"
    github.create_or_update_file(
        file_path,
        f"Implement strategy for issue #{state['issue_number']}",
        clean_code,
        branch_name,
    )

    # create_pull_request returns the existing OPEN PR if one exists, else creates a new
    # one. Because the Performance Reviewer closes the PR when a strategy is abandoned, a
    # new spec naturally gets a fresh PR here.
    pr_body = f"{result.pr_description}\n\nCloses #{state['issue_number']}"
    pr = github.create_pull_request(
        title=f"Strategy: {issue.title}", body=pr_body, head=branch_name
    )
    # Keep the description current even when reusing an existing PR.
    github.update_pr_body(pr.number, pr_body)
    github.post_comment(pr.number, f"### 🛠️ Change Summary\n{result.change_summary}")

    github.set_status(state["issue_number"], "backtester")

    return {
        "messages": [
            f"Engineer implemented issue #{state['issue_number']} on PR #{pr.number}"
        ],
        "engineer_failures": 0,
    }
