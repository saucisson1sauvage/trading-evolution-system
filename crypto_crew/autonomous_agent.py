import os
import json
import time
import random
import threading
import math
import subprocess
from datetime import datetime

# Import modular components
from crew_agents import Crew
from modules.runner import FreqtradeRunner
from modules.strategy import StrategyManager
from modules.qa import QAManager

# --- SETTINGS ---
PROJECT_DIR = "/home/saus/crypto_crew"
STRATEGY_NAME = "EvolutionaryVolScaler"
STRAT_PATH = "/home/saus/freqtrade/user_data/strategies/EvolutionaryVolScaler.py"
CONFIG = "/home/saus/freqtrade/user_data/config.json"
USER_DIR = "/home/saus/freqtrade/user_data"
PYTHON = "/home/saus/freqtrade/.venv/bin/python"
MAIN = "/home/saus/freqtrade/freqtrade/main.py"
HISTORY_JSON = f"{PROJECT_DIR}/gen_history.json"
LIVE_THINKING = f"{PROJECT_DIR}/ai_thinking.live"
POOL_FILE = f"{PROJECT_DIR}/pool/mating_pool.json"
BACKUP_DIR = f"{PROJECT_DIR}/backups"
AIDER_SCRIPT = f"{PROJECT_DIR}/aider.sh"

