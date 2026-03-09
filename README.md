# AI-Driven Genetic Programming Evolution Engine

## Overview
This project is an advanced, autonomous trading strategy generator built around **Genetic Programming (GP)** and **Large Language Models (LLMs)**. Instead of manually hardcoding trading rules, this engine represents strategies as JSON-based Abstract Syntax Trees ("DNA") that are dynamically generated, mutated, evaluated, and retired.

The system utilizes a dual-model LLM approach (e.g., Google Gemini 3.1 Flash/Lite) acting as the "Brain", generating new logical trees using a strict registry of technical analysis blocks. These strategies then run a Gauntlet of historical backtests across multiple market regimes via Freqtrade, fighting for survival in an endless evolutionary loop.

## Core Architecture

### 1. The Assembly Line (Evolution Loop)
The core engine (`scripts/evolution_engine.py`) evaluates a population of 6 slots per generation:
- **Slot 1 (The King)**: The highest-performing strategy from the Vault, subjected to micro-mutations to extend its lineage.
- **Slots 2-6 (AI Batch)**: New genomes synthesized by the LLM. This batch includes structural mutations of top-ranking strategies (Candidates) and completely random "Alien" strategies (Outsiders) to inject fresh genetic diversity.

### 2. The Brain (`scripts/ai_batch_generator.py`)
Powered by LLMs utilizing Prefix Caching (a 20k+ character Encyclopedia of successful patterns and valid grammar). 
- It rotates API keys to maintain high throughput and avoid rate limits.
- Implements a strict **Anti-Hallucination Strike System** (halts the engine if the AI repeatedly fails structural validation).
- Outputs exactly formatted JSON GP trees utilizing operators (`AND`, `OR`, `NOT`, `CROSS_UP`), comparators, and indicators (`RSI`, `EMA`, `BB_LOWER`).

### 3. The Shield (`scripts/smoke_test.py`)
Before a full, computationally expensive evaluation, every newly generated genome undergoes a 7-day "Flash Smoke Test" in a forced-buy environment (injected natively into `GPTreeStrategy.py`). If a genome fails to produce valid Freqtrade signals or throws a pandas evaluation error, it is instantly discarded.

### 4. Evaluation & Fitness Mapping
Genomes that pass the Shield are backtested against **5 distinct market regimes** (Recent, Bull, Bear, Crash, and Sideways/Consolidation).
The objective fitness function severely punishes drawdown while rewarding risk-adjusted consistency:
`Fitness = (Total Profit * Avg Sharpe * log(Trades)) / (1 + Max Drawdown)`

The engine also implements **Age Debuffs** to slowly penalize older "Kings" over hundreds of generations, ensuring the population doesn't permanently stagnate on a single local maximum.

### 5. Persistence: The Vault & The Graveyard
- **The Vault (`hall_of_fame.json`)**: An elitist persistence layer storing the top 30 lineages across all time.
- **The Graveyard (`user_data/strategies/graveyard/`)**: Genomes that fail the backtests or fall out of the Vault are mercilessly buried here for potential future data mining.

### 6. Master Generation Ledger & Dashboard
- **The Ledger (`generation_history.json`)**: The immutable pulse of the engine. It records generation numbers, execution times, AI model logs, lineage IDs, and fitness outcomes for every slot in every cycle.
- **The Observatory (`scripts/dashboard.py`)**: A fully real-time Streamlit dashboard that reads the Ledger and Graveyard to render macro-fitness charts, generation deep-dives, backtest details, and AI transcript analysis.

## Key Files
- `user_data/strategies/GPTreeStrategy.py`: The Freqtrade strategy adapter that recursively parses and evaluates the JSON DNA against live pandas OHLCV dataframes.
- `user_data/strategies/gp_blocks.py`: The central registry of all available technical indicators (`num`) and logical operators (`bool`, `comparator`).
- `scripts/evolution_engine.py`: The central orchestrator running the evaluation pipeline.
- `scripts/final_loop.sh`: The infinite execution loop that runs the engine and auto-syncs genetic memory to git.

## Getting Started

**1. Run the Evolution Loop:**
Executes the engine continuously, evolving new strategies and syncing them automatically.
```bash
./scripts/final_loop.sh
```

**2. Launch the AI Quant Observatory:**
Monitor the system's real-time generation metrics, fitness progression, and analyze the failed DNA in the Graveyard.
```bash
./.venv/bin/python3 -m streamlit run scripts/dashboard.py
```