# 🤖 AI Trading Bot Team

A personal learning project: a simple algorithmic trading "team" built as a set of AI agents
(Researcher, Engineer, Reviewer) plus a deterministic Backtester, coordinated through GitHub
Issues. The **goal is to learn multi-agent orchestration patterns** — the trading logic itself
is secondary. The agents do the work; a human reviews and merges.

## Architecture at a glance

- **Framework:** [LangGraph](https://langchain-ai.github.io/langgraph/) — stateful agent
  workflow. Here it acts as a thin router: each issue's `status:` label decides which node runs.
- **Models:** Google AI Studio free tier, tiered by role (see `llm.py`) — Researcher on
  `gemini-3.1-flash-lite`, Engineer on `gemini-3-flash`, and the Reviewer (sole quality gate) on
  `gemini-2.5-pro` with an automatic fallback to `gemini-3-flash`. The architecture compensates for
  light models with rigid checklist prompts and deterministic verification (the Backtester).
- **Coordination layer:** GitHub Issues as the ticket board and primary state. Agents read/write
  comments, flip `status:` labels, and open Pull Requests. The human merges.
- **Persistence:** SQLite (`SqliteSaver`) checkpoints LangGraph thread state so internal agent
  history survives restarts. Constraint: `thread_id == issue_number`.

## Agent workflow

```mermaid
graph TD
    Start(("New Strategy Issue<br/>status:researcher")) --> Researcher
    Researcher -- "Proposes spec" --> Reviewer_Spec{"Reviewer<br/>(spec check)"}

    Reviewer_Spec -- "rejected (researcher)" --> Researcher
    Reviewer_Spec -- "approved" --> Engineer

    Engineer -- "Opens PR" --> Backtester

    subgraph "Self-Correction Loop (cap: 3)"
    Backtester -- "Error / 0 trades" --> Engineer
    end

    Backtester -- "3 failures" --> Blocked(("status:blocked<br/>Human investigates"))
    Backtester -- "Pass (has results)" --> Reviewer_Code{"Reviewer<br/>(code check)"}

    Reviewer_Code -- "rejected (engineer)" --> Engineer
    Reviewer_Code -- "3 rejections" --> Blocked
    Reviewer_Code -- "approved" --> Done(("status:done<br/>Human merges PR"))
```

## Agent roles

| Agent | Type | Responsibility |
| :--- | :--- | :--- |
| **Researcher** | LLM | Turns a manager objective into an explicit strategy spec (hypothesis, entry/exit, sizing). |
| **Engineer** | LLM | Translates the approved spec into runnable Python (`pandas` / `pandas_ta` / `yfinance`), commits to a branch, opens a PR. |
| **Backtester** | Deterministic | Statically validates the interface, runs the code in a sandboxed subprocess, parses metrics, and enforces the 3-retry self-correction cap. |
| **Reviewer** | LLM | The single AI quality gate. Checklist-driven review of both the spec and the code, covering correctness, look-ahead bias, **and risk** (position sizing, stop-loss, slippage, overfitting). |
| **Manager** | Human (you) | Sets objectives by opening issues, and performs the final review by merging (or rejecting) the PR. |

The flow has **no intermediate human gates** — agents run end-to-end until the code is either
ready to merge (`status:done`) or stuck (`status:blocked`). The human's review *is* the PR merge.

> **Note:** A Risk Manager and a Historian (performance-manifest archivist) existed in earlier
> versions and are intentionally **not** part of the current pipeline. Risk review now lives in the
> Reviewer. They may be reintroduced later.

## Key features

- **GitHub as the state machine & UI** — transparent audit trail via Issues, `status:` labels, and PR comments.
- **TDD for LLMs** — every strategy must actually execute and produce metrics (the Backtester) before any qualitative review.
- **Bounded self-correction** — the Engineer ⇄ Backtester loop is capped at 3 attempts, then escalates to a human (`status:blocked`).

## Getting started

### Prerequisites
- Python 3.10+
- GitHub Personal Access Token (fine-grained, `repo` scope on this repo)
- Google AI Studio (Gemini) API key

### Installation
1. Clone the repo.
2. Create a `.env` file:
   ```env
   GITHUB_TOKEN=your_token
   GITHUB_REPO=username/trading-bot-team
   GOOGLE_API_KEY=your_gemini_key
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Initialise GitHub labels:
   ```bash
   python scripts/setup_labels.py
   ```
5. (Optional) seed an example strategy issue:
   ```bash
   python scripts/create_first_issue.py
   ```
6. Start the orchestrator:
   ```bash
   python main.py
   ```

## Documentation

- [`DEVELOPER_GUIDE.md`](DEVELOPER_GUIDE.md) — technical invariants and the Engineer ⇄ Backtester contract
- [`docs/architecture.md`](docs/architecture.md) — high-level design and decisions
- [`docs/roles.md`](docs/roles.md) — agent role definitions
- [`docs/lifecycle.md`](docs/lifecycle.md) — strategy development lifecycle
- [`docs/ticket-schema.md`](docs/ticket-schema.md) — GitHub Issues labels & schema
- [`docs/setup.md`](docs/setup.md) — dev machine setup

## Next steps

1. **Historian / Portfolio Manager:** reintroduce metric archiving to a `performance_manifest.csv`, then select strategies by Sharpe/volatility.
2. **Unified execution engine:** run multiple approved strategies against live/paper data.
3. **Alpaca integration:** connect the execution engine for real-time paper trading.

## Out of scope

Real-money trading, real-time data feeds, and production deployment.
