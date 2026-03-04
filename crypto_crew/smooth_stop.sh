#!/bin/bash
echo "Gracefully stopping Agent processes..."
pkill -TERM -f "autonomous_agent.py"
pkill -TERM -f "freqtrade"
echo "Termination signals sent. Processes will exit after current tasks."
