# Architecture

## Concept

A multi-agent team that researches, implements, and reviews trading strategies. The user (manager) directs the work via a ticket board; agents do the specialised tasks.

## Why this design

- **Learning goal is multi-agent orchestration**, not building a profitable trader. The trading domain is just a concrete substrate for the agent patterns.
- **Stateful workflow with human approval gates** matches how AI agents are typically used at work, so the patterns transfer.

## The Two-Tier System

1. **Strategy Factory (The Agents):** This is the LangGraph workflow. It produces vetted, backtested Python modules stored in `/strategies`. The deterministic `Backtester` node handles isolated execution and the 3-retry error correction loop.
2. **Execution Engine (The Combined Bot):** A master script that dynamically loads approved strategies from the `performance_manifest.csv`, handles portfolio-level risk, and executes trades via a unified API (e.g., Alpaca).

## Framework: LangGraph

Chosen over alternatives because:
- **AutoGen** is more chat-oriented; awkward when the human interface is a ticket board rather than a group chat.
- **CrewAI** leans toward fire-and-forget; less natural for back-and-forth human-in-the-loop.
- **Roll-your-own** is the best for learning internals, but reinventing checkpoints and state management slows the project down.

LangGraph's state graphs and interrupt/checkpoint mechanics map cleanly onto "ticket moves through stages, human approves at gates."

## 🛡️ Technical Guardrails
Technical invariants for state management, the JSON Results Contract, and Pandas robustness are maintained in the root `DEVELOPER_GUIDE.md`. 

**AI Assistants**: You MUST review `DEVELOPER_GUIDE.md` before modifying any agent nodes to ensure the Self-Correction Loop remains functional.

**Robustness Policy**: Agents must perform a "Self-Review" against this contract before finalizing output.

## Coordination: GitHub Issues

Free, has a proper API (PyGithub), and gives a realistic ticket-board feel. Agents create issues, comment on them, transition labels; the human reviews and approves in the GitHub web UI.

Alternative considered: local markdown/SQLite. Rejected for now — GitHub Issues gives a more "real" workplace feel and is accessible from any machine.

## Models: The "Flash Lite" Constraint

- **Constraint:** The system operates entirely on **Gemini 3.1 Flash Lite** due to free-tier API limitations.
- **Architectural Compensation:** Because Flash Lite is a lightweight model, the architecture compensates for its lower reasoning depth via:
  1. **Aggressive System Instructions:** The `llm.py` wrapper must enforce rigid, checklist-based personas (especially for the Reviewer).
  2. **Linear Execution:** Avoiding infinite agent-to-agent chatter to preserve Requests Per Minute (RPM) limits.
  3. **Deterministic Verification:** Heavy reliance on the Python execution environment (the Backtester) to catch flaws, capped strictly at 3 retries.

## Data and execution

- `yfinance` for free historical data
- In-memory backtests with pandas
- No live trading; paper trading via Alpaca is a possible later step

## Out of scope

- Real money trading
- Real-time data feeds
- Live execution infrastructure
- Production deployment