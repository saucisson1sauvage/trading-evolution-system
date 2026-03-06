#!/bin/bash
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd $PROJECT_ROOT || exit 1

git add user_data/strategies/genomes/hall_of_fame.json user_data/strategies/population.json user_data/strategies/state.json user_data/strategies/genomes/*.json user_data/logs/*.log
git commit -m "Auto-Update: Genetic Memory Sync (Vault & Population)"
git push origin main
