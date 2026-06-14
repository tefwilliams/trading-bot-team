# Agent roles

## Manager (human)

The user. Acts as the **Strategic Product Manager**. 
Directs the team via GitHub Issues — generates high-level strategy objectives, defines product vision, approves/rejects proposals, and performs final PR merges.

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

## Backtester (not an LLM)

- Deterministic LangGraph node that executes strategy code in a subprocess.
- Forces non-interactive plotting (Agg backend) and reports performance metrics (Returns, MDD, Sharpe) back to the GitHub issue.
- **Contract Enforcer**: Strictly validates that the Engineer's code adheres to the JSON results interface.
