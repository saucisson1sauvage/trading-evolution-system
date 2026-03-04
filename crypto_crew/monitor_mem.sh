#!/bin/bash
PID=$1
MAX_MEM=${2:-10485760} # Default to 10GB in KB if not provided
echo "Monitoring memory for PID $PID (Max: $MAX_MEM KB)"
while true; do
  if ! ps -p $PID > /dev/null; then
    echo "Process $PID finished."
    break
  fi
  # Get memory of process group
  MEM=$(ps -o rss= --ppid $PID | awk '{s+=$1} END {print s}')
  # Also add the parent process memory
  PARENT_MEM=$(ps -o rss= -p $PID)
  TOTAL_MEM=$((MEM + PARENT_MEM))
  
  if [ $TOTAL_MEM -gt $MAX_MEM ]; then
    echo "Memory limit exceeded ($TOTAL_MEM KB). Killing $PID and children."
    # Kill process group
    kill -- -$PID
    break
  fi
  sleep 5
done
