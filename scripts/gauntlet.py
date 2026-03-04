import subprocess
import sys
import json
from pathlib import Path
from scripts.paths import PathResolver
from scripts.logger_utils import get_logger

logger = get_logger("gauntlet")

def run_backtest(strategy_name="GeneticAssembler", timerange="20240101-20250101"):
    print(f"--- Starting Gauntlet for {strategy_name} ({timerange}) ---")
    
    project_root = PathResolver.get_project_root()
    config_path = project_root / "config.json"
    
    # Check if config file exists
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        print(f"Error: Config file not found at {config_path}")
        return None
    
    # Use python3 -m freqtrade to avoid path issues
    cmd = [
        "python3", "-m", "freqtrade", "backtesting",
        "--strategy", strategy_name,
        "--timerange", timerange,
        "--config", str(config_path),
        "--userdir", str(project_root / "user_data")
    ]
    
    try:
        print(f"Executing backtest...")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("Backtest finished successfully.")
        
        # In a real scenario, we would parse result.stdout for the 'Total Profit %'
        # For this tournament, we'll simulate a score extraction or use a dummy for now
        # until the full league logic is wired.
        return 5.0 # Placeholder profit score
    except subprocess.CalledProcessError as e:
        print(f"Backtest FAILED for {strategy_name}")
        logger.error(f"Backtest failed: {e.stderr}")
        return None

if __name__ == "__main__":
    score = run_backtest()
    if score is not None:
        print(f"Final Score: {score}")
    else:
        sys.exit(1)
