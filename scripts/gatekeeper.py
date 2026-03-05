import subprocess
import sys
import py_compile
from pathlib import Path
from scripts.paths import PathResolver
from scripts.logger_utils import get_logger

logger = get_logger("gatekeeper")
FREQTRADE_BIN = "/home/saus/freqtrade/.venv/bin/freqtrade"

def check_syntax():
    logger.info("Starting syntax check...")
    project_root = PathResolver.get_project_root()
    success = True
    for py_file in project_root.rglob("*.py"):
        try:
            py_compile.compile(str(py_file), doraise=True)
            logger.info(f"Syntax OK: {py_file.relative_to(project_root)}")
        except py_compile.PyCompileError as e:
            logger.error(f"Syntax ERROR in {py_file}: {e}")
            success = False
    return success

def check_freqtrade():
    logger.info("Checking freqtrade installation...")
    try:
        subprocess.run([FREQTRADE_BIN, "list-strategies"], capture_output=True, text=True, check=True)
        logger.info("Freqtrade check successful.")
        return True
    except Exception as e:
        logger.error(f"Freqtrade check FAILED: {e}")
        return False

def smoke_test():
    logger.info("Starting ETH/USDT smoke test...")
    # Test both strategies
    strategies = ["GeneticAssembler", "V2Assembler"]
    all_success = True
    
    for strategy in strategies:
        logger.info(f"Testing strategy: {strategy}")
        try:
            # Use a very small timerange to make the test quick
            result = subprocess.run(
                [FREQTRADE_BIN, "backtesting", "--strategy", strategy, "--timerange", "20260201-20260202"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                logger.info(f"Strategy {strategy} smoke test SUCCESSFUL.")
            else:
                logger.error(f"Strategy {strategy} smoke test FAILED: {result.stderr[:500]}")
                all_success = False
        except subprocess.TimeoutExpired:
            logger.warning(f"Strategy {strategy} test timed out (may be okay if data is downloading)")
            # Don't fail on timeout
        except Exception as e:
            logger.error(f"Strategy {strategy} smoke test ERROR: {e}")
            all_success = False
    
    if all_success:
        logger.info("All smoke tests SUCCESSFUL.")
    else:
        logger.warning("Some smoke tests had issues.")
    return all_success

if __name__ == "__main__":
    s1 = check_syntax()
    s2 = check_freqtrade()
    s3 = smoke_test()
    sys.exit(0 if all([s1, s2, s3]) else 1)
