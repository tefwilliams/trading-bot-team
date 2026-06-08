# Strategy Development Lifecycle

This document defines the standard operating procedure for developing new trading strategies within the team.

## Core Principle: No Manual Intervention
Strategy code in the `strategies/` directory is strictly managed by AI agents. Human managers steer via requirements and reviews but should **never** manually edit implementation files. 

If a backtest fails or an interface is rejected, the system is designed to loop back to the **Engineer** for automated correction based on the logs provided by the **Backtester**.

## Phase 1: Ideation & Research
1. **Manager (Human)** creates an issue with `role:researcher`.
2. **Researcher (AI)** proposes a strategy spec and moves to `role:reviewer`.
3. **Reviewer (AI)** critiques the spec. Once `[APPROVED]`, it moves to `role:manager`.

## Phase 2: Implementation
1. **Manager (Human)** reviews the spec. If satisfied, changes label to `role:engineer`.
2. **Engineer (AI)**:
    - Creates a feature branch (`strat/issue-X`).
    - Implements the strategy in `strategies/`.
    - Opens a **Pull Request**.
    - Transitions issue to `role:reviewer`.

## Phase 3: Validation
1. **Reviewer (AI)** critiques the code in the PR.
2. **Backtester (Deterministic)** executes the code and posts performance metrics.
3. **Manager (Human)** analyzes the metrics and code for final sign-off.

## Phase 4: Integration
1. **Manager (Human)** performs the final code review on the PR.
2. **Manager (Human)** merges the PR. 
    - *Note: Merging automatically closes the issue via the "Closes #X" keyword.*