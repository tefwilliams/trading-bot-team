# Agent roles

## Manager (human)

The user. Directs the team via GitHub Issues — opens high-level objectives, approves or rejects proposals, decides when to merge or kick back work.

## Researcher

- **Default model:** Gemini (long context useful for digesting articles, papers, prior backtest results)
- **Responsibilities:** Propose strategy ideas with rationale, cite sources/reasoning, define entry/exit conditions in plain English.
- **Output:** A strategy proposal issue with a clear specification.

## Engineer

- **Default model:** Claude (strong code generation)
- **Responsibilities:** Translate an approved strategy spec into runnable Python — signal generation, position sizing, backtest harness.
- **Output:** Code committed to a branch, plus a comment on the originating issue linking to the PR.

## Reviewer

- **Default model:** Whichever model did NOT produce the artifact under review (cross-model review).
- **Responsibilities:** Critique strategies for logical flaws, look-ahead bias, unrealistic assumptions; review code for bugs, edge cases, risk-handling gaps.
- **Output:** Review comments on the issue or PR.

## Backtester (not an LLM)

- Deterministic Python function that runs strategy code on historical data and returns standard metrics (Sharpe, max drawdown, hit rate, etc.).
- Called by the workflow, not "reasoned with."
