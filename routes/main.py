"""Public pages and service health."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, render_template
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from repositories import ApplicationRepository

bp = Blueprint("main", __name__)


@bp.get("/")
def home():
    try:
        application_count = ApplicationRepository.count()
    except SQLAlchemyError:
        current_app.logger.exception("Could not count applications for the home page")
        db.session.rollback()
        application_count = None
    return render_template("home.html", application_count=application_count)


@bp.get("/health")
def health():
    predictor = current_app.extensions.get("loan_predictor")
    model_ready = predictor is not None

    database_status = "ok"
    try:
        db.session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        current_app.logger.exception("Database health check failed")
        db.session.rollback()
        database_status = "error"

    status = "ok" if model_ready and database_status == "ok" else "degraded"
    payload = {
        "status": status,
        "model": predictor.info() if model_ready else {"ready": False},
        "database": database_status,
    }
    return jsonify(payload), (200 if status == "ok" else 503)
