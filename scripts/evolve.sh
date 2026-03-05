#!/bin/bash
export PYTHONPATH=.

for i in {1..5}
do
  echo "--- Generation $i ---"
  python3 scripts/mutate.py
  ./scripts/validate_and_save.sh
  
  echo "--- Backing up to GitHub ---"
  git push origin main || echo "Push failed, will retry next cycle"
  echo ""
done
