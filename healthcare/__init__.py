"""Application factory for the Smart Health platform."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix

# Configuration classes evaluate environment values at import time.
load_dotenv()

from .config import config_by_name  # noqa: E402 - dotenv must load before configuration imports
from .extensions import csrf, db, limiter, login_manager, migrate, socketio  # noqa: E402


def create_app(config_name: str | None = None, test_config: dict | None = None) -> Flask:
    name = config_name or os.getenv("FLASK_ENV", "development")
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=str(Path(__file__).parent.parent / "templates"),
        static_folder=str(Path(__file__).parent.parent / "static"),
    )
    app.config.from_object(config_by_name.get(name, config_by_name["development"]))
    if test_config:
        app.config.update(test_config)
    if app.config.get("ENV_NAME") == "production":
        config_by_name["production"].validate()
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["PRIVATE_UPLOAD_ROOT"]).mkdir(parents=True, exist_ok=True)
    for folder in ("reports", "photos"):
        Path(app.config["PRIVATE_UPLOAD_ROOT"], folder).mkdir(exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db, compare_type=True)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    socketio.init_app(app)

    if app.config.get("TRUST_PROXY_HEADERS"):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

    from .auth import register_auth_routes
    from .routes import register_public_routes
    from .staff import register_staff_routes

    register_auth_routes(app)
    register_public_routes(app)
    register_staff_routes(app)
    register_cli(app)
    register_error_handlers(app)
    register_security_headers(app)

    if app.config.get("AUTO_CREATE_DB"):
        with app.app_context():
            from .seed import seed_database

            db.create_all()
            seed_database()
    return app


def register_security_headers(app: Flask) -> None:
    @app.after_request
    def headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Content-Security-Policy", app.config["CONTENT_SECURITY_POLICY"])
        if app.config.get("ENV_NAME") == "production":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if request.path.startswith(
            (
                "/dashboard",
                "/appointments",
                "/chat",
                "/staff",
                "/profile",
                "/payment",
                "/private",
                "/report-result",
                "/photo-result",
            )
        ):
            response.headers["Cache-Control"] = "no-store, max-age=0"
        return response


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(400)
    def bad_request(error):
        return render_template("error.html", code=400, message="The request could not be validated."), 400

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("error.html", code=403, message="You do not have permission to access this record."), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template("error.html", code=404, message="The page you requested was not found."), 404

    @app.errorhandler(413)
    def too_large(error):
        return render_template("error.html", code=413, message="The upload exceeds the configured limit."), 413

    @app.errorhandler(429)
    def limited(error):
        return render_template("error.html", code=429, message="Too many requests. Please wait and try again."), 429

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        return render_template(
            "error.html", code=500, message="A server error occurred. The event has been logged."
        ), 500


def register_cli(app: Flask) -> None:
    import click
    from sqlalchemy import func, select

    @app.cli.command("seed")
    def seed_command():
        """Insert idempotent non-patient reference data."""
        from .seed import seed_database

        seed_database(include_demo=False)
        print("Reference data seed complete.")

    @app.cli.command("seed-demo")
    def seed_demo_command():
        """Insert local demonstration accounts and records."""
        if app.config.get("ENV_NAME") == "production":
            raise click.ClickException("Demo accounts cannot be seeded in production mode.")
        from .seed import seed_database

        seed_database(include_demo=True)
        print("Development demo seed complete.")

    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.password_option(confirmation_prompt=True)
    def create_admin_command(email: str, password: str):
        """Provision an administrator without a shared bootstrap key."""
        from .models import User, UserRole

        normalized = email.strip().lower()
        if len(password) < 15:
            raise click.ClickException("Password must contain at least 15 characters.")
        if db.session.scalar(select(User).where(func.lower(User.email) == normalized)):
            raise click.ClickException("That email already exists.")
        user = User(email=normalized, role=UserRole.ADMIN, email_verified=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print("Administrator created.")
