"""Application configuration.

All secrets and environment-specific values are read from environment
variables. Copy ``.env.example`` to ``.env`` before running the project.
"""
from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def normalize_database_url(url: str | None) -> str:
    """Use SQLite by default and normalise common MySQL URLs to PyMySQL."""
    if not url:
        return f"sqlite:///{(BASE_DIR / 'instance' / 'loan_eligibility.db').as_posix()}"
    url = url.strip()
    if url.startswith("mysql://"):
        url = "mysql+pymysql://" + url[len("mysql://"):]
    return url


def resolve_path(value: str | None, default: Path) -> str:
    path = Path(value) if value else default
    if not path.is_absolute():
        path = BASE_DIR / path
    return str(path.resolve())


class Config:
    APP_NAME = os.getenv("APP_NAME", "LoanLens")
    SECRET_KEY = os.getenv("SECRET_KEY", "")

    # Database -------------------------------------------------------------
    SQLALCHEMY_DATABASE_URI = normalize_database_url(os.getenv("DATABASE_URL"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    AUTO_CREATE_DB = env_bool("AUTO_CREATE_DB", True)

    # Model ----------------------------------------------------------------
    MODEL_PATH = resolve_path(os.getenv("MODEL_PATH"), BASE_DIR / "loan_model.pkl")
    METRICS_PATH = resolve_path(
        os.getenv("METRICS_PATH"), BASE_DIR / "model_metrics.json"
    )

    # Sessions and form security ------------------------------------------
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024

    # Pagination -----------------------------------------------------------
    APPLICATIONS_PER_PAGE = 8
    ADMIN_APPLICATIONS_PER_PAGE = 12

    # Administrator bootstrap values (used only by the CLI command) --------
    ADMIN_NAME = os.getenv("ADMIN_NAME", "System Administrator")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

    DEBUG = env_bool("FLASK_DEBUG", False)
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5000"))
