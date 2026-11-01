"""Administrator dashboard, application management and CSV export."""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from ml.metrics import get_performance_summary
from repositories import ApplicationRepository
from utils.decorators import admin_required
from utils.formatting import format_datetime, format_percent

bp = Blueprint("admin", __name__, url_prefix="/admin")

STATUS_FILTERS = {"all", "eligible", "not_eligible"}


def _filters() -> tuple[str, str]:
    query = (request.args.get("q") or "").strip()[:120]
    status = (request.args.get("status") or "all").lower()
    if status not in STATUS_FILTERS:
        status = "all"
    return query, status


@bp.get("/")
@admin_required
def dashboard():
    stats = ApplicationRepository.dashboard_stats()
    recent = ApplicationRepository.recent(limit=8)
    performance = get_performance_summary(current_app.config["METRICS_PATH"])
    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent=recent,
        performance=performance,
        now=datetime.now(timezone.utc),
    )


@bp.get("/applications")
@admin_required
def applications():
    query, status = _filters()
    page = request.args.get("page", 1, type=int) or 1
    page = max(page, 1)
    pagination = ApplicationRepository.paginate_all(
        query=query,
        status=status,
        page=page,
        per_page=current_app.config["ADMIN_APPLICATIONS_PER_PAGE"],
    )
    return render_template(
        "admin/applications.html",
        pagination=pagination,
        query=query,
        status=status,
    )


@bp.get("/applications/<int:application_id>")
@admin_required
def application_detail(application_id: int):
    application = ApplicationRepository.get(application_id)
    if application is None:
        abort(404)
    return render_template(
        "application_detail.html",
        application=application,
        is_new=False,
        admin_view=True,
        back_url=url_for("admin.applications"),
    )


@bp.post("/applications/<int:application_id>/delete")
@admin_required
def delete_application(application_id: int):
    application = ApplicationRepository.get(application_id)
    if application is None:
        abort(404)
    reference = application.reference
    try:
        db.session.delete(application)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Could not delete application %s", application_id)
        flash("The application could not be deleted. Please try again.", "danger")
        return redirect(url_for("admin.applications"))

    current_app.logger.info(
        "Administrator %s deleted application %s",
        current_user.email,
        reference,
    )
    flash(f"Application {reference} was deleted.", "success")
    return redirect(url_for("admin.applications"))


@bp.get("/applications/export")
@admin_required
def export_applications():
    query, status = _filters()
    records = ApplicationRepository.all_filtered(query=query, status=status)

    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        [
            "Reference",
            "Applicant name",
            "Account email",
            "Gender",
            "Marital status",
            "Dependents",
            "Education",
            "Self employed",
            "Applicant income",
            "Co-applicant income",
            "Loan amount (thousands)",
            "Loan term (months)",
            "Credit history",
            "Property area",
            "Prediction",
            "Eligibility probability",
            "Model confidence",
            "Model",
            "Predicted at (UTC)",
        ]
    )
    for record in records:
        writer.writerow(
            [
                record.reference,
                record.applicant_name,
                record.user.email if record.user else "",
                record.Gender,
                record.Married,
                record.Dependents,
                record.Education,
                record.Self_Employed,
                record.ApplicantIncome,
                record.CoapplicantIncome,
                record.LoanAmount,
                record.Loan_Amount_Term,
                record.Credit_History,
                record.Property_Area,
                record.eligibility_label,
                format_percent(record.eligibility_probability),
                format_percent(record.prediction_confidence),
                record.model_name,
                format_datetime(record.created_at),
            ]
        )

    payload = io.BytesIO(("\ufeff" + output.getvalue()).encode("utf-8"))
    filename = datetime.now(timezone.utc).strftime("loan_applications_%Y%m%d_%H%M.csv")
    return send_file(
        payload,
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename,
    )
