# scripts/prod_settings.py

import os
import secrets
from dotenv import load_dotenv
from pathlib import Path

# Load environment overrides
load_dotenv()

# === Base Directories ===
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"

# === Secure Secrets ===
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "secure-admin-token")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-o4-mini")

# === Feature Toggles ===
ENABLE_REBUILD_INDEX = os.getenv("ENABLE_REBUILD_INDEX", "false").lower() == "true"

# === Debug Mode ===
DEBUG = False  # Always False in production

# === Allowed Hosts ===
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# === Directories ===
UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(BASE_DIR / "data/uploads"))
REPORTS_DIR = os.getenv("REPORTS_DIR", str(BASE_DIR / "reports"))
FRAMEWORK_DIR = os.getenv("FRAMEWORK_DIR", str(BASE_DIR / "data/frameworks"))
INDEX_DIR = os.getenv("INDEX_DIR", str(BASE_DIR / "data/faiss"))
JWT_SECRET = os.getenv("JWT_SECRET") or secrets.token_urlsafe(64)

# === Security Headers ===
SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), camera=()"
}

# === Logging Configuration ===
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose"
        },
        "file": {
            "level": "WARNING",
            "class": "logging.FileHandler",
            "filename": str(LOG_DIR / "prod_warnings.log"),
            "formatter": "verbose"
        }
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
}

# === Rate Limits ===
RATE_LIMITS = {
    "upload": os.getenv("RATE_LIMIT_UPLOAD", "5/minute"),
    "rebuild": os.getenv("RATE_LIMIT_REBUILD", "2/hour"),
}

# === Settings object (optional for clean import)
class Settings:
    DEBUG = DEBUG
    SECRET_KEY = SECRET_KEY
    ADMIN_TOKEN = ADMIN_TOKEN
    JWT_SECRET = JWT_SECRET
    OPENAI_API_KEY = OPENAI_API_KEY
    OPENAI_MODEL = OPENAI_MODEL
    ENABLE_REBUILD_INDEX = ENABLE_REBUILD_INDEX

    ALLOWED_HOSTS = ALLOWED_HOSTS
    UPLOAD_DIR = UPLOAD_DIR
    REPORTS_DIR = REPORTS_DIR
    FRAMEWORK_DIR = FRAMEWORK_DIR
    INDEX_DIR = INDEX_DIR

    SECURITY_HEADERS = SECURITY_HEADERS
    LOGGING_CONFIG = LOGGING_CONFIG
    RATE_LIMITS = RATE_LIMITS

settings = Settings()
