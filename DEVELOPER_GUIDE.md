# AI Developer Guide & System Blueprint (Meta-Instructions)

This document serves as the absolute source of truth and global system prompt for AI Coding Assistants (Gemini Code Assist, Agent Mode, etc.) working on this repository. It defines technical invariants, strict schemas, and workspace structures required to maintain the multi-agent orchestration.

---

## 📜 Documentation Maintenance & AI Synchronization Mandate

**Documentation is Code.** To prevent agent logic drift, AI Assistants must strictly adhere to this synchronization workflow:

1. **The Update-First Rule:** Whenever you modify, add, or refactor logic anywhere in the codebase (e.g., adding a validation check to `backtester.py`), you **MUST** simultaneously update this guide or relevant `.md` files in the same file-writing transaction.
2. **Single Source of Truth:** Technical contracts (JSON keys, function signatures, state mutations) live *only* here. Do not duplicate implementation details in `docs/architecture.md`—keep that file purely conceptual to avoid conflicting context.
3. **Keep Context Open:** When writing new code, ensure this file, your target file, and `state.py` are active tabs in the IDE so the local context window retains these parameters.

---

## 📂 Workspace & Directory Blueprint

AI assistants must only create or look for files within this established framework:

| Directory/File | Responsibility | Rule / Invariant |
| :--- | :--- | :--- |
| `/nodes/` | LangGraph node execution logic | Every file must house pure function nodes. (Currently in root). |
| `/tools/` | External agent actions & APIs | Must contain LangChain `@tool` definitions. |
| `/prompts/` | System prompts & LLM instructions | Isolated from code strings; strictly plain text/markdown. |
| `/docs/` | System design specifications | Kept high-level; details are offloaded here. |
| `state.py` | Graph state schema definitions | Houses the central `AgentState` configuration. |
| `checkpoints.sqlite` | Persistence Layer | Local SQLite database for LangGraph thread persistence. |

---

## 🏗️ LangGraph Invariants & State Philosophy

1. **Pure Functional Node Pattern:** Every LangGraph node must be defined as a function (e.g., `def engineer_node(state: AgentState)`). It must accept `AgentState` as its primary argument and return a `dict` representing only the keys it intends to update or append.
2. **State Mutation Safety:** Nodes must never overwrite arrays or historical sequences in the state directly. Use appending mechanisms (e.g., `operator.add` for message trackers).
3. **GitHub-First State Tracking:** Never update `AgentState["current_role"]` manually inside a running node execution. Instead, call `github.set_status(issue_number, "next_role")`. The orchestration loop in `main.py` will ingest this hook and update the graph router dynamically.
4. **Thread Persistence:** All graph executions must use a `SqliteSaver` checkpointer. The `thread_id` passed to the graph's `config` must always match the `issue_number` to ensure continuity.

---

## 🛠️ Tool Creation & Execution Rules

When generating new capabilities or external APIs for agents:
- **Decorators:** Always use the `@tool` decorator from `langchain_core.tools`.
- **Strict Typing:** Every tool must have a robust Pydantic `args_schema` class defined explicitly to prevent model execution halucinations.
- **Semantic Clarity:** Provide exhaustive docstrings inside the tool function. The LLM relies directly on the tool's docstring to evaluate utility and pass arguments.

---

## 📝 The "Self-Correction" Contract (Engineer ⇄ Backtester)

The interplay between the `Engineer` agent and the `Backtester` agent represents the critical engine of this infrastructure.

### 1. The JSON Results Contract
The `Engineer` agent **MUST** generate execution code that writes its output directly to a file located at `os.environ['BACKTEST_RESULTS_PATH']`.

The JSON payload structure must adhere strictly to these keys and value types:
* **Required Keys:** `total_return`, `max_drawdown`, `sharpe_ratio`, `total_trades`.
* **Value Types:** Strictly raw floats or integers. **Never** include formatting symbols or wrapped strings (e.g., use `0.15`, do not use `"15%"`).

### 2. The yfinance Requirement
When writing data acquisition scripts using `yfinance`:
* Always explicitly declare `interval='1d'`.
* **MultiIndex Flattening:** `yfinance` returns a MultiIndex DataFrame if requesting multiple tickers or specific fields. Always execute this sanitization check immediately after loading data:
  ```python
  if isinstance(df.columns, pd.MultiIndex):
      df.columns = df.columns.get_level_values(0)