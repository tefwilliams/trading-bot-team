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
- **Grounding:** Reads curated material from `references/` (loaded by `references.py`) and prefers
  proven approaches from it, noting which it drew on — rather than relying on the model's memory alone.
- **Output:** An explicit strategy proposal posted to the issue; moves it to `status:strategy_reviewer`.

## Strategy Reviewer

- **Responsibilities:** Reviews the strategy *specification* for soundness before any code is written
  — look-ahead bias in the logic, ambiguous rules, overfitting, plausibility of the hypothesis, and
  risk controls (there is no separate Risk Manager, so risk soundness lives here). This is the hardest
  reasoning task, so it runs on Pro; it fires once per research iteration.
- **Grounding:** reads the same `references/` material as the Researcher to sanity-check the proposal
  against established approaches (reinvented-worse, missing standard risk controls, overfit parameters).
- **Routing:** approval → Engineer; rejection → Researcher.
- **Output:** A structured verdict (`decision`, `review_markdown`) via structured-output mode.

## Engineer

- **Responsibilities:** Translate an approved strategy spec into runnable Python — signal
  generation, position sizing, backtest harness. Must adhere strictly to the JSON results contract
  and the `yfinance` requirements in `DEVELOPER_GUIDE.md`. Uses `pandas` / `pandas_ta` (never `talib`).
- **Output:** Structured `EngineerOutput` (`pr_description`, `change_summary`, `code`). Commits code to
  `strat/issue-X`, opens a **fresh PR per spec** (reusing the open one while iterating on the same
  spec), keeps the PR description current, and posts a change-summary comment **on the PR** each run.
  It does not post to the issue. Moves to `status:backtester`.

## Code Reviewer

- **Responsibilities:** Owns the *implementation* side of quality. Runs after a successful backtest
  and checks contract compliance, look-ahead bias **in the code**, faithfulness to the spec,
  correctness, and pandas hygiene. It does NOT judge whether the strategy is a good idea (that's the
  Strategy Reviewer). On the cheap model, it absorbs the Engineer bug-fix churn loop.
- **Routing:** rejections always go back to the **Engineer**; approval → Performance Reviewer.
- **Output:** Structured `CodeReviewDecision` (`decision`, `review_markdown`, `high_level_summary`).
  Posts the review **on the PR**; **on approval** also posts `high_level_summary` to the **issue** —
  the one spec-level "implemented" note (so the issue gains an entry only once per implemented spec).

## Performance Reviewer

- **Responsibilities:** Judges **edge** — does the backtested strategy beat its buy-and-hold
  `benchmark_return` with a positive risk-adjusted return? A clean backtest with no edge is rejected.
  The judgment is largely numeric, so it runs on the cheaper `gemini-3-flash`. Reads the **PR only**
  (metrics + code) and distils its verdict to the issue.
- **Routing:** approval → posts the verdict on the PR, `status:done` (human merges); rejection →
  notes it on the PR and **closes the PR**, posts a summary to the issue, `status:researcher`.
- **Output:** A structured verdict (`decision`, `review_markdown`) via structured-output mode.
- **Edge-test caveats:** the benchmark is naive buy-and-hold of the *primary instrument* (not a broad
  index); transaction costs and slippage are not modelled (so high-churn edge is overstated); and raw
  return alone can mislead (lower return with much lower drawdown may still be edge). The reviewer is
  told to weigh risk-adjusted performance, not just "beats benchmark."

Loop caps (all → `status:blocked`, PR left open): Strategy + Code rejections share a **per-cycle**
counter (`MAX_REVIEW_REJECTIONS`, 5) that resets each research cycle; the number of research cycles
(Performance-Reviewer "no edge" rejections) is capped by `MAX_RESEARCH_CYCLES` (3). See
`DEVELOPER_GUIDE.md` for all counters.

## Backtester (Deterministic Node — Not an LLM)

- **Responsibilities:**
  1. **Static validation:** AST-checks the required interface (`generate_signals`, `run_backtest`, results contract).
  2. **Execution engine:** runs the Engineer's code in an isolated subprocess (120s timeout).
  3. **Error correction:** on failure, captures the stack trace / report and routes back to the
     Engineer, capped at 3 attempts before escalating to `status:blocked`.
- **Audit trail:** acts as the source of truth for portfolio metrics, protecting the system from LLM hallucinations.

> Earlier versions also had a **Risk Manager** and a **Historian** (manifest archivist). These are
> not part of the current pipeline; risk review now lives in the Strategy Reviewer.
