"""
Core configuration management using Pydantic Settings.
All environment variables are loaded from .env file.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "MediSure AI — Healthcare Intelligence Platform"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: list[str] = ["*"]

    # ── Groq LLM — current active models (April 2026) ──────────────────
    # llama3-70b-8192 and llama3-8b-8192 were decommissioned May 2025
    # mixtral-8x7b-32768 decommissioned March 2025
    # Current replacements per console.groq.com/docs/deprecations
    GROQ_API_KEY: str
    GROQ_MODEL_PRIMARY: str = "llama-3.3-70b-versatile"   # replaces llama3-70b-8192
    GROQ_MODEL_FAST: str = "llama-3.1-8b-instant"         # replaces llama3-8b-8192
    GROQ_MODEL_ANALYSIS: str = "llama-3.3-70b-versatile"  # replaces mixtral-8x7b-32768
    GROQ_MAX_TOKENS: int = 4096
    GROQ_TEMPERATURE: float = 0.1
    GROQ_MAX_RETRIES: int = 3
    GROQ_RETRY_DELAY: float = 2.0

    # Database (SQLite for zero-setup, swap to PostgreSQL URL for production)
    DATABASE_URL: str = "sqlite+aiosqlite:///./claims.db"
    DB_POOL_SIZE: int = 5
    DB_ECHO: bool = False

    # ChromaDB Vector Store
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    CHROMA_COLLECTION_POLICIES: str = "insurance_policies"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # OCR
    OCR_ENGINE: str = "easyocr"  # easyocr | pypdf
    OCR_LANGUAGE: list[str] = ["en", "hi"]
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_FILE_TYPES: list[str] = ["pdf", "png", "jpg", "jpeg", "tiff"]

    # Fraud Detection
    FRAUD_HIGH_THRESHOLD: float = 0.75
    FRAUD_MEDIUM_THRESHOLD: float = 0.45
    AUTO_APPROVE_THRESHOLD: float = 0.85
    AUTO_REJECT_FRAUD_THRESHOLD: float = 0.90

    # Claim Limits (INR-focused)
    DEFAULT_CURRENCY: str = "INR"
    AUTO_APPROVE_MAX_AMOUNT_INR: float = 50000.0
    HIGH_VALUE_THRESHOLD_INR: float = 500000.0

    # Security
    SECRET_KEY: str = "change-this-in-production-use-secrets-manager"
    API_KEY_HEADER: str = "X-API-Key"
    ADMIN_API_KEY: str = "admin-key-change-in-production"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: str = ""

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
