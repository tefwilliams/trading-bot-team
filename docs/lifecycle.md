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
2. **Researcher (AI)** proposes a strategy spec and moves it to `status:reviewer`.
3. **Reviewer (AI)** critiques the spec against its checklist.
   - `[APPROVED]` → `status:engineer` (straight to implementation, no human gate).
   - `[REJECTED]` with `[RESEARCHER]` → back to `status:researcher`.

## Phase 2: Implementation
1. **Engineer (AI)**:
   - Creates a feature branch (`strat/issue-X`).
   - Implements the strategy in `strategies/strategy_X.py`.
   - Opens a **Pull Request**.
   - Transitions the issue to `status:backtester`.

## Phase 3: Validation & Self-Correction
1. **Backtester (Deterministic)** validates the interface and executes the PR code.
   - **Failure loop:** on any failure (interface, runtime error, data failure, missing/zero
     results, timeout) it posts the details and routes back to `status:engineer`.
   - **Retry cap:** failures are counted per issue. After **3** consecutive failures the issue
     is escalated to `status:blocked` for a human to investigate — it is no longer retried
     automatically. A successful backtest resets the counter.
   - **Success:** posts performance metrics and routes to `status:reviewer`.
2. **Reviewer (AI)** critiques the executed code (correctness, look-ahead bias, and risk).
   - `[APPROVED]` → `status:done`.
   - `[REJECTED]` with `[ENGINEER]` → back to `status:engineer`.

## Phase 4: Integration (Human)
1. The issue sits at `status:done` with a green backtest and an approved review.
2. **Manager (Human)** performs the final review and merges the PR.
   - Merging automatically closes the issue via the `Closes #X` keyword.

## Terminal states
- `status:done` — code approved by the Reviewer; waiting for the human to merge.
- `status:blocked` — self-correction cap reached; needs human intervention.
