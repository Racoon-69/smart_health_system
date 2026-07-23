"""Environment-driven configuration with secure production defaults."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def database_url() -> str:
    value = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'smart_health.db'}")
    return value.replace("postgres://", "postgresql+psycopg://", 1) if value.startswith("postgres://") else value


class BaseConfig:
    ENV_NAME = "base"
    SECRET_KEY = os.getenv("SECRET_KEY", "development-only-change-me")
    SQLALCHEMY_DATABASE_URI = database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_MB", "8")) * 1024 * 1024
    PRIVATE_UPLOAD_ROOT = os.getenv("PRIVATE_UPLOAD_ROOT", str(BASE_DIR / "instance" / "private_uploads"))
    REPORT_TEXT_LIMIT = 50_000
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_NAME = "smarthealth_session"
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=int(os.getenv("SESSION_MINUTES", "30")))
    WTF_CSRF_TIME_LIMIT = 3600
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_HEADERS_ENABLED = True
    TRUST_PROXY_HEADERS = os.getenv("TRUST_PROXY_HEADERS", "false").lower() == "true"
    AUTO_CREATE_DB = False
    SEED_DEMO_DATA = False
    ALLOW_SELF_REGISTRATION = False
    SMS_ENABLED = os.getenv("SMS_ENABLED", "false").lower() == "true"
    SMS_PROVIDER = os.getenv("SMS_PROVIDER", "twilio")
    SMS_FROM = os.getenv("SMS_FROM", "")
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
    CONTENT_SECURITY_POLICY = (
        "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; "
        "form-action 'self'; img-src 'self' data: blob:; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
        "font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "connect-src 'self' https://cdn.jsdelivr.net https://translate.googleapis.com https://generativelanguage.googleapis.com"
    )


class DevelopmentConfig(BaseConfig):
    ENV_NAME = "development"
    DEBUG = True
    AUTO_CREATE_DB = os.getenv("AUTO_CREATE_DB", "false").lower() == "true"
    SEED_DEMO_DATA = True
    ALLOW_SELF_REGISTRATION = True
    SESSION_COOKIE_SECURE = False


class TestingConfig(BaseConfig):
    ENV_NAME = "testing"
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    AUTO_CREATE_DB = True
    SEED_DEMO_DATA = True
    ALLOW_SELF_REGISTRATION = True
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    SESSION_COOKIE_SECURE = False
    SMS_ENABLED = True
    SMS_PROVIDER = "mock"


class ProductionConfig(BaseConfig):
    ENV_NAME = "production"
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = "https"

    @classmethod
    def validate(cls) -> None:
        if not os.getenv("SECRET_KEY") or len(os.getenv("SECRET_KEY", "")) < 32:
            raise RuntimeError("Production requires SECRET_KEY with at least 32 characters.")
        if cls.SQLALCHEMY_DATABASE_URI.startswith("sqlite"):
            raise RuntimeError("Production requires a PostgreSQL DATABASE_URL.")


config_by_name = {"development": DevelopmentConfig, "testing": TestingConfig, "production": ProductionConfig}
