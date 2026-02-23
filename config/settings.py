"""
Configuration settings for the Patent Document Text Extract Service.
"""

import os
from pathlib import Path


class Settings:
    """Application configuration settings."""

    APP_NAME = "Patent Document Text Extract Service"
    APP_VERSION = "1.0.0"

    BASE_DIR = Path(__file__).parent.parent
    STORAGE_DIR = BASE_DIR / "storage"
    INPUT_DIR = STORAGE_DIR / "input_docs"
    OUTPUT_DIR = STORAGE_DIR / "extracted_output"
    LOGS_DIR = BASE_DIR / "logs"

    SUPPORTED_FORMATS = [".pdf", ".docx", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"]

    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "200"))

    MINERU_METHOD = os.getenv("MINERU_METHOD", "auto")
    MINERU_LANG = os.getenv("MINERU_LANG", "en")

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist."""
        for directory in [cls.INPUT_DIR, cls.OUTPUT_DIR, cls.LOGS_DIR]:
            directory.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
