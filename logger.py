"""
Logging utility for the Music Production Platform.
Provides consistent logging functionality across all modules.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any

# Define log levels with their corresponding methods
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

class MusicPlatformLogger:
    """
    Centralized logger for the Music Production Platform.
    Handles both console and file logging with customizable formats.
    """
    
    _instance: Optional['MusicPlatformLogger'] = None
    _loggers: Dict[str, logging.Logger] = {}
    
    def __new__(cls) -> 'MusicPlatformLogger':
        """Implement singleton pattern for logger."""
        if cls._instance is None:
            cls._instance = super(MusicPlatformLogger, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        """Initialize the logger if it hasn't been initialized yet."""
        if not getattr(self, '_initialized', False):
            self._setup_logging()
            self._initialized = True
    
    def _setup_logging(self) -> None:
        """Set up the basic logging configuration."""
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Define log format
        self.log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        self.date_format = '%Y-%m-%d %H:%M:%S'
        
        # Set the default level
        self.default_level = os.environ.get('LOG_LEVEL', 'INFO')
        
        # Create default formatter
        self.formatter = logging.Formatter(self.log_format, self.date_format)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(LOG_LEVELS.get(self.default_level, logging.INFO))
        
        # Add console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(self.formatter)
        root_logger.addHandler(console_handler)
        
        # Add file handler
        file_handler = RotatingFileHandler(
            os.path.join(logs_dir, 'music_platform.log'),
            maxBytes=10*1024*1024,  # 10 MB
            backupCount=5
        )
        file_handler.setFormatter(self.formatter)
        root_logger.addHandler(file_handler)
        
        # Create separate file for errors
        error_handler = RotatingFileHandler(
            os.path.join(logs_dir, 'errors.log'),
            maxBytes=10*1024*1024,  # 10 MB
            backupCount=5
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(self.formatter)
        root_logger.addHandler(error_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a named logger.
        
        Args:
            name: The name of the logger, typically the module name.
            
        Returns:
            A configured logger instance.
        """
        if name not in self._loggers:
            logger = logging.getLogger(name)
            self._loggers[name] = logger
        
        return self._loggers[name]

# Global function to get a logger
def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger for the specified module.
    
    Args:
        name: The name of the module requiring a logger.
        
    Returns:
        A configured logger instance.
    """
    return MusicPlatformLogger().get_logger(name)
