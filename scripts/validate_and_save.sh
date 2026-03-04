#!/bin/bash
export PYTHONPATH=.
echo "Running Gatekeeper validation..."
if python3 scripts/gatekeeper.py; then
    echo "VALIDATION PASSED - COMMITTING"
    git add .
    git commit -m "feat: passed gatekeeper validation"
else
    echo "VALIDATION FAILED - ROLLING BACK"
    git checkout -- config.json scripts/gatekeeper.py scripts/validate_and_save.sh 2>/dev/null
    # We don't want to wipe the whole repo if we are just setting it up
    echo "Note: Rollback limited to key files to allow recovery."
    tail -n 5 user_data/logs/system.log
fi
