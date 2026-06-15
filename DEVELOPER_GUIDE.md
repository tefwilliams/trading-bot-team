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
| `/nodes/` | LangGraph node execution logic | Every file must house pure function nodes. |
| `/prompts/` | System prompts & LLM instructions | Isolated from code strings; strictly plain text/markdown. |
| `/references/` | Curated quant material for the Researcher | `.md`/`.txt`/`.pdf`; loaded by `references.py` and injected into the Researcher's prompt. PDFs are git-ignored. |
| `/docs/` | System design specifications | Kept high-level; details are offloaded here. |
| `/scripts/` | Utility & Setup scripts | Non-orchestration helper scripts. |
| `state.py` | Graph state schema definitions | Houses the central `AgentState` configuration. |
| `checkpoints.sqlite` | Persistence Layer | Local SQLite database for LangGraph thread persistence. |

---

## 🏗️ LangGraph Invariants & State Philosophy

1. **Pure Functional Node Pattern:** Every LangGraph node must be defined as a function (e.g., `def engineer_node(state: AgentState)`). It must accept `AgentState` as its primary argument and return a `dict` representing only the keys it intends to update or append.
2. **State Mutation Safety:** Nodes must never overwrite arrays or historical sequences in the state directly. Use appending mechanisms (e.g., `operator.add` for message trackers).
3. **GitHub-First State Tracking:** Never update `AgentState["current_role"]` manually inside a running node execution. Instead, call `github.set_status(issue_number, "next_role")`. The orchestration loop in `main.py` will ingest this hook and update the graph router dynamically.
4. **Thread Persistence:** All graph executions must use a `SqliteSaver` checkpointer. The `thread_id` passed to the graph's `config` must always match the `issue_number` to ensure continuity.
5. **Self-Correction Retry Cap:** `AgentState.backtest_retries` counts consecutive backtest failures per issue. The `Backtester` increments it on every failure route back to the `Engineer`; once it reaches `MAX_BACKTEST_RETRIES` (currently 3) the issue is moved to `status:blocked` instead of retrying. A successful backtest resets it to 0. Do not route back to the engineer without going through this counter.
6. **Loop Caps (convergence guarantee):** several per-issue counters bound every loop so an issue always reaches `status:done` or `status:blocked`:
   - `backtest_retries` — consecutive backtest failures (Backtester ⇄ Engineer); reset on a successful backtest; cap `MAX_BACKTEST_RETRIES` (3).
   - `review_rejections` — **per-cycle** churn: Strategy- and Code-Reviewer rejections within one research cycle (via `nodes/review_common.apply_rejection`); **reset to 0 by the Performance Reviewer when it starts a new cycle**; cap `MAX_REVIEW_REJECTIONS` (5).
   - `research_cycles` — Performance-Reviewer "no edge" rejections (distinct strategies tried); never reset; cap `MAX_RESEARCH_CYCLES` (3).
   - `engineer_failures` — consecutive Engineer model/output errors; reset on success; cap `MAX_ENGINEER_FAILURES` (3).
   When a counter trips its cap the issue goes to `status:blocked` **without closing the PR** (leave it open for the human). The Performance Reviewer only closes (and deletes the branch of) the PR on the *continue* path, so the next spec gets a fresh PR off `main`.
7. **Structured Reviewer Verdict:** Every reviewer MUST return a structured `ReviewDecision` (`decision`, `review_markdown`) via `with_structured_output` (the Code Reviewer uses `CodeReviewDecision`, which adds `high_level_summary`; the Engineer uses `EngineerOutput` with `pr_description`/`change_summary`/`code`). Routing keys off `decision` — never re-introduce string scraping of free-text (e.g. matching `[APPROVED]`). Blame is **structural**: the Code Reviewer always routes rejections to the Engineer; the Strategy Reviewer (spec) and Performance Reviewer (edge) always to the Researcher.
8. **Communication Channels (issue vs PR):** The **issue is the strategy channel** (one spec-level note per implemented spec) and the **PR is the implementation channel** (the full iteration history). Each node reads through the matching `github_utils` helper so feedback is never invisible to its consumer:
   - Reads — Researcher & Strategy Reviewer: `get_issue_context`; Engineer & Code Reviewer: `get_full_context` (issue + PR); Performance Reviewer: `get_pr_context` (PR only).
   - Writes — Researcher/Strategy Reviewer → issue; Engineer & Backtester → PR; Code Reviewer → PR, **plus the issue on approval** (its `high_level_summary`, the spec-level "implemented" note); Performance Reviewer → issue, and **on rejection it closes the PR** (after noting it) so the next spec gets a fresh PR.
   - Never post agent feedback to a channel its consumer does not read. (This is why the Engineer reads the PR — its feedback from the Backtester and Code Reviewer lives there.)

---

> **Note on tool-calling:** Agents do **not** currently use LangChain tool-calling. Nodes call
> `github_utils` helpers directly and the LLM only returns text. There is no `/tools/` directory.
> If tool-calling agents are introduced later, add `/tools/` with `@tool` definitions (Pydantic
> `args_schema`, exhaustive docstrings) and re-document it here first.

---

## 📝 The "Self-Correction" Contract (Engineer ⇄ Backtester)

The interplay between the `Engineer` agent and the `Backtester` agent represents the critical engine of this infrastructure.

### 1. The JSON Results Contract
The `Engineer` agent **MUST** generate execution code that writes its output directly to a file located at `os.environ['BACKTEST_RESULTS_PATH']`.

The JSON payload structure must adhere strictly to these keys and value types:
* **Required Keys:** `total_return`, `max_drawdown`, `sharpe_ratio`, `total_trades`, `benchmark_return`.
* `benchmark_return` is the buy-and-hold return of the strategy's primary instrument over the same window, used by the Reviewer to judge whether the strategy has any edge.
* **Value Types:** Strictly raw floats or integers. **Never** include formatting symbols or wrapped strings (e.g., use `0.15`, do not use `"15%"`).

### 2. The yfinance Requirement
When writing data acquisition scripts using `yfinance`:
* Always explicitly declare `interval='1d'`.
* **MultiIndex Flattening:** `yfinance` returns a MultiIndex DataFrame if requesting multiple tickers or specific fields. Always execute this sanitization check immediately after loading data:
  ```python
  if isinstance(df.columns, pd.MultiIndex):
      df.columns = df.columns.get_level_values(0)
  ```

### 3. Indicator Libraries
Use `pandas` or `pandas_ta` for indicators. **Never import `talib` / `TA-Lib`** — it is not
installed in the sandbox and will crash the backtest.