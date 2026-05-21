# trading-bot-team

A personal learning project: a simple algorithmic trading bot built as a team of AI agents (researcher, engineer, reviewer) coordinated by me as the manager. The goal is to learn multi-agent orchestration patterns — the trading logic itself is secondary.

## Architecture at a glance

- **Framework:** LangGraph (stateful agent workflows with human-in-the-loop checkpoints)
- **Models:** Claude (Anthropic) and Gemini (Google), split by role with cross-model review
- **Coordination layer:** GitHub Issues as a ticket board — agents read and write issues, I act as the manager
- **Data:** `yfinance` for historical data, in-memory backtests to start. Paper trading via Alpaca later.

## Status

Project scaffold and design docs only. No agent code yet.

## Documentation

- [`docs/architecture.md`](docs/architecture.md) — high-level design and decisions
- [`docs/roles.md`](docs/roles.md) — agent role definitions and model assignments
- [`docs/ticket-schema.md`](docs/ticket-schema.md) — planned GitHub Issues schema
- [`docs/setup.md`](docs/setup.md) — how to set up a dev machine

## Next steps

1. Define GitHub Issues labels and templates (see `docs/ticket-schema.md`)
2. Write the dual-provider LLM wrapper (`agents/llm.py`)
3. Build the researcher agent and have it open a strategy proposal issue
4. Add engineer and reviewer agents
5. Wire up the LangGraph state machine
