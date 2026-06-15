# Agent Roles (Free-Tier Optimized)

All roles run on Google AI Studio free-tier models, tiered by need (see `llm.py`). Reasoning effort
is concentrated on the *strategy* side (the hard part); implementation is comparatively mechanical:
- **Researcher** → `gemini-3-flash` (strong, high-quota producer), temp 0.7.
- **Strategy Reviewer** → `gemini-2.5-pro` (most capable free reasoning, for spec soundness + edge), temp 0.0, with a fallback to `gemini-3-flash` on error/throttle.
- **Engineer** → `gemini-3-flash` (code generation), temp 0.3.
- **Code Reviewer** → `gemini-3.1-flash-lite` (mechanical implementation checks), temp 0.0.

Note: `gemini-2.5-pro` is free but heavily rate-limited (~5 RPM, 50-100 RPD); the 3.x Pro models are
paid. The cheap Code Reviewer absorbs the implementation-churn loop, so the Pro Strategy Reviewer is
only invoked on mechanically-clean code — keeping Pro usage bounded. The architecture still
compensates for lightweight models with rigid checklist prompts and deterministic verification.

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

- **Responsibilities:** Owns the *strategy* side of quality. Reviews the spec for soundness
  (look-ahead bias in the logic, ambiguous rules, overfitting, missing risk controls) and — after
  the Code Reviewer clears the implementation — judges **edge**: does the backtested strategy beat
  its buy-and-hold `benchmark_return` with a positive risk-adjusted return? A clean backtest with no
  edge is rejected. There is no separate Risk Manager, so risk soundness lives here too.
- **Routing:** rejections always go back to the **Researcher** (flawed hypothesis); spec approval →
  Engineer, edge approval → `status:done`.
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
- **Routing:** rejections always go back to the **Engineer**; approval → Strategy Reviewer.
- **Output:** A structured verdict (`decision`, `review_markdown`) via structured-output mode.

Rejections from both reviewers share a single cumulative per-issue counter; after
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
