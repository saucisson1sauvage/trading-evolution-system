#!/bin/bash
export PYTHONPATH=$PYTHONPATH:.

while true; do
  echo "--- 🧠 AI ARCHITECT: GENERATING NEW DESIGNS ---"
  python3 scripts/ai_propose.py
  
  echo "--- 🛡️ SECURITY GUARD: CHECKING CODE QUALITY ---"
  # This triggers the Gemini CLI role we defined
  gemini-cli "Review the latest blocks in user_data/strategies/blocks/. Fix syntax only. Do not change logic."

  echo "--- 🏟️ THE GAUNTLET: TESTING ALL 5 GLADIATORS ---"
  # This runs the 12-month backtest for everyone in the league
  python3 scripts/league_manager.py --run-gauntlet
  
  echo "--- 📈 REFEREE: RANKING THE LEAGUE ---"
  python3 scripts/league_manager.py --rank
  
  echo "--- 💾 SAVING TO GIT ---"
  git add .
  git commit -m "Tournament Update: Gen $(date +%Y%m%d_%H%M)"
  
  echo "--- 💤 RESTING (60s) ---"
  sleep 60
done
