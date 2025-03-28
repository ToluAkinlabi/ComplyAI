# scripts/logger_config.py
# This module configures the logging for the application. It sets up a rotating file handler that logs to a file and a console handler that logs to the console. The log messages include timestamps, log levels, and the name of the logger.

import logging
from logging.handlers import RotatingFileHandler
from loguru import logger
import sys
import os

# Ensure logs directory exists
if not os.path.exists("logs"):
    os.makedirs("logs")

# Remove default logger
logger.remove()

# Console Logger with Color
logger.add(sys.stdout, 
           format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan> | {message}",
           level="INFO")

# Standard File Logger (rotating)
logger.add("logs/complyai.log", 
           rotation="5 MB", 
           retention="10 days", 
           level="INFO", 
           encoding="utf-8",
           enqueue=True)  

# JSON Logger for Cloud Logging (GCP, ELK, etc.)
logger.add("logs/complyai.json", 
           rotation="5 MB", 
           retention="10 days", 
           level="INFO", 
           serialize=True,   # This makes it JSON
           enqueue=True)