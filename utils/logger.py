"""
Logging utility to capture all print statements and errors to a file.
All logs are saved to the utils/logger/ folder with timestamps.
"""
import os
import sys
from datetime import datetime
from pathlib import Path

class TeeLogger:
    """A logger that writes to both console and file simultaneously."""
    
    def __init__(self, log_file_path: str):
        """
        Initialize the logger.
        
        Args:
            log_file_path: Path to the log file (will be created if doesn't exist)
        """
        self.log_file_path = log_file_path
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.log_file = None
        
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        # Open log file in append mode
        self.log_file = open(log_file_path, 'a', encoding='utf-8')
        
        # Write header
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_file.write(f"\n{'='*80}\n")
        self.log_file.write(f"Log started at: {timestamp}\n")
        self.log_file.write(f"{'='*80}\n\n")
        self.log_file.flush()
    
    def write(self, message):
        """Write to both console and file."""
        self.original_stdout.write(message)
        self.log_file.write(message)
        self.log_file.flush()
    
    def flush(self):
        """Flush both streams."""
        self.original_stdout.flush()
        if self.log_file:
            self.log_file.flush()
    
    def close(self):
        """Close the log file and restore original stdout."""
        if self.log_file:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.log_file.write(f"\n{'='*80}\n")
            self.log_file.write(f"Log ended at: {timestamp}\n")
            self.log_file.write(f"{'='*80}\n\n")
            self.log_file.close()
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr

class ErrorLogger:
    """A logger that captures stderr (errors) to both console and file."""
    
    def __init__(self, log_file_path: str):
        """
        Initialize the error logger.
        
        Args:
            log_file_path: Path to the log file
        """
        self.log_file_path = log_file_path
        self.original_stderr = sys.stderr
        self.log_file = None
        
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        # Open log file in append mode
        self.log_file = open(log_file_path, 'a', encoding='utf-8')
    
    def write(self, message):
        """Write errors to both console and file."""
        self.original_stderr.write(message)
        self.log_file.write(f"[ERROR] {message}")
        self.log_file.flush()
    
    def flush(self):
        """Flush both streams."""
        self.original_stderr.flush()
        if self.log_file:
            self.log_file.flush()
    
    def close(self):
        """Close the log file and restore original stderr."""
        if self.log_file:
            self.log_file.close()
        sys.stderr = self.original_stderr

def setup_logging(script_name: str, log_dir: str = "utils/logger"):
    """
    Set up logging for a script.
    
    Args:
        script_name: Name of the script (without .py extension)
        log_dir: Directory to save log files (default: "utils/logger")
    
    Returns:
        Tuple of (TeeLogger, ErrorLogger) instances
    """
    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"{script_name}_{timestamp}.log"
    log_path = os.path.join(log_dir, log_filename)
    
    # Set up stdout and stderr logging
    stdout_logger = TeeLogger(log_path)
    stderr_logger = ErrorLogger(log_path)
    
    sys.stdout = stdout_logger
    sys.stderr = stderr_logger
    
    print(f"Logging to: {log_path}")
    print(f"Script: {script_name}")
    print("-" * 80)
    
    return stdout_logger, stderr_logger

def cleanup_logging(stdout_logger, stderr_logger):
    """Clean up logging and restore original streams."""
    if stdout_logger:
        stdout_logger.close()
    if stderr_logger:
        stderr_logger.close()
