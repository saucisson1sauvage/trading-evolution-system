# crypto-crew-4.0: ETH/USDT Genetic Algorithm Bot

## Architecture: Modular JSON-DNA
This project implements a modular strategy framework where trading logic is defined as "DNA" in JSON format. This allows for:
- **Dynamic Blocks:** Reusable technical analysis components.
- **Genetic Evolution:** Automated strategy optimization through historical backtesting.
- **Extensible Pathing:** Unified directory management via `scripts/paths.py`.

## Project Structure
- `user_data/strategies/blocks/`: Modular logic units.
- `user_data/logs/`: Execution and evolution logs.
- `scripts/`: Core utilities and path resolution.
- `tests/`: Unit and integration tests.
