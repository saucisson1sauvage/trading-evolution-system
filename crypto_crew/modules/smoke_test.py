import os
import sys
import shutil
import json
import time

# Add root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.runner import FreqtradeRunner
from modules.strategy import StrategyManager
from modules.qa import QAManager

# --- TEST SETTINGS ---
STRAT_PATH = "/home/saus/freqtrade/user_data/strategies/EvolutionaryVolScaler.py"
CONFIG = "/home/saus/freqtrade/user_data/config.json"
USER_DIR = "/home/saus/freqtrade/user_data"
PYTHON = "/home/saus/freqtrade/.venv/bin/python"
MAIN = "/home/saus/freqtrade/freqtrade/main.py"
BACKUP_DIR = "/home/saus/crypto_crew/backups_test"
TEST_HISTORY = "/home/saus/crypto_crew/test_history.json"

def run_smoke_test():
    print("🚀 INITIALIZING SMOKE TEST (2 mini-generations)...")
    
    # 1. Setup
    runner = FreqtradeRunner(PYTHON, MAIN, CONFIG, USER_DIR, cores=2)
    strat_mgr = StrategyManager(STRAT_PATH, BACKUP_DIR)
    qa = QAManager(runner, strat_mgr)
    
    # 2. Pre-check
    ok, report = qa.run_all_checks()
    if not ok:
        print(f"❌ QA Check Failed: {report}")
        return False

    # 3. Generation Loop
    for gen in range(1, 3):
        print(f"\n--- SMOKE GEN {gen}/2 ---")
        
        # A. Mock AI Injection
        print("STEP: Injecting Mock Logic...")
        mock_logic = f"dataframe.loc[(dataframe['rsi'] < {20 + gen}), 'enter_long'] = 1"
        new_source = strat_mgr.inject_logic("", mock_logic, "")
        strat_mgr.save_source(new_source)
        
        # B. Mini Hyperopt (1 epoch)
        print("STEP: Running Mini Hyperopt (1 epoch)...")
        res_h = runner.run_hyperopt("EvolutionaryVolScaler", "20260201-20260202", epochs=1)
        if res_h.returncode != 0:
            print("❌ Hyperopt Failed")
            return False
            
        # C. Backtest
        print("STEP: Running Backtest...")
        res_b = runner.run_backtest("EvolutionaryVolScaler", "20260201-20260303")
        metrics = runner.parse_metrics(res_b.stdout)
        print(f"RESULT: Trades={metrics['trades']}, Profit={metrics['profit_pct']}%")
        
        # D. Verify Persistence
        if gen == 1:
            with open(TEST_HISTORY, "w") as f:
                json.dump([{"gen": 1, "metrics": metrics}], f)
        else:
            with open(TEST_HISTORY, "r") as f:
                hist = json.load(f)
            hist.append({"gen": 2, "metrics": metrics})
            with open(TEST_HISTORY, "w") as f:
                json.dump(hist, f)

    # 4. Final Validation
    if os.path.exists(TEST_HISTORY):
        with open(TEST_HISTORY, "r") as f:
            final_hist = json.load(f)
            if len(final_hist) == 2:
                print("\n✅ SMOKE TEST PASSED: Pipeline fully functional.")
                return True
    
    print("\n❌ SMOKE TEST FAILED: History not updated.")
    return False

if __name__ == "__main__":
    success = run_smoke_test()
    if not success:
        sys.exit(1)
