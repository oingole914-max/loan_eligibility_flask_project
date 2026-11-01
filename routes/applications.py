"""Loan application submission, prediction results and customer history."""
from __future__ import annotations

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from ml.predictor import PredictionError, get_predictor
from ml.schema import MODEL_FEATURES
from repositories import ApplicationRepository
from utils.validators import validate_application_form

bp = Blueprint("applications", __name__)

STATUS_FILTERS = {"all", "eligible", "not_eligible"}
SORT_OPTIONS = {"newest", "oldest"}


def _default_values() -> dict[str, str]:
    return {
        "applicant_name": current_user.full_name,
        "Dependents": "0",
        "CoapplicantIncome": "0",
        "Loan_Amount_Term": "360",
    }


def _display_values() -> dict[str, str]:
    values = {field: "" for field in ("applicant_name", *MODEL_FEATURES)}
    for field in values:
        values[field] = request.form.get(field, "")
    return values


@bp.route("/apply", methods=["GET", "POST"])
@login_required
def apply():
    errors: dict[str, str] = {}
    values = _default_values()
    service_error: str | None = None

    if request.method == "POST":
        values = _display_values()
        cleaned, errors = validate_application_form(request.form)

        if not errors:
            try:
                prediction = get_predictor().predict(cleaned)
            except PredictionError:
                current_app.logger.exception("Prediction failed while submitting an application")
                service_error = (
                    "The prediction service is temporarily unavailable. "
                    "Your details are still in the form; please try again."
                )
            else:
                try:
                    application = ApplicationRepository.create(
                        current_user, cleaned, prediction
                    )
                except SQLAlchemyError:
                    db.session.rollback()
                    current_app.logger.exception("Could not save an application")
                    abort(500)
                flash("Your eligibility assessment is ready.", "success")
                return redirect(url_for("applications.result", application_id=application.id))

    return render_template(
        "application_form.html",
        values=values,
        errors=errors,
        service_error=service_error,
        model_features=MODEL_FEATURES,
    )


def _get_visible_application(application_id: int):
    application = ApplicationRepository.get(application_id)
    if application is None:
        abort(404)
    is_owner = application.user_id == current_user.id
    is_admin = getattr(current_user, "is_admin", False)
    if not is_owner and not is_admin:
        abort(404)
    return application, is_owner, is_admin


@bp.get("/result/<int:application_id>")
@login_required
def result(application_id: int):
    application, is_owner, is_admin = _get_visible_application(application_id)
    return render_template(
        "application_detail.html",
        application=application,
        is_new=True,
        admin_view=is_admin and not is_owner,
        back_url=url_for("applications.history") if not (is_admin and not is_owner) else url_for("admin.applications"),
    )


@bp.get("/history")
@login_required
def history():
    query = (request.args.get("q") or "").strip()[:120]
    status = (request.args.get("status") or "all").lower()
    sort = (request.args.get("sort") or "newest").lower()
    if status not in STATUS_FILTERS:
        status = "all"
    if sort not in SORT_OPTIONS:
        sort = "newest"

    page = request.args.get("page", 1, type=int) or 1
    page = max(page, 1)
    pagination = ApplicationRepository.paginate_for_user(
        current_user.id,
        query=query,
        status=status,
        sort=sort,
        page=page,
        per_page=current_app.config["APPLICATIONS_PER_PAGE"],
    )
    stats = ApplicationRepository.stats_for_user(current_user.id)
    return render_template(
        "history.html",
        pagination=pagination,
        stats=stats,
        query=query,
        status=status,
        sort=sort,
    )


@bp.get("/history/<int:application_id>")
@login_required
def detail(application_id: int):
    application, is_owner, is_admin = _get_visible_application(application_id)
    return render_template(
        "application_detail.html",
        application=application,
        is_new=False,
        admin_view=is_admin and not is_owner,
        back_url=url_for("applications.history") if not (is_admin and not is_owner) else url_for("admin.applications"),
    )
