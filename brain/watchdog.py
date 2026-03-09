import os
import time
import subprocess
import shutil
from datetime import datetime

# CONFIG
AGENT_SCRIPT = "autonomous_agent.py"
LOG_FILE = "/home/saus/crypto_crew/agent_crew.log"
BACKUP_DIR = "/home/saus/crypto_crew/backups"
STRAT_PATH = "/home/saus/freqtrade/user_data/strategies/EvolutionaryVolScaler.py"
HISTORY_FILE = "/home/saus/crypto_crew/gen_history.json"
STALE_THRESHOLD_SEC = 600 # 10 minutes silence = crash (increased)

class Watchdog:
    def __init__(self):
        self.last_check = time.time()

    def log(self, msg):
        print(f"[WATCHDOG] {msg}")
        with open("/home/saus/crypto_crew/watchdog.log", "a") as f:
            f.write(f"[{datetime.now()}] {msg}\n")

    def is_agent_running(self):
        try:
            # Check if the python process with the script name is running
            res = subprocess.run(["pgrep", "-f", AGENT_SCRIPT], capture_output=True, text=True)
            # Filter out the watchdog itself if needed, though pgrep -f usually works fine
            pids = res.stdout.strip().split('\n')
            pids = [p for p in pids if p]
            return len(pids) > 0
        except: return False

    def is_log_stale(self):
        if not os.path.exists(LOG_FILE): return False
        mtime = os.path.getmtime(LOG_FILE)
        return (time.time() - mtime) > STALE_THRESHOLD_SEC

    def perform_recovery(self, diagnosis="RESTART"):
        self.log(f"Executing Recovery Action: {diagnosis}")
        subprocess.run(["/home/saus/crypto_crew/hard_stop.sh"], stdout=subprocess.DEVNULL)
        time.sleep(5)

        self.log("Restarting Crew via resume_crew.sh...")
        # Use nohup to ensure it doesn't die with the watchdog
        subprocess.Popen(["bash", "/home/saus/crypto_crew/resume_crew.sh"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def monitor(self):
        self.log("Watchdog started. Monitoring system health...")
        # INITIAL GRACE PERIOD (Wait for agent to load LLMs)
        time.sleep(120) 
        
        while True:
            alive = self.is_agent_running()
            stale = self.is_log_stale()
            
            if not alive or stale:
                status = "DEAD" if not alive else "STALE"
                self.log(f"CRITICAL: System appears {status}. Attempting RESTART.")
                self.perform_recovery()
                time.sleep(300) # Wait 5 minutes before checking again
            
            time.sleep(60)

if __name__ == "__main__":
    w = Watchdog()
    w.monitor()
