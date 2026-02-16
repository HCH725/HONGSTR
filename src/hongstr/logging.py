import logging
import os
import sys
from logging.handlers import RotatingFileHandler

def setup_logging(level: str = "INFO", log_dir: str = "logs", name: str = "hongstr"):
    """
    Configure structured logging to console and rotating file.
    """
    os.makedirs(log_dir, exist_ok=True)
    
    # Root logger
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console Handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    # File Handler (Rotating)
    log_file = os.path.join(log_dir, f"{name}.log")
    fh = RotatingFileHandler(
        log_file, 
        maxBytes=5*1024*1024, # 5MB
        backupCount=5
    )
    fh.setLevel(level)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    logging.info(f"Logging Initialized. Level: {level}, File: {log_file}")
