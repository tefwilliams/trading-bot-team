# trading-bot-team

A personal learning project: a simple algorithmic trading bot built as a team of AI agents (researcher, engineer, reviewer) coordinated by me as the manager. The goal is to learn multi-agent orchestration patterns — the trading logic itself is secondary.

## Architecture at a glance

- **Framework:** LangGraph (stateful agent workflows with human-in-the-loop checkpoints)
- **Models:** Gemini 3.1 Flash Lite (Google) used across all roles for cost-efficiency.
- **Coordination layer:** GitHub Issues as a ticket board — agents read and write issues, I act as the manager
- **Workflow:** Pull Request-based implementation loop. Automated backtesting via subprocess execution.

## Status

**Active Development.** Core orchestration loop is functional.
- Researcher, Engineer, Reviewer, Risk Manager, and Product Manager agents are implemented.
- Automated Backtester node is operational.
- GitHub issue-to-PR workflow is established.

## Documentation

- [`docs/architecture.md`](docs/architecture.md) — high-level design and decisions
- [`docs/roles.md`](docs/roles.md) — agent role definitions and model assignments
- [`docs/ticket-schema.md`](docs/ticket-schema.md) — planned GitHub Issues schema
- [`docs/setup.md`](docs/setup.md) — how to set up a dev machine

## Next steps

1. Implement automated strategy performance tracking (Historian node).
2. Integrate Alpaca API for paper trading execution.
