# Strategy Development Lifecycle

This document defines the standard operating procedure for developing new trading strategies within the team.

## Core Principle: No Manual Intervention
Strategy code in the `strategies/` directory is strictly managed by AI agents. Human managers steer via requirements and reviews but should **never** manually edit implementation files. 

If a backtest fails or an interface is rejected, the system is designed to loop back to the **Engineer** for automated correction based on the logs provided by the **Backtester**.

## Phase 1: Ideation & Research
1. **Manager (Human)** creates an issue with `role:researcher`.
2. **Researcher (AI)** proposes a strategy spec and moves to `role:reviewer`.
3. **Reviewer (AI)** critiques the spec against the Flash Lite checklist constraints. Once `[APPROVED]`, it moves to `role:manager`.

## Phase 2: Implementation
1. **Manager (Human)** reviews the spec. If satisfied, changes label to `role:engineer`.
2. **Engineer (AI)**:
    - Creates a feature branch (`strat/issue-X`).
    - Implements the strategy in `strategies/`.
    - Opens a **Pull Request**.
    - Transitions issue to `role:backtester`. *(Note: Code must compile before logical review).*

## Phase 3: Validation & Self-Correction
1. **Backtester (Deterministic)** executes the PR code. 
    - **Failure Loop:** If execution fails, it captures the stack trace and routes back to `role:engineer` for a fix (Strictly capped at 3 retries).
    - **Success:** If execution succeeds, it posts performance metrics and routes to `role:reviewer`.
2. **Reviewer (AI)** critiques the executed code in the PR for logical flaws and look-ahead bias. 
3. **Manager (Human)** analyzes the metrics and code for final sign-off.

## Phase 4: Integration
1. **Manager (Human)** performs the final code review on the PR.
2. **Manager (Human)** merges the PR. 
    - *Note: Merging automatically closes the issue via the "Closes #X" keyword.*
3. **Archivist (Backtester/System)** logs the approved strategy's final metrics into the `performance_manifest.csv` for the Execution Engine to use.