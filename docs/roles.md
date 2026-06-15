# Agent Roles (Free-Tier Optimized)

All roles run on Google AI Studio free-tier models, tiered by need (see `llm.py`). Pro is reserved for
the single hardest reasoning task — judging spec soundness:
- **Researcher** → `gemini-3-flash`, temp 0.7.
- **Strategy Reviewer** → `gemini-2.5-pro` (spec soundness), temp 0.0, with a fallback to `gemini-3-flash`.
- **Engineer** → `gemini-3-flash` (code generation), temp 0.3.
- **Code Reviewer** → `gemini-3.1-flash-lite` (mechanical implementation checks), temp 0.0.
- **Performance Reviewer** → `gemini-3-flash` (edge vs benchmark — largely numeric), temp 0.0.

Note: `gemini-2.5-pro` is heavily rate-limited (~5 RPM, 50-100 RPD), but the Strategy Reviewer fires
only once per research iteration (at the spec gate, before any code), so the limit is comfortable; it
degrades to `gemini-3-flash` on error/throttle. The architecture still compensates for lightweight
models with rigid checklist prompts and deterministic verification.

## Manager (Human)

- **Role:** The user. Acts as the Strategic Product Manager.
- **Responsibilities:** Directs the team via GitHub Issues — sets high-level strategy objectives,
  and performs the **single human gate**: the final review and merge of the Pull Request. Also the
  safety net for issues escalated to `status:blocked`.

## Researcher

- **Responsibilities:** Propose strategy ideas with a simple mathematical rationale and define
  entry/exit conditions in plain, unambiguous English. Must use explicit step-by-step logic to
  compensate for lightweight model reasoning.
- **Output:** An explicit strategy proposal posted to the issue; moves it to `status:strategy_reviewer`.

## Strategy Reviewer

- **Responsibilities:** Reviews the strategy *specification* for soundness before any code is written
  — look-ahead bias in the logic, ambiguous rules, overfitting, plausibility of the hypothesis, and
  risk controls (there is no separate Risk Manager, so risk soundness lives here). This is the hardest
  reasoning task, so it runs on Pro; it fires once per research iteration.
- **Routing:** approval → Engineer; rejection → Researcher.
- **Output:** A structured verdict (`decision`, `review_markdown`) via structured-output mode.

## Engineer

- **Responsibilities:** Translate an approved strategy spec into runnable Python — signal
  generation, position sizing, backtest harness. Must adhere strictly to the JSON results contract
  and the `yfinance` requirements in `DEVELOPER_GUIDE.md`. Uses `pandas` / `pandas_ta` (never `talib`).
- **Output:** Code committed to `strat/issue-X`, a PR, and a comment linking it; moves to `status:backtester`.

## Code Reviewer

- **Responsibilities:** Owns the *implementation* side of quality. Runs after a successful backtest
  and checks contract compliance, look-ahead bias **in the code**, faithfulness to the spec,
  correctness, and pandas hygiene. It does NOT judge whether the strategy is a good idea (that's the
  Strategy Reviewer). On the cheap model, it absorbs the Engineer bug-fix churn loop.
- **Routing:** rejections always go back to the **Engineer**; approval → Performance Reviewer.
- **Output:** A structured verdict (`decision`, `review_markdown`) via structured-output mode.

## Performance Reviewer

- **Responsibilities:** Judges **edge** — does the backtested strategy beat its buy-and-hold
  `benchmark_return` with a positive risk-adjusted return? A clean backtest with no edge is rejected.
  The judgment is largely numeric, so it runs on the cheaper `gemini-3-flash`.
- **Routing:** approval → `status:done` (human merges); rejection → Researcher (hypothesis has no edge).
- **Output:** A structured verdict (`decision`, `review_markdown`) via structured-output mode.
- **Edge-test caveats:** the benchmark is naive buy-and-hold of the *primary instrument* (not a broad
  index); transaction costs and slippage are not modelled (so high-churn edge is overstated); and raw
  return alone can mislead (lower return with much lower drawdown may still be edge). The reviewer is
  told to weigh risk-adjusted performance, not just "beats benchmark."

Rejections from all three reviewers share a single cumulative per-issue counter; after
`MAX_REVIEW_REJECTIONS` (5) the issue is escalated to `status:blocked`.

## Backtester (Deterministic Node — Not an LLM)

- **Responsibilities:**
  1. **Static validation:** AST-checks the required interface (`generate_signals`, `run_backtest`, results contract).
  2. **Execution engine:** runs the Engineer's code in an isolated subprocess (120s timeout).
  3. **Error correction:** on failure, captures the stack trace / report and routes back to the
     Engineer, capped at 3 attempts before escalating to `status:blocked`.
- **Audit trail:** acts as the source of truth for portfolio metrics, protecting the system from LLM hallucinations.

> Earlier versions also had a **Risk Manager** and a **Historian** (manifest archivist). These are
> not part of the current pipeline; risk review now lives in the Strategy Reviewer.
