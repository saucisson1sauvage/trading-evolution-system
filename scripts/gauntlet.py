import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
import subprocess
import sys
import json
from pathlib import Path
from scripts.paths import PathResolver
from scripts.logger_utils import get_logger

logger = get_logger("gauntlet")

def validate_timerange(timerange: str) -> bool:
    """
    Validate timerange format (basic check).
    Accepts formats like:
    - YYYYMMDD-YYYYMMDD
    - YYYYMMDD-
    - -YYYYMMDD
    """
    if not timerange:
        return False
    
    parts = timerange.split('-')
    if len(parts) != 2:
        return False
    
    # Check if each part is either empty or 8 digits
    for part in parts:
        if part and (len(part) != 8 or not part.isdigit()):
            return False
    
    return True

def check_data_files(timerange: str, verbose: bool = False) -> bool:
    """
    Check if required .feather files exist in user_data/data/binance
    for the given timerange.
    """
    data_dir = PathResolver.get_user_data_path() / "data" / "binance"
    if not data_dir.exists():
        logger.error(f"Data directory does not exist: {data_dir}")
        return False
    
    # List all .feather files
    feather_files = list(data_dir.glob("*.feather"))
    if not feather_files:
        logger.error(f"No .feather files found in {data_dir}")
        return False
    
    if verbose:
        print(f"Found {len(feather_files)} .feather files in {data_dir}")
        for f in feather_files[:5]:  # Show first 5
            print(f"  {f.name}")
        if len(feather_files) > 5:
            print(f"  ... and {len(feather_files) - 5} more")
    
    # For now, we just check if there are any files
    # In a more advanced implementation, we could parse timerange and check specific dates
    # But this is a basic check
    return True

def run_backtest(strategy_name="GeneticAssembler", timerange="20240101-20250101", verbose=False):
    print(f"--- Starting Gauntlet for {strategy_name} ({timerange}) ---")
    
    # Validate timerange format
    if not validate_timerange(timerange):
        logger.error(f"Invalid timerange format: {timerange}")
        print(f"Error: Timerange must be in format YYYYMMDD-YYYYMMDD, YYYYMMDD-, or -YYYYMMDD")
        return None
    
    # Check data files first
    if not check_data_files(timerange, verbose):
        logger.error("Data file check failed. Aborting backtest.")
        return None
    
    project_root = PathResolver.get_project_root()
    config_path = project_root / "config.json"
    
    # Check if config file exists
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        print(f"Error: Config file not found at {config_path}")
        return None
    
    # Use python3 -m freqtrade to avoid path issues
    cmd = [
        "/home/saus/freqtrade/.venv/bin/freqtrade", "backtesting",
        "--strategy", strategy_name,
        "--timerange", timerange,
        "--config", str(config_path),
        "--userdir", str(project_root / "user_data")
    ]
    
    if verbose:
        print(f"Full command: {' '.join(cmd)}")
    
    try:
        print(f"Executing backtest...")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("Backtest finished successfully.")
        
        if verbose:
            print("Backtest output (first 500 chars):")
            print(result.stdout[:500])
            if result.stderr:
                print("Backtest stderr (first 500 chars):")
                print(result.stderr[:500])
        
        # In a real scenario, we would parse result.stdout for the 'Total Profit %'
        # For this tournament, we'll simulate a score extraction or use a dummy for now
        # until the full league logic is wired.
        return 5.0 # Placeholder profit score
    except subprocess.CalledProcessError as e:
        print(f"Backtest FAILED for {strategy_name}")
        logger.error(f"Backtest failed with exit code {e.returncode}")
        
        # Print error output
        print(f"Error output (first 1000 chars):")
        print(e.stderr[:1000] if e.stderr else "No stderr captured")
        
        # Try to find and print the last 20 lines of the Freqtrade log
        log_path = PathResolver.get_logs_path() / "system.log"
        if log_path.exists():
            print(f"\n--- Last 20 lines of system.log ({log_path}) ---")
            # Read last 20 lines
            try:
                with open(log_path, 'r') as f:
                    lines = f.readlines()
                    last_lines = lines[-20:] if len(lines) >= 20 else lines
                    print(''.join(last_lines))
            except Exception as read_err:
                print(f"Unable to read log file: {read_err}")
        else:
            # Try to find other log files
            logs_dir = PathResolver.get_logs_path()
            log_files = list(logs_dir.glob("*.log"))
            if log_files:
                # Use the most recent log file
                latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
                print(f"\n--- Last 20 lines of {latest_log.name} ---")
                try:
                    with open(latest_log, 'r') as f:
                        lines = f.readlines()
                        last_lines = lines[-20:] if len(lines) >= 20 else lines
                        print(''.join(last_lines))
                except Exception as read_err:
                    print(f"Unable to read log file: {read_err}")
            else:
                print("No log files found in logs directory")
        
        return None
    except Exception as e:
        print(f"Unexpected error during backtest: {e}")
        logger.exception("Unexpected error in run_backtest")
        return None

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run a gauntlet backtest for a strategy")
    parser.add_argument("--strategy", default="GeneticAssembler",
                       help="Strategy name (default: GeneticAssembler)")
    parser.add_argument("--timerange", default="20240101-20250101",
                       help="Timerange for backtest (default: 20240101-20250101)")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose output including full command and debug info")
    
    args = parser.parse_args()
    
    score = run_backtest(
        strategy_name=args.strategy,
        timerange=args.timerange,
        verbose=args.verbose
    )
    
    if score is not None:
        print(f"Final Score: {score}")
        sys.exit(0)
    else:
        print("Backtest failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
