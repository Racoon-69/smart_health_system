"""Compatibility exports for project-defense imports.

The production implementation now uses Flask-SQLAlchemy models and Alembic
migrations under ``healthcare`` instead of application-managed raw SQLite.
"""
from healthcare.extensions import db
from healthcare.models import *  # noqa: F403 - convenient documented compatibility surface
from healthcare.services import SLOT_CAPACITY, TIME_SLOTS, slot_details


def init_db() -> None:
    """Development helper. Production deployments must run ``flask db upgrade``."""
    from flask import current_app
    if current_app.config.get("ENV_NAME") == "production":
        raise RuntimeError("Use database migrations in production.")
    db.create_all()
