# Agent roles

## Manager (human)

The user. Directs the team via GitHub Issues — opens high-level objectives, approves or rejects proposals, decides when to merge or kick back work.

## Researcher

- **Default model:** Gemini 3.1 Flash Lite
- **Responsibilities:** Propose strategy ideas with rationale, cite sources/reasoning, define entry/exit conditions in plain English.
- **Output:** A strategy proposal issue with a clear specification.

## Engineer

- **Default model:** Gemini 3.1 Flash Lite
- **Responsibilities:** Translate an approved strategy spec into runnable Python — signal generation, position sizing, backtest harness.
- **Output:** Code committed to a branch, plus a comment on the originating issue linking to the PR.

## Reviewer

- **Default model:** Gemini 3.1 Flash Lite
- **Responsibilities:** Critique strategies for logical flaws, look-ahead bias, unrealistic assumptions; review code for bugs, edge cases, risk-handling gaps.
- **Output:** Review comments on the issue or PR.

## Product Manager

- **Default model:** Gemini 3.1 Flash Lite
- **Responsibilities:** Analyze the current state of the application, review the backlog, and propose new features or infrastructure improvements.
- **Output:** Detailed feature proposals or system enhancement issues.

## Backtester (not an LLM)

- Deterministic LangGraph node that executes strategy code in a subprocess.
- Forces non-interactive plotting (Agg backend) and reports performance metrics (Returns, MDD, Sharpe) back to the GitHub issue.
