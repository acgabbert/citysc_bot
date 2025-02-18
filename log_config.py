"""
Centralized logging configuration for consistent logging across all modules.
"""
import logging
import logging.handlers
import os
from typing import Optional

# Create logs directory if it doesn't exist
os.makedirs('log', exist_ok=True)

# Common log format
FORMATTER = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def get_console_handler() -> logging.StreamHandler:
    """Create console handler with proper formatting"""
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(FORMATTER)
    return console_handler

def get_file_handler(filename: str, max_bytes: int = 1000000, backup_count: int = 5) -> logging.handlers.RotatingFileHandler:
    """Create rotating file handler with proper formatting"""
    file_handler = logging.handlers.RotatingFileHandler(
        filename=f'log/{filename}',
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setFormatter(FORMATTER)
    return file_handler

def get_logger(logger_name: str) -> logging.Logger:
    """
    Get a logger instance with both console and file handlers.
    
    Args:
        logger_name: Name of the logger, typically __name__
        
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(logger_name)
    
    # Only add handlers if the logger doesn't already have them
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        # Add handlers
        logger.addHandler(get_console_handler())
        logger.addHandler(get_file_handler('debug.log'))
        logger.addHandler(get_file_handler('error.log', max_bytes=2000000, backup_count=2))
        
        # Prevent log messages from being propagated to the root logger
        logger.propagate = False
        
    return logger

def setup_root_logger() -> None:
    """Configure the root logger with rotating file handlers"""
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    
    # Add handlers if they don't exist
    if not root.handlers:
        # Debug log with standard size
        debug_handler = get_file_handler('debug.log')
        debug_handler.setLevel(logging.DEBUG)
        root.addHandler(debug_handler)
        
        # Controller log with medium size
        controller_handler = get_file_handler('controller.log', max_bytes=1000000, backup_count=5)
        controller_handler.setLevel(logging.INFO)
        root.addHandler(controller_handler)
        
        # Error log with larger size
        error_handler = get_file_handler('error.log', max_bytes=2000000, backup_count=2)
        error_handler.setLevel(logging.ERROR)
        root.addHandler(error_handler)

def get_module_logger(name: str, log_file: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    """
    Get or create a logger for a specific module with optional custom file output.
    
    Args:
        name: Logger name (typically __name__)
        log_file: Optional specific log file for this module
        level: Logging level for this module
        
    Returns:
        logging.Logger: Configured logger instance
    """
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Only add handlers if none exist
    if not logger.handlers:
        # Add console handler
        logger.addHandler(get_console_handler())
        
        # Add standard file handlers
        logger.addHandler(get_file_handler('debug.log'))
        logger.addHandler(get_file_handler('error.log', max_bytes=2000000, backup_count=2))
        
        # Add module-specific log file if specified
        if log_file:
            module_handler = get_file_handler(log_file)
            module_handler.setLevel(level)
            logger.addHandler(module_handler)
        
        logger.propagate = False
        
    return logger