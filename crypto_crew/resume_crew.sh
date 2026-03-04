#!/bin/bash
# DO NOT START WATCHDOG HERE - Watchdog starts this script.
/home/saus/crypto_crew/hard_stop.sh
sleep 2
CORES=6
RAM=12
echo "Resuming Agent Crew in HIGH RESOURCE mode ($CORES cores, ${RAM}GB RAM)..."
nohup taskset -c 0,1,2,3,4,5 python3 /home/saus/crypto_crew/autonomous_agent.py $CORES $RAM > /home/saus/crypto_crew/agent_crew.log 2>&1 &
AGENT_PID=$!
nohup /home/saus/crypto_crew/monitor_mem.sh $AGENT_PID 12582912 > /home/saus/crypto_crew/monitor_high.log 2>&1 &
echo "Agent Crew started with PID $AGENT_PID. Monitoring log: agent_crew.log"
