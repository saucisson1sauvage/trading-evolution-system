import logging
import sys
import threading
from pathlib import Path
from scripts.paths import PathResolver

# Thread-safe lock for logger initialization
_logger_lock = threading.Lock()

def get_logger(name: str) -> logging.Logger:
    """
    Returns a thread-safe, lazy-formatted logger writing to user_data/logs/system.log.
    
    The logger uses lazy formatting by default through the standard logging library.
    Thread-safety is ensured during logger setup via a module-level lock.
    """
    logger = logging.getLogger(name)
    
    # Early exit if logger already has handlers configured
    # This check is not sufficient to guarantee thread-safety during setup
    # So we use a lock for the configuration part
    if logger.handlers:
        return logger
    
    with _logger_lock:
        # Double-check inside the lock to prevent race conditions
        if logger.handlers:
            return logger
            
        logger.setLevel(logging.INFO)
        
        # Prevent propagation to root logger to avoid duplicate logs
        logger.propagate = False
        
        # Ensure logs directory exists
        logs_dir = PathResolver.get_logs_path()
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = logs_dir / "system.log"
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # File handler for persistent logging
        file_handler = logging.FileHandler(
            filename=log_file,
            mode='a',
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        
        # Console handler for real-time visibility
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)
        
        return logger
