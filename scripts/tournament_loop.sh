#!/bin/bash
export PYTHONPATH=.

while true
do
  echo "--- Starting Tournament Round: $(date) ---"
  
  echo "Phase 1: AI Proposal"
  python3 scripts/ai_propose.py
  
  echo "Phase 2: The Gauntlet"
  python3 scripts/league_manager.py --run-gauntlet
  
  echo "Phase 3: Scoring & Ranking"
  python3 scripts/league_manager.py --rank
  
  echo "Phase 4: Syncing Results"
  git add .
  git commit -m "chore: tournament round update $(date)" || echo "Nothing to commit"
  git push origin main || echo "Push failed, will retry next cycle"
  
  echo "Round Complete. Sleeping for 10 seconds (Development Mode)..."
  sleep 10
done
