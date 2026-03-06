#!/bin/bash
PROJECT_ROOT="/home/saus/crypto-crew-4.0"
cd $PROJECT_ROOT || exit 1

git add user_data/strategies/genomes/hall_of_fame.json user_data/strategies/population.json user_data/strategies/state.json user_data/strategies/genomes/*.json user_data/logs/*.log
git commit -m "Auto-Update: Genetic Memory Sync (Vault & Population)"
git push origin main
