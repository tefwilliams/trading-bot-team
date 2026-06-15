# Agent Roles (Free-Tier Optimized)

All AI roles run on **Gemini 3.1 Flash Lite**. The architecture compensates for the lightweight
model with rigid checklist prompts and deterministic verification.

## Manager (Human)

- **Role:** The user. Acts as the Strategic Product Manager.
- **Responsibilities:** Directs the team via GitHub Issues — sets high-level strategy objectives,
  and performs the **single human gate**: the final review and merge of the Pull Request. Also the
  safety net for issues escalated to `status:blocked`.

## Researcher

- **Responsibilities:** Propose strategy ideas with a simple mathematical rationale and define
  entry/exit conditions in plain, unambiguous English. Must use explicit step-by-step logic to
  compensate for lightweight model reasoning.
- **Output:** An explicit strategy proposal posted to the issue; moves it to `status:reviewer`.

## Engineer

- **Responsibilities:** Translate an approved strategy spec into runnable Python — signal
  generation, position sizing, backtest harness. Must adhere strictly to the JSON results contract
  and the `yfinance` requirements in `DEVELOPER_GUIDE.md`. Uses `pandas` / `pandas_ta` (never `talib`).
- **Output:** Code committed to `strat/issue-X`, a PR, and a comment linking it; moves to `status:backtester`.

## Reviewer

- **Responsibilities:** The **single AI quality gate** — there is no separate Risk Manager, so the
  Reviewer owns both correctness and risk. Uses a rigid markdown checklist to evaluate the spec or
  the code for: look-ahead bias, logical flaws, contract compliance, and risk (position sizing,
  stop-loss, slippage/liquidity, overfitting).
- **Output:** A structured review ending in `[APPROVED]` or `[REJECTED]`. On rejection it tags the
  responsible role (`[RESEARCHER]` or `[ENGINEER]`) to route the fix. Approved code moves to `status:done`.

## Backtester (Deterministic Node — Not an LLM)

- **Responsibilities:**
  1. **Static validation:** AST-checks the required interface (`generate_signals`, `run_backtest`, results contract).
  2. **Execution engine:** runs the Engineer's code in an isolated subprocess (120s timeout).
  3. **Error correction:** on failure, captures the stack trace / report and routes back to the
     Engineer, capped at 3 attempts before escalating to `status:blocked`.
- **Audit trail:** acts as the source of truth for portfolio metrics, protecting the system from LLM hallucinations.

> Earlier versions also had a **Risk Manager** and a **Historian** (manifest archivist). These are
> not part of the current pipeline; risk review now lives in the Reviewer.
