#!/bin/bash
# Master evolution loop

for i in {1..5}
do
  echo "--- Generation $i ---"
  python3 scripts/mutate.py
  ./scripts/validate_and_save.sh
  echo ""
done
