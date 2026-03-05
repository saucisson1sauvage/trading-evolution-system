#!/usr/bin/env bash
set -euo pipefail

# Set up environment
export PYTHONPATH=.

# Create logs directory if it doesn't exist
mkdir -p user_data/logs

# Run 10 generations of evolution
for i in {1..10}; do
    echo "Starting generation $i"
    
    # Mutate one parameter
    python3 scripts/mutate_v2.py --generation "$i"
    
    # Validate and save the configuration
    ./scripts/validate_and_save.sh
    
    # Run backtest with V2Assembler strategy
    python3 scripts/gauntlet.py V2Assembler
    
    # Commit changes
    git add .
    git commit -m "Evolve: Generation $i - Score PLACEHOLDER" || true
    
    # Push to remote
    git push origin main
    
    # Wait before next generation
    sleep 2
done

echo "Evolution completed for 10 generations"
