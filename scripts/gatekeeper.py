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
    try:
        subprocess.run([FREQTRADE_BIN, "backtesting", "--strategy", "GeneticAssembler", "--timerange", "20260201-"], capture_output=True, text=True, check=True)
        logger.info("Smoke test SUCCESSFUL.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Smoke test FAILED (Expected if strategy missing): {e.stderr}")
        return False

if __name__ == "__main__":
    s1 = check_syntax()
    s2 = check_freqtrade()
    s3 = smoke_test()
    sys.exit(0 if all([s1, s2, s3]) else 1)
