# 🧠 Crypto-Crew 4.0: Project Soul & Architecture

**If you are reading this after a memory wipe or starting a new session, this document serves as your absolute Ground Truth.**

## 1. Core Purpose & High-Level Architecture
Crypto-Crew 4.0 is a **Genetic Programming (GP) Trading Engine** built on top of the **Freqtrade** algorithmic trading framework. 
Rather than hardcoding trading rules, the system dynamically discovers and evolves trading strategies using a survival-of-the-fittest loop.

### The Decoupled Architecture
The system is divided into two distinct halves:
- **The Execution Shell (`user_data/strategies/GPTreeStrategy.py`)**: A Freqtrade `IStrategy` that does not contain trading logic. Instead, it reads a JSON genome (`current_genome.json`) representing an Abstract Syntax Tree (AST) of logic, and recursively evaluates it using vectorized mathematical primitives.
- **The Evolution Brain (`scripts/evolution_engine.py`)**: An external Python script that generates populations of random AST genomes, spawns Freqtrade subprocesses to test them, extracts their "Fitness" (Profit/Drawdown/Trades), and uses Genetic Algorithms (Crossover, Mutation, Selection) to evolve better strategies over generations.

## 2. Tech Stack & Dependencies
- **Core Framework**: Freqtrade (`v2026.3-dev-ac8f408` or compatible Freqtrade V3 Interface).
- **Language**: Python 3.12+
- **Data Manipulation**: `pandas`, `numpy` (Strictly Vectorized operations, NO `.apply()` or `for` loops in indicators).
- **Indicators Library**: `pandas_ta` (Provides standard indicators like RSI, EMA, SMA, BBands).
- **Version Control**: Git (Automated committing/pushing is integrated into the evolution loop).

## 3. Coding Standards & Conventions
- **Strict Vectorization**: Any function in `gp_blocks.py` must operate on entire Pandas Series at once.
- **Pathing Safety**: Freqtrade often changes the execution working directory. All Python scripts must resolve paths dynamically using absolute paths relative to the project root (e.g., using `pathlib.Path(__file__).parent`). Hardcoded relative strings (like `"user_data/..."`) are forbidden.
- **Fault Tolerance (The "Gatekeeper" Mentality)**: The Evolution Engine generates *random* code. The `GPTreeStrategy` must wrap evaluations in `try/except` blocks to prevent Freqtrade from crashing on bad math (e.g., NaN comparisons). If an error occurs, it should log the error and default to `0` (no signal), allowing the engine to give it a `0.0` fitness and move on.
- **Regex Parsing**: `evolution_engine.py` extracts backtest results by parsing the `STDOUT` terminal table via Regex, rather than relying on Freqtrade's fragile JSON export paths.

## 4. Recent Progress & Immediate Mission
- **Recently Completed**: Restored Deep Genetic Programming Logic. The `evolution_engine.py` now supports recursive tree generation, Crossover (sub-branch swapping), Point/Subtree Mutation, and Population Persistence (`population.json`). The pipeline is fully verified with a 2-individual test run and successful Git synchronization.
- **Current Mission**: Expand the Primitive Library and Tune the Fitness Function. We must integrate all functions from `gp_blocks.py` (e.g., `is_trending_up`, `is_volatile`, `volume_spike`) into the `GPTreeStrategy.py` evaluation loop. Additionally, we need to improve the fitness function to penalize Drawdown and reward high Sharpe/Sortino ratios, rather than just raw profit and trade count. Finally, start a 100-generation evolution run on `ETH/USDT` 5m data.

## 5. Constraints & Protocols
- **Trading Target**: Currently optimized for `ETH/USDT` on Binance Spot.
- **Data Availability**: High-density `1m` and `5m` candle data exists in `user_data/data/binance/` from `2024-10-01` to `2026-03-05`.
- **System Synchronization**: After every successful generational evaluation, the system automatically runs `git commit` and `git push`. DO NOT break this loop. Ensure `GITHUB_PAT` authentication remains silent.
- **Architecture Mapping**: Always run `python3 scripts/generate_architecture_map.py` if you create or modify files so the dynamic `PROJECT_MAP.md` stays up to date. Read `PROJECT_MAP.md` if you need to remember where a specific block or script lives.

---

### **Workflow Note for Agents:**
- **Gemini CLI**: Handles environmental prep, data downloading, log checking, and generating high-level Aider prompts.
- **Aider**: Handles the surgical file edits, logic rewrites, and deep Python refactoring. Use the `WHY/HOW/WHAT` prompt structure when delegating from Gemini to Aider.
