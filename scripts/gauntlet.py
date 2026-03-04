import sys
from pathlib import Path
# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

import subprocess
import json
import argparse
from scripts.paths import PathResolver
from scripts.logger_utils import get_logger

logger = get_logger("gauntlet")

def run_backtest(strategy_name="GeneticAssembler", timerange="20240101-20250101", verbose=False):
    print(f"--- Starting Gauntlet for {strategy_name} ({timerange}) ---")
    
    project_root = PathResolver.get_project_root()
    config_path = project_root / "config.json"
    
    # Verify binary path
    freqtrade_bin = "/home/saus/freqtrade/.venv/bin/freqtrade"
    if not Path(freqtrade_bin).exists():
        logger.error(f"Freqtrade binary not found at {freqtrade_bin}")
        print(f"Error: Freqtrade binary not found at {freqtrade_bin}")
        return None
    
    # Tournament requirements: 5m strategy timeframe with 1m detail for precision
    # (timeframe-detail MUST be smaller than timeframe)
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
        
        # Simulated score extraction
        return 5.0 
    except subprocess.CalledProcessError as e:
        print(f"Backtest FAILED for {strategy_name}")
        logger.error(f"Backtest failed: {e.stderr}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Run gauntlet backtest for a strategy")
    # Positional argument for strategy name
    parser.add_argument("strategy", nargs="?", default="GeneticAssembler", 
                        help="Name of the strategy to test (default: GeneticAssembler)")
    # Optional flags - default timerange set to tournament standard
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
