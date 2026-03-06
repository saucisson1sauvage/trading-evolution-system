#!/bin/bash

# Configuration
GENS_PER_RUN=1
POP_SIZE=20
PROJECT_ROOT="/home/saus/crypto-crew-4.0"

echo "🚀 Starting Crypto-Crew 4.0 FINAL LOOP..."
echo "This loop will run forever (or until you stop it)."

while true; do
    # 1. Run Evolution Engine
    echo "--- [EVOLUTION PHASE] ---"
    python3 -c "import sys; sys.path.append('scripts'); from evolution_engine import run_loop; run_loop(gens=$GENS_PER_RUN, pop_size=$POP_SIZE)"
    
    # 2. Run AI Fixer (Fixes zero-trade genomes using LLM)
    echo "--- [AI FIX PHASE] ---"
    python3 "$PROJECT_ROOT/scripts/ai_fixer.py"
    
    # 3. Final Commit and Push
    echo "--- [SYNC PHASE] ---"
    git add .
    git commit -m "Auto-Update: Gen Complete + AI Fix Applied"
    git push origin main
    
    echo "✅ Cycle Complete. Waiting 10 seconds before next generation..."
    sleep 10
done
