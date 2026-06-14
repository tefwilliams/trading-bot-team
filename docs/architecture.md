# Architecture

## Concept

A multi-agent team that researches, implements, and reviews trading strategies. The user (manager) directs the work via a ticket board; agents do the specialised tasks.

## Why this design

- **Learning goal is multi-agent orchestration**, not building a profitable trader. The trading domain is just a concrete substrate for the agent patterns.
- **Stateful workflow with human approval gates** matches how AI agents are typically used at work, so the patterns transfer.

## The Two-Tier System

1. **Strategy Factory (The Agents):** This is the current LangGraph workflow. It produces vetted, backtested Python modules stored in `/strategies`.
2. **Execution Engine (The Combined Bot):** A master script that dynamically loads approved strategies from the `performance_manifest.csv`, handles portfolio-level risk, and executes trades via a unified API (e.g., Alpaca).

## Framework: LangGraph

Chosen over alternatives because:
- **AutoGen** is more chat-oriented; awkward when the human interface is a ticket board rather than a group chat.
- **CrewAI** leans toward fire-and-forget; less natural for back-and-forth human-in-the-loop.
- **Roll-your-own** is the best for learning internals, but reinventing checkpoints and state management slows the project down.

LangGraph's state graphs and interrupt/checkpoint mechanics map cleanly onto "ticket moves through stages, human approves at gates."

## 🛡️ Developer Guardrails for AI Coding Assistants

When modifying or creating new agents, AI assistants MUST verify their implementation against these invariants:

1.  **State Integrity**: All nodes must accept `AgentState` and return a dictionary that updates the state. Never bypass the `github_utils.py` manager for state transitions.
2.  **The JSON Contract**: Every implementation of the `Engineer` prompt or the `backtester.py` logic must strictly enforce the use of `os.environ['BACKTEST_RESULTS_PATH']` and the specific keys: `total_return`, `max_drawdown`, `sharpe_ratio`, and `total_trades`.
3.  **Self-Correction Loops**: Ensure the `Backtester` remains deterministic. If a test fails, the node must provide actionable, copy-pasteable feedback to the `Engineer`.
4.  **Pandas Robustness**: `yfinance` data is often MultiIndex. Agents must be instructed to flatten columns immediately using `.get_level_values(0)`.
5.  **Environment Isolation**: Agents should not assume a persistent local filesystem for data; they must use environment variables for paths.

**AI Peer Review Task**: Before finalizing any code for an agent, perform a "System Check" to ensure the logic doesn't break the communication loop between the Engineer and the Backtester.

## Technical Interface Contract

To ensure the Self-Correction Loop functions, all `Engineer` agents must adhere to the following interface:

1. **Inputs**: Use `yfinance` with `interval='1d'`. Flatten MultiIndex columns immediately.
2. **Interface**: 
    - `generate_signals(data)`: Returns a Series of -1, 0, 1.
    - `run_backtest()`: Orchestrates the execution.
3. **Outputs**: Metrics MUST be written to the path specified in `os.environ['BACKTEST_RESULTS_PATH']`.
4. **JSON Schema**: 
    - Keys: `total_return` (float), `max_drawdown` (float), `sharpe_ratio` (float), `total_trades` (int).

**Robustness Policy**: Agents must perform a "Self-Review" against this contract before finalizing output.

## Coordination: GitHub Issues

Free, has a proper API (PyGithub), and gives a realistic ticket-board feel. Agents create issues, comment on them, transition labels; the human reviews and approves in the GitHub web UI.

Alternative considered: local markdown/SQLite. Rejected for now — GitHub Issues gives a more "real" workplace feel and is accessible from any machine.

## Models: Claude + Gemini

- Different models for producer vs. reviewer reduces shared blind spots.
- Default assignment in `docs/roles.md`.
- Single LLM wrapper (`agents/llm.py`, not yet written) hides provider differences behind one function.

## Data and execution

- `yfinance` for free historical data
- In-memory backtests with pandas
- No live trading; paper trading via Alpaca is a possible later step

## Out of scope

- Real money trading
- Real-time data feeds
- Live execution infrastructure
- Production deployment
