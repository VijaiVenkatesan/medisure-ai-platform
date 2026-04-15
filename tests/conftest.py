"""
tests/conftest.py
Sets environment variables for testing before any app module imports.
Uses in-memory SQLite and disables actual LLM/OCR calls by default.
"""
import os
import pytest

# Override env vars BEFORE any app imports resolve settings
os.environ.setdefault("GROQ_API_KEY", "gsk_test_key_not_real")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_claims.db")
os.environ.setdefault("CHROMA_PERSIST_DIR", "./test_chroma_db")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("LOG_FILE", "")


# Ensure test DB is cleaned up
import atexit
import os as _os

def _cleanup():
    for f in ["./test_claims.db", "./test_claims.db-shm", "./test_claims.db-wal"]:
        try:
            _os.remove(f)
        except FileNotFoundError:
            pass
    import shutil
    try:
        shutil.rmtree("./test_chroma_db", ignore_errors=True)
    except Exception:
        pass

atexit.register(_cleanup)
