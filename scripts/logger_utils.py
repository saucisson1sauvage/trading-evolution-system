import logging
import sys
from pathlib import Path
from scripts.paths import PathResolver

def get_logger(name: str) -> logging.Logger:
    """Returns a thread-safe, lazy-formatted logger writing to user_data/logs/system.log."""
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.INFO)
    
    # Path Resolution
    logs_dir = PathResolver.get_logs_path()
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "system.log"

    # Formatting
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # File Handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console Handler (optional but good for visibility)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
