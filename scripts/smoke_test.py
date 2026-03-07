"""
Smoke Test for Genome Validation
Runs a 7-day backtest to verify basic functionality before full evaluation.
"""
import json
import subprocess
import re
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CURRENT_GENOME_FILE = PROJECT_ROOT / "user_data" / "current_genome.json"
SMOKE_CONFIG_FILE = PROJECT_ROOT / "user_data" / "smoke_config.json"

def find_latest_data_date() -> str:
    """
    Find the most recent date in the data directory to use for smoke testing.
    Returns a string in format YYYYMMDD for the last available day.
    """
    data_dir = PROJECT_ROOT / "user_data" / "data"
    if not data_dir.exists():
        # Fallback to a recent date if data directory doesn't exist
        return "20250301"
    
    # Look for feather files (common data format in freqtrade)
    # The data is organized in subdirectories like binance/ETH_USDT-5m.feather
    exchange_dirs = list(data_dir.iterdir())
    if not exchange_dirs:
        # Fallback to a recent date
        return "20250301"
    
    # Get all feather files
    feather_files = []
    for exchange_dir in exchange_dirs:
        if exchange_dir.is_dir():
            feather_files.extend(exchange_dir.glob("*.feather"))
    
    if not feather_files:
        # Fallback to current date minus 7 days
        week_ago = datetime.now() - timedelta(days=7)
        return week_ago.strftime("%Y%m%d")
    
    # Get the most recent file by modification time
    latest_file = max(feather_files, key=lambda f: f.stat().st_mtime)
    
    # Use current date as end date (data is up to now)
    # For smoke test, we want the last 7 days, so end date is today
    today = datetime.now()
    return today.strftime("%Y%m%d")

def generate_smoke_timerange() -> str:
    """
    Generate a 7-day timerange ending with the latest available data.
    """
    end_date_str = find_latest_data_date()
    
    # Parse end date
    try:
        end_dt = datetime.strptime(end_date_str, "%Y%m%d")
    except ValueError:
        # If parsing fails, use current date
        end_dt = datetime.now()
    
    # Make sure end date is not in the future
    today = datetime.now()
    if end_dt > today:
        end_dt = today
    
    # Calculate start date (7 days before)
    start_dt = end_dt - timedelta(days=7)
    start_date = start_dt.strftime("%Y%m%d")
    end_date = end_dt.strftime("%Y%m%d")
    
    timerange = f"{start_date}-{end_date}"
    logger.info(f"Smoke test timerange: {timerange}")
    return timerange

def create_smoke_config():
    """
    Create a modified configuration for smoke testing.
    """
    # Load the main config
    main_config_path = PROJECT_ROOT / "config.json"
    if not main_config_path.exists():
        logger.error("Main config.json not found")
        return False
    
    try:
        with open(main_config_path, 'r') as f:
            config = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load main config: {e}")
        return False
    
    # Modify for smoke testing
    config["max_open_trades"] = 1
    config["stake_amount"] = 10  # Fixed small amount
    config["dry_run_wallet"] = 1000  # Ensure enough for testing
    
    # Save smoke config
    try:
        with open(SMOKE_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info("Smoke test config created")
        return True
    except Exception as e:
        logger.error(f"Failed to save smoke config: {e}")
        return False

def run_smoke_test(genome: dict) -> bool:
    """
    Run a 7-day backtest on the genome.
    Returns True if the test passes (at least 1 trade), False otherwise.
    """
    # Save genome to current_genome.json
    try:
        CURRENT_GENOME_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CURRENT_GENOME_FILE, 'w') as f:
            json.dump(genome, f, indent=2)
        logger.info(f"Genome saved for smoke test")
    except Exception as e:
        logger.error(f"Failed to save genome: {e}")
        return False
    
    # Create smoke config
    if not create_smoke_config():
        return False
    
    # Generate timerange
    timerange = generate_smoke_timerange()
    
    # Run backtest
    freqtrade_bin = str(Path(sys.executable).parent / "freqtrade")
    
    command = [
        freqtrade_bin, "backtesting",
        "--strategy", "GPTreeStrategy",
        "--timerange", timerange,
        "--config", str(SMOKE_CONFIG_FILE),
        "--userdir", str(PROJECT_ROOT / "user_data"),
        "--cache", "none",
        "--timeframe", "5m"  # Use 5m timeframe for faster testing
    ]
    
    try:
        logger.info(f"Starting smoke test with command: {' '.join(command)}")
        start_time = time.time()
        res = subprocess.run(command, capture_output=True, text=True, timeout=30)
        elapsed = time.time() - start_time
        
        if res.returncode != 0:
            logger.warning(f"Smoke test failed with return code {res.returncode}")
            logger.debug(f"STDOUT: {res.stdout[:500]}")
            logger.debug(f"STDERR: {res.stderr[:500]}")
            return False
        
        # Check for trades in output
        output = res.stdout
        
        # Look for trade count in the summary table
        # Try multiple patterns to be robust
        patterns = [
            r"GPTreeStrategy\s+[|│]\s+(\d+)\s+[|│]",
            r"Total trades\s*:\s*(\d+)",
            r"Trades\s*:\s*(\d+)",
            r"(\d+)\s+trades"
        ]
        
        trades = 0
        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                try:
                    trades = int(match.group(1))
                    break
                except (ValueError, IndexError):
                    continue
        
        if trades > 0:
            logger.info(f"Smoke test completed in {elapsed:.1f}s with {trades} trades")
            return True
        else:
            # Check if there were any errors in the output
            if "error" in output.lower() or "exception" in output.lower():
                logger.warning("Errors found in smoke test output")
            logger.info(f"Smoke test completed in {elapsed:.1f}s with 0 trades")
            return False
                
    except subprocess.TimeoutExpired:
        logger.error("Smoke test timed out after 30 seconds")
        return False
    except Exception as e:
        logger.error(f"Smoke test exception: {e}")
        return False

def main():
    """
    Main function for standalone testing.
    """
    if len(sys.argv) > 1:
        # Load genome from file
        genome_path = Path(sys.argv[1])
        try:
            with open(genome_path, 'r') as f:
                genome = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load genome from {genome_path}: {e}")
            sys.exit(1)
    else:
        # Load from current_genome.json
        if not CURRENT_GENOME_FILE.exists():
            logger.error("No genome file provided and current_genome.json not found")
            sys.exit(1)
        try:
            with open(CURRENT_GENOME_FILE, 'r') as f:
                genome = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load current_genome.json: {e}")
            sys.exit(1)
    
    logger.info("Starting smoke test...")
    success = run_smoke_test(genome)
    
    if success:
        logger.info("✅ Smoke test PASSED")
        sys.exit(0)
    else:
        logger.error("❌ Smoke test FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()
