"""Smoke-test the LLM wiring without running the orchestrator.

Verifies the two pieces that can't be checked offline:
  1. Each role's model id actually resolves on your GOOGLE_API_KEY.
  2. `with_structured_output` returns a populated object for every schema in use
     (and the Strategy Reviewer's Pro model + fallback wrapper invokes cleanly).

Usage:
    python scripts/smoke_test_llm.py            # LLM checks only (~5 API calls)
    python scripts/smoke_test_llm.py --issue 1  # also read-only GitHub context checks for issue #1

Costs a handful of free-tier calls (gemini-3.5-flash and gemini-3.1-flash-lite). Read-only —
it never writes to GitHub.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from llm import get_llm  # noqa: E402
from nodes.engineer import EngineerOutput  # noqa: E402
from nodes.review_common import ReviewDecision, CodeReviewDecision  # noqa: E402
from llm import ROLE_MODELS  # noqa: E402


def _check(name, fn):
    """Run one check, print a pass/fail line, and return True on success."""
    try:
        detail = fn()
        print(f"  ✅ {name}: {detail}")
        return True
    except Exception as e:
        print(f"  ❌ {name}: {type(e).__name__}: {e}")
        return False


def llm_checks():
    """One call per role — the exact (model, structured-output) combination each uses."""
    print("LLM wiring (model resolution + structured output):")
    results = []

    # Researcher — plain text generation on its model.
    def researcher():
        resp = get_llm("researcher").invoke("Reply with the single word: ok")
        text = resp.content if isinstance(resp.content, str) else str(resp.content)
        assert text.strip(), "empty response"
        return f"{ROLE_MODELS['researcher']} -> {text.strip()[:40]!r}"

    results.append(_check("researcher (plain)", researcher))

    # Strategy Reviewer — Pro model (+ fallback wrapper) returning a ReviewDecision.
    def strategy_reviewer():
        v = get_llm("strategy_reviewer", structured_output=ReviewDecision).invoke(
            "You are reviewing a spec. Reply approved with a one-line review."
        )
        assert v.decision in ("approved", "rejected"), f"bad decision {v.decision!r}"
        return f"{ROLE_MODELS['strategy_reviewer']} -> decision={v.decision}"

    results.append(_check("strategy_reviewer (ReviewDecision + fallback)", strategy_reviewer))

    # Engineer — EngineerOutput structured output.
    def engineer():
        out = get_llm("engineer", structured_output=EngineerOutput).invoke(
            "Implement a trivial strategy. Set code to \"print('hello')\" and fill the other fields."
        )
        assert out.code.strip(), "empty code field"
        return f"{ROLE_MODELS['engineer']} -> fields={list(out.model_dump().keys())}"

    results.append(_check("engineer (EngineerOutput)", engineer))

    # Code Reviewer — CodeReviewDecision (adds high_level_summary).
    def code_reviewer():
        v = get_llm("code_reviewer", structured_output=CodeReviewDecision).invoke(
            "Reply approved with a one-line review and a one-line high_level_summary."
        )
        assert v.decision in ("approved", "rejected"), f"bad decision {v.decision!r}"
        assert hasattr(v, "high_level_summary"), "missing high_level_summary"
        return f"{ROLE_MODELS['code_reviewer']} -> decision={v.decision}"

    results.append(_check("code_reviewer (CodeReviewDecision)", code_reviewer))

    # Performance Reviewer — ReviewDecision on its model.
    def performance_reviewer():
        v = get_llm("performance_reviewer", structured_output=ReviewDecision).invoke(
            "You are judging edge. Reply rejected with a one-line review."
        )
        assert v.decision in ("approved", "rejected"), f"bad decision {v.decision!r}"
        return f"{ROLE_MODELS['performance_reviewer']} -> decision={v.decision}"

    results.append(_check("performance_reviewer (ReviewDecision)", performance_reviewer))

    return results


def github_checks(issue_number):
    """Read-only: confirm the context helpers work against a real issue."""
    print(f"\nGitHub context (read-only, issue #{issue_number}):")
    from github_utils import GitHubManager

    github = GitHubManager()
    issue = github.get_issue(issue_number)
    results = []

    results.append(_check(
        "get_issue_context",
        lambda: f"{len(github.get_issue_context(issue))} chars",
    ))
    results.append(_check(
        "get_full_context",
        lambda: (lambda ctx, pr: f"{len(ctx)} chars, pr={pr.number if pr else None}")(
            *github.get_full_context(issue)
        ),
    ))
    return results


def main():
    issue_number = None
    if "--issue" in sys.argv:
        issue_number = int(sys.argv[sys.argv.index("--issue") + 1])

    results = llm_checks()
    if issue_number is not None:
        results += github_checks(issue_number)

    passed = sum(results)
    total = len(results)
    print(f"\n{passed}/{total} checks passed.")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
