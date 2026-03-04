#!/bin/bash
# Low Resource Start
# 1 Core (2 threads), 6GB RAM, All GPUs

/home/saus/crypto_crew/hard_stop.sh
sleep 2

CORES=1 # taskset will handle thread mapping if cores are hyperthreaded
RAM=6

# STRICT THREAD LIMITS for Python/ML/OpenBLAS (Low Res = 2 threads)
export OMP_NUM_THREADS=2
export MKL_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export VECLIB_MAXIMUM_THREADS=2
export NUMEXPR_NUM_THREADS=2
export JOBLIB_NUM_THREADS=2

echo "Starting Agent Crew in LOW RESOURCE mode ($CORES core, ${RAM}GB RAM)..."

nohup taskset -c 0,1 python3 /home/saus/crypto_crew/autonomous_agent.py $CORES $RAM > /home/saus/crypto_crew/agent_crew.log 2>&1 &
AGENT_PID=$!

# Start the memory monitor
nohup /home/saus/crypto_crew/monitor_mem.sh $AGENT_PID 6291456 > /home/saus/crypto_crew/monitor_low.log 2>&1 &

echo "Agent Crew started with PID $AGENT_PID. Monitoring log: agent_crew.log"
