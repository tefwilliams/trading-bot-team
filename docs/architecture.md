# Architecture

## Concept

A multi-agent team that researches, implements, and reviews trading strategies. The user (manager) directs the work via a ticket board; agents do the specialised tasks.

## Why this design

- **Learning goal is multi-agent orchestration**, not building a profitable trader. The trading domain is just a concrete substrate for the agent patterns.
- **Stateful workflow with human approval gates** matches how AI agents are typically used at work, so the patterns transfer.

## The Two-Tier System

1. **Strategy Factory (The Agents):** This is the LangGraph workflow. It produces vetted, backtested Python modules stored in `/strategies`. The deterministic `Backtester` node handles isolated execution and the 3-retry error correction loop (escalating to `status:blocked` when exhausted).
2. **Execution Engine (The Combined Bot) — *future*:** A master script that dynamically loads approved strategies, handles portfolio-level risk, and executes trades via a unified API (e.g. Alpaca). This depends on a `performance_manifest.csv` produced by a Historian/archivist role, which is **not part of the current pipeline** (see below).

## Current pipeline scope

The active pipeline is: **Researcher → Strategy Reviewer (spec) → Engineer → Backtester → Code Reviewer → Performance Reviewer (edge) → human merge**, with the Backtester ⇄ Engineer self-correction loop in the middle.

Review is split by concern across three reviewers: the **Strategy Reviewer** (`gemini-2.5-pro`) owns spec soundness, the **Code Reviewer** (`gemini-3.1-flash-lite`) owns implementation correctness, and the **Performance Reviewer** (`gemini-3-flash`) owns edge vs benchmark. The **Risk Manager** and **Historian** roles existed in earlier iterations and are intentionally out of scope for now: risk review has been folded into the Strategy Reviewer, and performance-manifest archiving is deferred. The only human gate is the final PR merge.

**Communication channels.** The **issue** is the strategy-level record (spec, reviews, and one "implemented" note per spec) and the **PR** is the implementation log (every Engineer iteration, backtest report, and code review). Each spec attempt gets its own PR: the Performance Reviewer closes the PR when it rejects a strategy, so the next spec opens a fresh one. Each node reads through the matching `github_utils` helper (`get_issue_context` / `get_pr_context` / `get_full_context`) so feedback is always visible to its consumer — see `DEVELOPER_GUIDE.md` for the per-node read/write contract.

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

**The Hybrid State Model:**
- **Coordination Layer (GitHub):** Acts as the primary UI and global state (status labels, comments). Rejected as a primary DB to keep the system accessible and "real-world."
- **Persistence Layer (SQLite):** Uses `SqliteSaver` for internal LangGraph checkpointing. This ensures that internal agent thoughts (`messages`) and graph progress are not lost if the process restarts.

**Constraint:** `thread_id == issue_number`.

## Models: The Free-Tier Constraint

- **Constraint:** The system operates entirely on Google AI Studio **free-tier** models. `gemini-3-flash`
  is the strongest high-quota free model. `gemini-2.5-pro` is the most capable free model but is heavily
  rate-limited (~5 RPM, 50-100 RPD), so it is used for exactly one role. (The 3.x Pro models are
  paid-only since April 2026.)
- **Per-role tiering (see `llm.py`):** Pro is reserved for the single hardest reasoning task. The
  **Strategy Reviewer** (spec soundness) → `gemini-2.5-pro` (fallback `gemini-3-flash`); it fires once
  per research iteration, so the rate limit is comfortable. Researcher, Engineer, and the
  **Performance Reviewer** (edge vs benchmark — largely numeric) → `gemini-3-flash`; the **Code
  Reviewer** (mechanical checks) → `gemini-3.1-flash-lite`. The cheap Code Reviewer absorbs the
  Engineer bug-fix churn loop.
- **Architectural Compensation:** Because these are still lightweight models, the architecture compensates for their lower reasoning depth via:
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