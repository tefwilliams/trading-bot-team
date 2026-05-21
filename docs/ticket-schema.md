# Ticket schema (planned)

Status: design only. To be implemented as the next step after agent scaffolding.

## Labels

### Role labels (who should act next)
- `role:researcher`
- `role:engineer`
- `role:reviewer`
- `role:manager` (awaiting human input)

### Stage labels (where in the workflow)
- `stage:proposal`
- `stage:approved-spec`
- `stage:implementation`
- `stage:review`
- `stage:backtest`
- `stage:done`
- `stage:rejected`

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

1. Manager opens an objective issue (`role:researcher`, `stage:proposal`).
2. Researcher comments with a filled strategy proposal, sets `stage:review`, `role:reviewer`.
3. Reviewer comments with critique; either `stage:approved-spec` or back to `stage:proposal`.
4. Manager approves moving to implementation; `role:engineer`, `stage:implementation`.
5. Engineer opens a PR, comments with link; `stage:review`, `role:reviewer`.
6. Reviewer reviews PR; either approves to `stage:backtest` or kicks back.
7. Backtester runs, posts results; `stage:done` or `stage:rejected`.
