#!/bin/bash
# Integration Test Gauntlet for Crypto-Crew 4.0
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/user_data/logs"
EVO_LOG="$LOG_DIR/evolution.log"
DEBUG_LOG="$LOG_DIR/strategy_debug.log"

echo "🧪 Starting Validation Gauntlet..."

# Auto-Diagnostics function
print_diagnostics() {
    echo "--- 🚨 DIAGNOSTICS: evolution.log (Last 50 lines) ---"
    tail -n 50 "$EVO_LOG" || echo "Log file not found."
    echo "--- 🚨 DIAGNOSTICS: strategy_debug.log (Last 50 lines) ---"
    if [ -f "$DEBUG_LOG" ]; then
        tail -n 50 "$DEBUG_LOG"
    else
        echo "strategy_debug.log not found (no exceptions logged)."
    fi
}

# 1. Check for basic file structure
if [ ! -f "$PROJECT_ROOT/scripts/evolution_engine.py" ]; then
    echo "❌ ERROR: evolution_engine.py missing!"
    exit 1
fi

# Ensure log directory exists
mkdir -p "$LOG_DIR"
touch "$EVO_LOG"

# 2. Run a dry generation (1 gen) with Timeboxing (300s)
echo "🏃 Running 1-generation dry run with 300s timeout..."
MARKER="--- TEST START $(date +%s) ---"
echo "$MARKER" >> "$EVO_LOG"

# Timebox the execution to prevent infinite loops
timeout 300s python3 -c "import sys; sys.path.append('scripts'); from evolution_engine import run_loop; run_loop(gens=1)"
EXIT_CODE=$?

if [ $EXIT_CODE -eq 124 ]; then
    echo "❌ ERROR: Engine timed out after 300 seconds (Infinite Loop?)."
    print_diagnostics
    exit 1
elif [ $EXIT_CODE -ne 0 ]; then
    echo "❌ ERROR: Engine exited with code $EXIT_CODE."
    print_diagnostics
    exit 1
fi

# Extract logs for current run
CURRENT_RUN_LOG=$(sed -n "/$MARKER/,\$p" "$EVO_LOG")

# 3. Check for Tracebacks
if echo "$CURRENT_RUN_LOG" | grep -q "Traceback"; then
    echo "❌ ERROR: Traceback detected in current test run!"
    echo "$CURRENT_RUN_LOG" | grep -A 10 -B 2 "Traceback"
    print_diagnostics
    exit 1
fi

# 4. Regression Check: King's Fitness >= 6.2544
KING_FITNESS=$(echo "$CURRENT_RUN_LOG" | grep -oP "KING FITNESS: \K[0-9.]+" | tail -n 1)
if [ -z "$KING_FITNESS" ]; then
    echo "❌ ERROR: Could not find 'KING FITNESS:' in logs."
    print_diagnostics
    exit 1
fi

# Use bc for float comparison
FITNESS_CHECK=$(echo "$KING_FITNESS >= 6.2544" | bc -l)
if [ "$FITNESS_CHECK" -eq 0 ]; then
    echo "❌ ERROR: Regression Detected! King Fitness ($KING_FITNESS) < 6.2544"
    print_diagnostics
    exit 1
fi
echo "✅ King Fitness Verified: $KING_FITNESS"

# 5. Zero-Trade Detector
TOTAL_TRADES=$(echo "$CURRENT_RUN_LOG" | grep -oP "Aggregated Trades: \K[0-9]+" | awk '{s+=$1} END {print s}')
if [ -z "$TOTAL_TRADES" ] || [ "$TOTAL_TRADES" -eq 0 ]; then
    echo "❌ ERROR: Zero trades detected across all evaluations in this run!"
    print_diagnostics
    exit 1
fi
echo "✅ Trade Signals Verified: $TOTAL_TRADES total aggregated trades."

# 6. Verify state and population files
if [ ! -f "$PROJECT_ROOT/user_data/strategies/state.json" ] || [ ! -f "$PROJECT_ROOT/user_data/strategies/population.json" ]; then
    echo "❌ ERROR: State or Population files missing!"
    print_diagnostics
    exit 1
fi

echo "✅ Integration Test PASSED 100%."
exit 0
