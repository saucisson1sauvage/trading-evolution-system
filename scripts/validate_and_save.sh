#!/bin/bash
# Gatekeeper automation: Commit on success, rollback on failure

export PYTHONPATH=.

echo "Running Gatekeeper validation..."
python3 scripts/gatekeeper.py

if [ $? -eq 0 ]; then
    echo "VALIDATION PASSED - COMMITTING"
    git add .
    git commit -m "feat: passed gatekeeper validation"
else
    echo "VALIDATION FAILED - ROLLING BACK"
    # Rollback everything to last known good state
    git checkout -- .
    git clean -fd
    echo "----------------------------------------"
    echo "Last 10 lines of gatekeeper log:"
    tail -n 10 user_data/logs/system.log
fi
