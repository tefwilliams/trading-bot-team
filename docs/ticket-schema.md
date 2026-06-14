# Ticket schema (planned)

Status: design only. To be implemented as the next step after agent scaffolding.

## Labels

### Status Labels (Routing Logic)
These labels control which LangGraph node processes the issue next:
- `status:researcher`
- `status:engineer`
- `status:backtester`
- `status:reviewer`
- `status:risk_manager`
- `status:historian`
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

1. Manager opens an objective issue (`status:researcher`).
2. Researcher posts strategy proposal and moves to `status:reviewer`.
3. Reviewer critiques the spec; if approved, it moves to `status:manager`.
4. Manager approves implementation; changes status to `status:engineer`.
5. Engineer implements code and opens a PR; moves to `status:backtester`.
6. Backtester validates code and JSON contract; if successful, moves to `status:reviewer`.
7. Reviewer performs qualitative check; if approved, moves to `status:risk_manager`.
