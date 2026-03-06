#!/bin/bash
# Integration Test for Crypto-Crew 4.0
PROJECT_ROOT="/home/saus/crypto-crew-4.0"
LOG_DIR="$PROJECT_ROOT/user_data/logs"
EVO_LOG="$LOG_DIR/evolution.log"

echo "🧪 Starting Integration Test..."

# 1. Check for basic file structure
if [ ! -f "$PROJECT_ROOT/scripts/evolution_engine.py" ]; then
    echo "❌ ERROR: evolution_engine.py missing!"
    exit 1
fi

# 2. Run a dry generation (1 gen, population exists)
echo "🏃 Running 1-generation dry run..."
MARKER="--- TEST START $(date +%s) ---"
echo "$MARKER" >> "$EVO_LOG"

python3 -c "import sys; sys.path.append('scripts'); from evolution_engine import run_loop; run_loop(gens=1)"

# 3. Check for Tracebacks in the log since the marker
echo "🔍 Checking logs for errors since test start..."
# We extract all lines after the marker and look for Traceback
ERROR_FOUND=$(sed -n "/$MARKER/,\$p" "$EVO_LOG" | grep "Traceback")

if [ ! -z "$ERROR_FOUND" ]; then
    echo "❌ ERROR: Traceback detected in current test run!"
    echo "$ERROR_FOUND"
    exit 1
fi

# 4. Verify state and population files
if [ ! -f "$PROJECT_ROOT/user_data/strategies/state.json" ] || [ ! -f "$PROJECT_ROOT/user_data/strategies/population.json" ]; then
    echo "❌ ERROR: State or Population files missing!"
    exit 1
fi

echo "✅ Integration Test PASSED 100%."
exit 0
