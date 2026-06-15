# Ticket schema

Created by `scripts/setup_labels.py`.

## Labels

### Status Labels (Routing Logic)
These labels control which LangGraph node processes the issue next. The orchestrator polls for
the first four; the last two are terminal, human-owned states with no node:
- `status:researcher`
- `status:engineer`
- `status:backtester`
- `status:reviewer`
- `status:done` — code approved by the Reviewer, waiting for the human to merge the PR
- `status:blocked` — self-correction cap reached, needs human intervention

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
2. Researcher posts the strategy proposal and moves to `status:reviewer`.
3. Reviewer critiques the spec; if approved it moves straight to `status:engineer` (no human gate).
4. Engineer implements code, opens a PR, and moves to `status:backtester`.
5. Backtester validates the interface and JSON contract and runs the code; on success it moves to
   `status:reviewer`, on failure back to `status:engineer` (capped at 3 attempts, then `status:blocked`).
6. Reviewer performs the qualitative + risk check on the code; if approved it moves to `status:done`.
7. Manager merges the PR (the single human gate), which closes the issue.
