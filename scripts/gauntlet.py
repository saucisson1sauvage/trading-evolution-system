import sys
from pathlib import Path
# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

import subprocess
import json
import argparse
import re
from scripts.paths import PathResolver
from scripts.logger_utils import get_logger

logger = get_logger("gauntlet")

def run_backtest(strategy_name="GeneticAssembler", timerange="20240101-20250101", verbose=False):
    print(f"--- Starting Gauntlet for {strategy_name} ({timerange}) ---")
    
    project_root = PathResolver.get_project_root()
    config_path = project_root / "config.json"
    
    # Verify binary path
    import shutil
    freqtrade_bin = shutil.which("freqtrade")
    if not freqtrade_bin:
        logger.error(f"Freqtrade binary not found at {freqtrade_bin}")
        print(f"Error: Freqtrade binary not found at {freqtrade_bin}")
        return None
    
    cmd = [
        freqtrade_bin, "backtesting",
        "--strategy", strategy_name,
        "--timerange", timerange,
        "--config", str(config_path),
        "--userdir", str(project_root / "user_data"),
        "--timeframe", "5m",
        "--timeframe-detail", "1m"
    ]
    
    if verbose:
        print(f"Executing: {' '.join(cmd)}")
    
    try:
        print(f"Executing backtest...")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("Backtest finished successfully.")
        
        output = result.stdout
        
        # Implement the "Honesty" Rule: If the backtest result shows 0 trades, the score must be 0.0.
        # Search for Total trades in the result output
        trades_match = re.search(r"Total trades\s+\|\s+(\d+)", output)
        total_trades = int(trades_match.group(1)) if trades_match else 0
        
        if total_trades == 0:
            print("Honesty Rule Applied: 0 trades detected. Score: 0.0")
            return 0.0
            
        # Extract Real Scores: Extract "Total profit %" from Freqtrade output
        # Search for the string "Total profit %" and use regex to grab the numeric value.
        profit_match = re.search(r"Total profit %\s+\|\s+([-]?\d+\.\d+)%", output)
        if profit_match:
            score = float(profit_match.group(1))
            print(f"Extracted Profit %: {score}%")
            return score
        else:
            print("Total profit % not found in output. Defaulting to 0.0")
            return 0.0
            
    except subprocess.CalledProcessError as e:
        print(f"Backtest FAILED for {strategy_name}")
        logger.error(f"Backtest failed: {e.stderr}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Run gauntlet backtest for a strategy")
    # Positional argument for strategy name
    parser.add_argument("strategy", nargs="?", default="GeneticAssembler", 
                        help="Name of the strategy to test (default: GeneticAssembler)")
    # Optional flags
    parser.add_argument("--timerange", default="20240101-20250101", help="Timerange for backtest")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    score = run_backtest(strategy_name=args.strategy, timerange=args.timerange, verbose=args.verbose)
    if score is not None:
        print(f"Final Score: {score}")
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
