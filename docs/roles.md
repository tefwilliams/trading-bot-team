# Agent Roles (Free-Tier Optimized)

## Manager (Human)

- **Role:** The user. Acts as the **Strategic Product Manager**. 
- **Responsibilities:** Directs the team via GitHub Issues — generates high-level strategy objectives, defines product vision, approves/rejects proposals, and performs final PR merges. Acts as the final safety net for escalated agent failures.

## Researcher

- **Default model:** Gemini 3.1 Flash Lite
- **Responsibilities:** Propose strategy ideas with simple mathematical rationale, cite specific formulas, and define entry/exit conditions in plain, unambiguous English. 
- **Output:** A highly explicit strategy proposal issue. Must use strict step-by-step logic to compensate for lightweight model reasoning.

## Engineer

- **Default model:** Gemini 3.1 Flash Lite
- **Responsibilities:** Translate an approved strategy spec into runnable Python — signal generation, position sizing, backtest harness. Must adhere strictly to the JSON contract and `yfinance` requirements defined in `DEVELOPER_GUIDE.md`.
- **Output:** Code committed to a branch, plus a comment on the originating issue linking to the PR.

## Reviewer

- **Default model:** Gemini 3.1 Flash Lite
- **Responsibilities:** Acts as an adversarial code checker. Because this is a lightweight model, it must use a rigid markdown checklist to evaluate code (checking explicitly for look-ahead bias, logical flaws, and risk-handling gaps) rather than a generalized review.
- **Output:** Rigidly structured review comments on the issue or PR detailing required fixes.

## Backtester (Deterministic Node - Not an LLM)

- **Responsibilities:** 1. **Execution Engine:** Runs the Engineer's generated Python code in an isolated environment. 
  2. **Error Correction:** If code fails, captures the raw Python stack trace and feeds it back to the Engineer (up to a strict limit of 3 retries).
  3. **Archivist:** After a strategy successfully executes and is approved, it archives the final backtest results and performance metrics into the `performance_manifest.csv`.
- **Audit Trail:** Protects the system from LLM hallucinations by acting as the absolute source of truth for portfolio metrics.