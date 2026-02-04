"""
TommyTalker Logging System
Centralized logging with file output and toggleable debug mode.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Log directory
LOG_DIR = Path.home() / "Documents" / "TommyTalker" / "logs"

# Global logger instance
_logger: Optional[logging.Logger] = None
_file_handler: Optional[logging.FileHandler] = None


def get_logger() -> logging.Logger:
    """Get the global TommyTalker logger."""
    global _logger
    if _logger is None:
        _logger = setup_logger()
    return _logger


def setup_logger(enabled: bool = True, level: int = logging.DEBUG) -> logging.Logger:
    """
    Setup the centralized logger.
    
    Args:
        enabled: Whether file logging is enabled
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        
    Returns:
        Configured logger instance
    """
    global _logger, _file_handler
    
    # Create logger
    logger = logging.getLogger("TommyTalker")
    logger.setLevel(level)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler (always active)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '[%(levelname)s] %(message)s'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler (if enabled)
    if enabled:
        _file_handler = _create_file_handler(level)
        if _file_handler:
            logger.addHandler(_file_handler)
            logger.info(f"Logging to: {_file_handler.baseFilename}")
    
    _logger = logger
    return logger


def _create_file_handler(level: int) -> Optional[logging.FileHandler]:
    """Create file handler with timestamped filename."""
    try:
        # Ensure log directory exists
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create filename with date and time
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_file = LOG_DIR / f"tommytalker_{timestamp}.log"
        
        handler = logging.FileHandler(log_file, encoding='utf-8')
        handler.setLevel(level)
        
        # Detailed format for file
        file_format = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s.%(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(file_format)
        
        return handler
        
    except Exception as e:
        print(f"[Logger] Failed to create file handler: {e}")
        return None


def enable_file_logging():
    """Enable file logging."""
    global _logger, _file_handler
    
    if _logger is None:
        setup_logger(enabled=True)
        return
        
    # Add file handler if not present
    if _file_handler is None or _file_handler not in _logger.handlers:
        _file_handler = _create_file_handler(logging.DEBUG)
        if _file_handler:
            _logger.addHandler(_file_handler)
            _logger.info("File logging enabled")


def disable_file_logging():
    """Disable file logging (keep console only)."""
    global _logger, _file_handler
    
    if _logger and _file_handler and _file_handler in _logger.handlers:
        _logger.removeHandler(_file_handler)
        _file_handler.close()
        _file_handler = None
        _logger.info("File logging disabled")


def get_log_directory() -> Path:
    """Get the log directory path."""
    return LOG_DIR


def get_recent_logs(count: int = 5) -> list[Path]:
    """Get the most recent log files."""
    if not LOG_DIR.exists():
        return []
    
    logs = sorted(LOG_DIR.glob("tommytalker_*.log"), reverse=True)
    return logs[:count]


# Convenience functions
def debug(msg: str, *args, **kwargs):
    """Log debug message."""
    get_logger().debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs):
    """Log info message."""
    get_logger().info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs):
    """Log warning message."""
    get_logger().warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs):
    """Log error message."""
    get_logger().error(msg, *args, **kwargs)


def exception(msg: str, *args, **kwargs):
    """Log exception with traceback."""
    get_logger().exception(msg, *args, **kwargs)
