#!/bin/bash
# Helper to run the Omniscience test suite within the correct environment.

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Auto-activate local virtual environment if it exists
if [ -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
else
    echo "❌ ERROR: Local virtual environment (.venv) not found."
    echo "Please ensure you are in the project root and have run the setup."
    exit 1
fi

echo "🧪 Running Omniscience Test Suite..."
python3 -m pytest "$PROJECT_ROOT/tests/test_omniscience.py" -v