class AutonomousAgent:
    def __init__(self, cores, ram_gb):
        self.cores = cores
        self.generation = 1
        self.history = []
        self.candidate_queue = [] 
        self.lock = threading.Lock()
        self.main_task_active = False
        
        # Initialize modules
        self.runner = FreqtradeRunner(PYTHON, MAIN, CONFIG, USER_DIR, cores)
        self.strategy_mgr = StrategyManager(STRAT_PATH, BACKUP_DIR)
        self.crew = Crew()
        self.qa = QAManager(self.runner, self.strategy_mgr)
        
        self.load_history()
        self.brain_thread = threading.Thread(target=self.brain_worker, daemon=True)
        self.brain_thread.start()

    def log(self, msg, type="THINK"):
        with open(LIVE_THINKING, "a") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] [{type}] {msg}\n\n")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def load_history(self):
        if os.path.exists(HISTORY_JSON):
            try:
                with open(HISTORY_JSON, 'r') as f:
                    self.history = json.load(f)
                    if self.history: self.generation = self.history[-1]['gen'] + 1
            except: pass

    def save_history(self, gen_data):
        self.history.append(gen_data)
        with open(HISTORY_JSON, 'w') as f: json.dump(self.history, f, indent=2)

    def calculate_score(self, m):
        if m['trades'] <= 5: return -100
        pf = m.get('profit_factor', 1.0)
        return m['profit_pct'] * pf * math.log10(m['trades'] + 1)

    def aider_fix(self, issue):
        """Calls Aider (DeepSeek-V3) to autonomously fix the strategy or system."""
        self.log(f"CRITICAL ISSUE detected. Summoning Aider (DeepSeek-V3)...", "ARCHITECT")
        
        # Non-interactive aider call
        cmd = [
            "bash", AIDER_SCRIPT, 
            "--no-git", # Prevent git overhead in test loop
            "--message", f"URGENT: The system reported this issue: {issue}. Please fix the code in {STRAT_PATH} or relevant modules to restore functionality. Output only the fix."
        ]
        
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_DIR)
            if res.returncode == 0:
                self.log("Aider fix applied successfully.", "ARCHITECT")
                return True
            else:
                self.log(f"Aider failed to apply fix: {res.stderr}", "ERROR")
                return False
        except Exception as e:
            self.log(f"Error calling Aider: {e}", "ERROR")
            return False

    def brain_worker(self):
        self.log("Background Brain active.", "BRAIN")
        while True:
            try:
                if len(self.candidate_queue) < 10:
                    with open(STRAT_PATH, 'r') as f: base_code = f.read()
                    
                    ind = self.crew.brain.ask("CODER_MODE: Indicators snippet. 8 spaces.", "Gen indicators.")
                    entry = self.crew.brain.ask("CODER_MODE: Entry logic. 8 spaces.", "Gen entry.")
                    exit_l = self.crew.brain.ask("CODER_MODE: Exit logic. 8 spaces.", "Gen exit.")
                    
                    cand_code = self.strategy_mgr.inject_logic(ind, entry, exit_l)
                    while self.main_task_active: time.sleep(10)
                    
                    tmp_strat = f"/tmp/wild_{random.randint(1000,9999)}.py"
                    with open(tmp_strat, "w") as f: f.write(cand_code)
                    
                    res = self.runner.run_backtest("EvolutionaryVolScaler", "20260201-20260303", strategy_path="/tmp")
                    if res.returncode == 0:
                        m = self.runner.parse_metrics(res.stdout)
                        score = self.calculate_score(m)
                        with self.lock:
                            self.candidate_queue.append({"code": cand_code, "score": score, "metrics": m})
                        self.log(f"Queued Outsider (Score: {score:.2f})", "BRAIN")
                time.sleep(30)
            except Exception as e:
                self.log(f"Brain Error: {e}", "ERROR")
                time.sleep(60)

    def run_tournament(self, base_metrics):
        self.log(f"Tournament Gen {self.generation}", "GA")
        self.strategy_mgr.backup()
        
        metrics_str = json.dumps(base_metrics, indent=2)
        bottleneck = self.crew.data_analyst(metrics_str)
        refine_idea = self.crew.creative(bottleneck, "Aggressive")
        
        ind = self.crew.brain.ask("CODER_MODE: Indicators. 8 spaces.", f"Refine: {bottleneck}")
        entry = self.crew.brain.ask("CODER_MODE: Entry. 8 spaces.", f"Fix: {bottleneck}")
        exit_l = self.crew.brain.ask("CODER_MODE: Exit. 8 spaces.", f"Refine: {bottleneck}")
        
        refine_code = self.strategy_mgr.inject_logic(ind, entry, exit_l)
        self.strategy_mgr.save_source(refine_code)
        
        res = self.runner.run_backtest(STRATEGY_NAME, "20260201-20260303", param_file=f"{USER_DIR}/strategies/{STRATEGY_NAME}.json")
        m_refine = self.runner.parse_metrics(res.stdout)
        score_refine = self.calculate_score(m_refine)
        
        results = [{"code": refine_code, "score": score_refine, "metrics": m_refine, "type": "Refine"}]
        with self.lock:
            while self.candidate_queue: results.append(self.candidate_queue.pop(0))
        
        results.sort(key=lambda x: x['score'], reverse=True)
        winner = results[0]
        
        self.strategy_mgr.save_source(winner['code'])
        self.log(f"Winner: {winner.get('type', 'Wild')} ({winner['score']:.2f})", "GA")
        return winner

    def start_loop(self):
        while True:
            try:
                self.main_task_active = False
                
                # QA PHASE WITH AUTONOMOUS AIDER FIXING
                ok, report = self.qa.run_all_checks()
                if not ok:
                    self.log(f"QA Failed: {report}", "CRITICAL")
                    # TRIGGER AIDER FOR SYNTAX ERRORS
                    if not report.get("Syntax", True):
                        self.aider_fix("Syntax error in strategy file.")
                    elif not report.get("Parser", True):
                        self.aider_fix("The Freqtrade metric parser is failing to read results.")
                    
                    time.sleep(60)
                    continue

                self.main_task_active = True
                self.log(f"Generation {self.generation} Start", "SYSTEM")
                
                self.runner.run_hyperopt(STRATEGY_NAME, "20260101-20260303", epochs=50)
                
                res = self.runner.run_backtest(STRATEGY_NAME, "20260201-20260303", param_file=f"{USER_DIR}/strategies/{STRATEGY_NAME}.json")
                base_metrics = self.runner.parse_metrics(res.stdout)
                
                winner = self.run_tournament(base_metrics)
                
                self.save_history({
                    "gen": self.generation, "timestamp": datetime.now().isoformat(),
                    "metrics": winner['metrics'], "score": winner['score']
                })
                
                self.generation += 1
                self.main_task_active = False
                subprocess.run(f"bash {PROJECT_DIR}/export_setup.sh", shell=True, env=os.environ.copy())
                time.sleep(30)
                
            except Exception as e:
                self.log(f"Loop Error: {e}", "ERROR")
                self.aider_fix(f"Loop crash: {e}")
                time.sleep(60)

if __name__ == "__main__":
    import sys
    agent = AutonomousAgent(int(sys.argv[1]), int(sys.argv[2]))
    agent.start_loop()
