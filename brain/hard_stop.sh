#!/bin/bash
echo "Hard stopping all Agent processes..."
pkill -9 -f "autonomous_agent.py"
pkill -9 -f "freqtrade"
pkill -9 -f "genetic_loop.py"
pkill -9 -f "monitor_mem.sh"
echo "All processes killed."
