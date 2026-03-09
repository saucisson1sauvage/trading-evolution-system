#!/bin/bash
# High Resource Start
# 6 Cores, Max RAM (safely 12GB to avoid swap), All GPUs

/home/saus/crypto-crew-4.0/brain/hard_stop.sh
pkill -f watchdog.py
sleep 2

CORES=6
RAM=12

# STRICT THREAD LIMITS
export OMP_NUM_THREADS=6
export MKL_NUM_THREADS=6
export OPENBLAS_NUM_THREADS=6
export VECLIB_MAXIMUM_THREADS=6
export NUMEXPR_NUM_THREADS=6
export JOBLIB_NUM_THREADS=6

echo "Starting Agent Crew in HIGH RESOURCE mode ($CORES cores, ${RAM}GB RAM)..."

# Apply taskset directly to the main process so all children inherit affinity
nohup taskset -c 0,1,2,3,4,5 python3 /home/saus/crypto-crew-4.0/brain/autonomous_agent.py $CORES $RAM > /home/saus/crypto-crew-4.0/brain/agent_crew.log 2>&1 &
AGENT_PID=$!

# Start the memory monitor
nohup /home/saus/crypto-crew-4.0/brain/monitor_mem.sh $AGENT_PID 12582912 > /home/saus/crypto-crew-4.0/brain/monitor_high.log 2>&1 &

echo "Agent Crew started with PID $AGENT_PID. Starting Watchdog..."

# START WATCHDOG
nohup python3 /home/saus/crypto-crew-4.0/brain/watchdog.py > /home/saus/crypto-crew-4.0/brain/watchdog_std.log 2>&1 &

echo "System Fully Active."
