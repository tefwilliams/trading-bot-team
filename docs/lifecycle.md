# Strategy Development Lifecycle

This document defines the standard operating procedure for developing new trading strategies
within the team. Routing is driven by the `status:<role>` label on each GitHub issue.

## Core Principle: No Manual Intervention (until the merge)
Strategy code in the `strategies/` directory is strictly managed by AI agents. The human
manager steers via requirements and the final PR merge but should **never** manually edit
implementation files. There are **no intermediate human approval gates** — agents run
end-to-end until the work is ready to merge (`status:done`) or stuck (`status:blocked`).

## Phase 1: Ideation & Research
1. **Manager (Human)** creates an issue labelled `status:researcher`.
2. **Researcher (AI)** proposes a strategy spec and moves it to `status:strategy_reviewer`.
3. **Strategy Reviewer (AI)** critiques the spec for soundness and returns a structured verdict.
   - `approved` → `status:engineer` (straight to implementation, no human gate).
   - `rejected` → back to `status:researcher`.

## Phase 2: Implementation
1. **Engineer (AI)**:
   - Creates a feature branch (`strat/issue-X`).
   - Implements the strategy in `strategies/strategy_X.py`.
   - Opens a **fresh Pull Request per spec** (the previous spec's PR was closed when its strategy was
     abandoned). While iterating on the *same* spec it reuses that open PR — keeping its description
     current and posting a change-summary comment on the **PR** each iteration. It does not post to
     the issue; the issue stays at the strategy level.
   - Transitions the issue to `status:backtester`.

## Phase 3: Validation & Self-Correction
1. **Backtester (Deterministic)** validates the interface and executes the PR code.
   - **Failure loop:** on any failure (interface, runtime error, data failure, missing/zero
     results, timeout) it posts the details and routes back to `status:engineer`.
   - **Retry cap:** failures are counted per issue. After **3** consecutive failures the issue
     is escalated to `status:blocked` for a human to investigate — it is no longer retried
     automatically. A successful backtest resets the counter.
   - **Success:** posts performance metrics (including benchmark) and routes to `status:code_reviewer`.
2. **Code Reviewer (AI)** checks the *implementation* — contract compliance, look-ahead bias in the
   code, faithfulness to the spec, correctness, pandas hygiene. Posts its review on the **PR**.
   Runs on the cheap model, so it absorbs the bug-fix churn loop.
   - `approved` → posts the spec-level "implemented" note to the **issue**, then `status:performance_reviewer`.
   - `rejected` → back to `status:engineer` (implementation bug).
3. **Performance Reviewer (AI)** judges *edge*: does the backtested strategy beat its buy-and-hold
   benchmark with a positive risk-adjusted return? A clean backtest with poor performance is a
   rejection, not a pass.
   - `approved` → posts the verdict on the **PR**, then `status:done` (ready for the human to merge).
   - `rejected` → notes it on the PR and **closes the PR**, posts a summary to the **issue**, then
     `status:researcher` (the hypothesis has no edge; the next spec gets a fresh PR).

**Loop caps (all escalate to `status:blocked`):**
- **Per-cycle review churn** — Strategy + Code rejections within one cycle, capped at **5**; reset
  when the Performance Reviewer starts a new cycle, so each spec attempt gets a fresh budget.
- **Research cycles** — distinct strategies tried (Performance-Reviewer "no edge" rejections), capped
  at **3**.
- **Backtest retries** (3) and **Engineer failures** (3) as above.

When any cap trips, the issue is blocked **with its PR left open** for inspection. The Performance
Reviewer only closes (and deletes the branch of) a PR when continuing to a new cycle.
   - **Review cap:** rejections are counted per issue. After **3** the issue is escalated to
     `status:blocked`. An approval resets the counter. This bounds both the spec and code review loops.

## Phase 4: Integration (Human)
1. The issue sits at `status:done` with a green backtest and an approved review.
2. **Manager (Human)** performs the final review and merges the PR.
   - Merging automatically closes the issue via the `Closes #X` keyword.

## Terminal states
- `status:done` — code approved by the Reviewer; waiting for the human to merge.
- `status:blocked` — self-correction cap reached; needs human intervention.
