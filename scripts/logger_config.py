# scripts/logger_config.py
# This module configures the logging for the application. It sets up a rotating file handler that logs to a file and a console handler that logs to the console. The log messages include timestamps, log levels, and the name of the logger.

import logging
from logging.handlers import RotatingFileHandler
import os

def get_logger(name: str):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Create log directory if not exists
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # Log Formatter
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Rotating File Handler (auto-rotates when logs reach 5MB)
    file_handler = RotatingFileHandler("logs/complyai.log", maxBytes=5*1024*1024, backupCount=5)
    file_handler.setFormatter(formatter)

    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
