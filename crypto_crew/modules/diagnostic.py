import os
import sys

# Add root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.runner import FreqtradeRunner
from modules.strategy import StrategyManager
from modules.qa import QAManager
from crew_agents import Crew

# --- SETTINGS ---
STRATEGY_NAME = "EvolutionaryVolScaler"
STRAT_PATH = "/home/saus/freqtrade/user_data/strategies/EvolutionaryVolScaler.py"
CONFIG = "/home/saus/freqtrade/user_data/config.json"
USER_DIR = "/home/saus/freqtrade/user_data"
PYTHON = "/home/saus/freqtrade/.venv/bin/python"
MAIN = "/home/saus/freqtrade/freqtrade/main.py"
BACKUP_DIR = "/home/saus/crypto_crew/backups"

def main():
    runner = FreqtradeRunner(PYTHON, MAIN, CONFIG, USER_DIR)
    strategy_mgr = StrategyManager(STRAT_PATH, BACKUP_DIR)
    crew = Crew()
    qa = QAManager(runner, strategy_mgr, crew)
    
    ok, report = qa.run_all_checks()
    if ok:
        print("\nDIAGNOSTIC PASSED: System is ready.")
    else:
        print("\nDIAGNOSTIC FAILED: Please fix the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
