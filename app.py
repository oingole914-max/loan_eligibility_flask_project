"""Loan Eligibility Prediction System — Flask application entry point.

Run locally:
    python app.py
or:
    flask --app app run --debug
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import click
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_wtf.csrf import CSRFError
from sqlalchemy.exc import SQLAlchemyError

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

from config import Config  # noqa: E402  (must load .env first)
from extensions import csrf, db, login_manager  # noqa: E402
from ml.metrics import get_performance_summary  # noqa: E402
from ml.predictor import ModelLoadError, get_predictor  # noqa: E402
from models import User  # noqa: E402
from repositories import UserRepository  # noqa: E402
from routes import register_blueprints  # noqa: E402
from utils.formatting import (  # noqa: E402
    format_date,
    format_datetime,
    format_inr,
    format_inr_thousands,
    format_loan_term,
    format_number,
    format_percent,
    initials,
    title_case,
)
from utils.validators import (  # noqa: E402
    validate_applicant_name,
    validate_email,
    validate_password,
)

def create_app(config_class=Config) -> Flask:
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config_class)

    secret_key = app.config.get("SECRET_KEY") or ""
    if len(secret_key) < 32 or secret_key.lower().startswith("replace-with"):
        raise RuntimeError(
            "SECRET_KEY is missing, too short, or still set to the example value. "
            "Copy .env.example to .env and generate a random SECRET_KEY of at "
            "least 32 characters before starting the application."
        )

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    _configure_logging(app)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to continue."
    login_manager.login_message_category = "warning"
    login_manager.session_protection = "strong"

    register_blueprints(app)
    _register_template_helpers(app)
    _register_error_handlers(app)
    _register_security_headers(app)
    _register_cli(app)

    # Create tables for a smooth first academic run. Set AUTO_CREATE_DB=0 for
    # production and manage schema migrations separately.
    if app.config.get("AUTO_CREATE_DB"):
        with app.app_context():
            try:
                db.create_all()
            except SQLAlchemyError as exc:
                db.session.rollback()
                raise RuntimeError(
                    "Could not create or connect to the database. Check "
                    "DATABASE_URL in .env (SQLite is the default)."
                ) from exc

    # Load the model exactly once per process and fail fast if the pickle is
    # missing or incompatible. Requests never train or reload the model.
    with app.app_context():
        try:
            predictor = get_predictor(app.config["MODEL_PATH"])
            predictor.self_check()
        except ModelLoadError as exc:
            app.logger.critical("Model start-up failed: %s", exc)
            raise RuntimeError(str(exc)) from exc
        app.extensions["loan_predictor"] = predictor
        app.extensions["loan_model_info"] = predictor.info()
        app.extensions["loan_performance"] = get_performance_summary(
            app.config["METRICS_PATH"]
        )

    app.logger.info(
        "Application ready. Database=%s",
        "SQLite" if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite") else "SQL",
    )
    return app


def _configure_logging(app: Flask) -> None:
    level = logging.DEBUG if app.config.get("DEBUG") else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app.logger.setLevel(level)


def _register_template_helpers(app: Flask) -> None:
    app.jinja_env.filters.update(
        {
            "percent": format_percent,
            "number": format_number,
            "inr": format_inr,
            "inr_thousands": format_inr_thousands,
            "datetime": format_datetime,
            "date": format_date,
            "loan_term": format_loan_term,
            "initials": initials,
            "title_case": title_case,
        }
    )

    @app.context_processor
    def inject_globals():
        return {
            "app_name": app.config["APP_NAME"],
            "current_year": datetime.now(timezone.utc).year,
            "model_info": app.extensions.get("loan_model_info", {}),
            "performance": app.extensions.get("loan_performance", {"available": False}),
        }


def _wants_json() -> bool:
    return request.path == "/predict" or request.accept_mimetypes.best == "application/json"


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(400)
    def bad_request(error):
        if _wants_json():
            return jsonify({"error": getattr(error, "description", "Bad request.")}), 400
        return (
            render_template(
                "errors/400.html",
                message=getattr(error, "description", "The request could not be processed."),
            ),
            400,
        )

    @app.errorhandler(403)
    def forbidden(error):
        if _wants_json():
            return jsonify({"error": "You do not have permission to do that."}), 403
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(error):
        if _wants_json():
            return jsonify({"error": "The requested resource was not found."}), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def payload_too_large(error):
        if _wants_json():
            return jsonify({"error": "The request payload is too large."}), 413
        return render_template("errors/400.html", message="The request is too large."), 413

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        app.logger.warning("CSRF validation failed on %s: %s", request.path, error.description)
        if _wants_json():
            return jsonify({"error": "CSRF token missing or expired. Refresh and try again."}), 400
        return (
            render_template(
                "errors/csrf.html",
                message="Your form session has expired. Refresh the page and try again.",
            ),
            400,
        )

    @app.errorhandler(SQLAlchemyError)
    def database_error(error):
        db.session.rollback()
        app.logger.exception("Unhandled database error")
        if _wants_json():
            return jsonify({"error": "A database error occurred. Please try again."}), 500
        return render_template("errors/500.html"), 500

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.exception("Unhandled server error")
        if _wants_json():
            return jsonify({"error": "An unexpected server error occurred."}), 500
        return render_template("errors/500.html"), 500


def _register_security_headers(app: Flask) -> None:
    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), camera=(), microphone=()"
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'",
        )
        if request.is_secure:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )

        endpoint = request.endpoint or ""
        if endpoint.startswith(("admin.", "applications.", "auth.")):
            if endpoint != "auth.admin_login" or request.method == "POST":
                response.headers["Cache-Control"] = "no-store"
        return response


def _register_cli(app: Flask) -> None:
    @app.cli.command("init-db")
    def init_db_command():
        """Create database tables without deleting existing data."""
        try:
            db.create_all()
        except SQLAlchemyError as exc:
            db.session.rollback()
            raise click.ClickException(
                "Database initialisation failed. Check DATABASE_URL in .env."
            ) from exc
        click.echo("Database tables are ready.")

    @app.cli.command("create-admin")
    @click.option("--name", default=None, help="Administrator display name.")
    @click.option("--email", default=None, help="Administrator email address.")
    @click.option(
        "--password",
        default=None,
        help="Administrator password (prompted securely when omitted).",
    )
    @click.option(
        "--update",
        is_flag=True,
        help="Promote/reset an existing account with this email.",
    )
    def create_admin_command(name, email, password, update):
        """Create or update an administrator account."""
        name = (name or app.config.get("ADMIN_NAME") or "Administrator").strip()
        email = (email or app.config.get("ADMIN_EMAIL") or "").strip()
        password = password or app.config.get("ADMIN_PASSWORD") or ""

        cleaned_name, name_error = validate_applicant_name(name)
        cleaned_email, email_error = validate_email(email)
        if name_error:
            raise click.ClickException(name_error)
        if email_error:
            raise click.ClickException(f"ADMIN_EMAIL: {email_error}")
        if not password:
            password = click.prompt(
                "Administrator password", hide_input=True, confirmation_prompt=True
            )
        password_error = validate_password(password)
        if password_error:
            raise click.ClickException(password_error)

        with app.app_context():
            existing = UserRepository.get_by_email(cleaned_email)
            if existing and not update:
                raise click.ClickException(
                    "An account with this email already exists. Use --update to "
                    "reset its password and grant administrator access."
                )
            if existing:
                existing.full_name = cleaned_name
                existing.role = "admin"
                existing.set_password(password)
                db.session.commit()
                click.echo(f"Administrator updated: {cleaned_email}")
            else:
                user = User(
                    full_name=cleaned_name,
                    email=cleaned_email.lower(),
                    role="admin",
                )
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                click.echo(f"Administrator created: {cleaned_email}")


if __name__ == "__main__":
    application = create_app()
    application.run(
        host=application.config.get("HOST", "127.0.0.1"),
        port=application.config.get("PORT", 5000),
        debug=application.config.get("DEBUG", False),
    )
