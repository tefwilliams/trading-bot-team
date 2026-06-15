# Ticket schema

Created by `scripts/setup_labels.py`.

## Labels

### Status Labels (Routing Logic)
These labels control which LangGraph node processes the issue next. The orchestrator polls for
the first five; the last two are terminal, human-owned states with no node:
- `status:researcher`
- `status:strategy_reviewer`
- `status:engineer`
- `status:backtester`
- `status:code_reviewer`
- `status:done` — strategy approved, waiting for the human to merge the PR
- `status:blocked` — a self-correction or review cap was reached, needs human intervention

### Type labels
- `type:strategy`
- `type:bug`
- `type:infra`

## Issue template: strategy proposal

To be created in `.github/ISSUE_TEMPLATE/`. Fields:

- **Hypothesis** — what market behaviour the strategy exploits
- **Entry rule** — precise conditions
- **Exit rule** — precise conditions
- **Universe** — which instruments
- **Timeframe** — daily, hourly, etc.
- **Position sizing** — fixed, vol-targeted, etc.
- **Risks and assumptions**
- **References**

## Workflow

1. Manager opens an objective issue (`status:researcher`).
2. Researcher posts the strategy proposal and moves to `status:strategy_reviewer`.
3. Strategy Reviewer critiques the spec; if approved it moves straight to `status:engineer` (no human gate).
4. Engineer implements code, opens a PR, and moves to `status:backtester`.
5. Backtester validates the interface and JSON contract and runs the code; on success it moves to
   `status:code_reviewer`, on failure back to `status:engineer` (capped at 3 attempts, then `status:blocked`).
6. Code Reviewer checks the implementation; if approved it moves to `status:strategy_reviewer`,
   otherwise back to `status:engineer`.
7. Strategy Reviewer judges edge vs benchmark; if approved it moves to `status:done`, otherwise back
   to `status:researcher`. (Both reviewers share a cumulative rejection cap → `status:blocked`.)
8. Manager merges the PR (the single human gate), which closes the issue.
