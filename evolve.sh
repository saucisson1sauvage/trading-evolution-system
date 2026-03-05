#!/bin/bash

# Configuration
STRATEGY="GeneticAssembler"
ROUNDS=100 # Set to a very high number or use "while true"

echo "🏆 Starting the Crypto-Crew Perpetual Tournament..."

for ((i=1; i<=ROUNDS; i++))
do
    echo "-------------------------------------------"
    echo "🔄 ROUND $i: ARCHITECTING..."
    
    # 1. AI Proposes new DNA/Blocks
    # Replace with your actual API key or ensure it's in your env
    python3 scripts/ai_propose.py
    
    echo "⚔️ ROUND $i: RUNNING GAUNTLET..."
    
    # 2. Run the backtest and update the league
    python3 scripts/league_manager.py --run-gauntlet
    
    echo "📊 CURRENT STANDINGS:"
    # 3. Show the leaderboard
    python3 scripts/league_manager.py --rank
    
    # Optional: Small sleep to avoid API rate limits
    sleep 5
done
