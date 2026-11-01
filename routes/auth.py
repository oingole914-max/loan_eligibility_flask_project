"""Registration, customer login and administrator login."""
from __future__ import annotations

from datetime import datetime, timezone

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_user, logout_user
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from extensions import db
from models import User
from repositories import UserRepository
from utils.security import is_safe_redirect_url
from utils.validators import (
    normalize_email,
    validate_password,
    validate_registration,
)

bp = Blueprint("auth", __name__)


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _post_login_destination(user: User, next_url: str | None) -> str:
    if is_safe_redirect_url(next_url, request.host_url):
        return next_url  # type: ignore[return-value]
    if user.is_admin:
        return url_for("admin.dashboard")
    return url_for("applications.history")


def _login_error(message: str = "Email or password is incorrect.") -> str:
    return message


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    next_url = request.args.get("next") or request.form.get("next") or ""
    values = {
        "full_name": "",
        "email": request.args.get("email", ""),
    }
    errors: dict[str, str] = {}

    if request.method == "POST":
        values["full_name"] = request.form.get("full_name", "")
        values["email"] = request.form.get("email", "")
        cleaned, errors = validate_registration(request.form)

        if not errors:
            if UserRepository.get_by_email(cleaned["email"]):
                errors["email"] = "An account with this email already exists."
            else:
                try:
                    UserRepository.create(
                        full_name=cleaned["full_name"],
                        email=cleaned["email"],
                        password=request.form.get("password", ""),
                        role="user",
                    )
                except IntegrityError:
                    db.session.rollback()
                    errors["email"] = "An account with this email already exists."
                except SQLAlchemyError:
                    db.session.rollback()
                    current_app.logger.exception("Registration database error")
                    errors["form"] = "We could not create your account. Please try again."
                else:
                    flash("Your account was created. Please sign in to continue.", "success")
                    return redirect(
                        url_for("auth.login", email=cleaned["email"], next=next_url or None)
                    )

    return render_template(
        "auth/register.html",
        values=values,
        errors=errors,
        next_url=next_url,
    )


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("applications.history"))

    next_url = request.args.get("next") or request.form.get("next") or ""
    email_value = request.args.get("email") or request.form.get("email", "")
    errors: dict[str, str] = {}

    if request.method == "POST":
        email = normalize_email(request.form.get("email"))
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        if not email:
            errors["email"] = "Email address is required."
        if not password:
            errors["password"] = "Password is required."
        if len(password) > 128:
            errors["password"] = "Email or password is incorrect."

        if not errors:
            user = UserRepository.get_by_email(email)
            if user is None or not user.check_password(password):
                errors["form"] = _login_error()
            else:
                try:
                    user.last_login_at = _utcnow()
                    db.session.commit()
                except SQLAlchemyError:
                    db.session.rollback()
                    current_app.logger.warning("Could not update last_login_at", exc_info=True)

                session.clear()
                login_user(user, remember=remember)
                session.permanent = True
                flash(f"Welcome back, {user.full_name.split()[0]}.", "success")
                return redirect(_post_login_destination(user, next_url))

    return render_template(
        "auth/login.html",
        email_value=email_value,
        errors=errors,
        next_url=next_url,
    )


@bp.post("/logout")
def logout():
    if current_user.is_authenticated:
        logout_user()
        session.clear()
        flash("You have been signed out.", "info")
    return redirect(url_for("main.home"))


@bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if current_user.is_authenticated and getattr(current_user, "is_admin", False):
        return redirect(url_for("admin.dashboard"))

    errors: dict[str, str] = {}
    email_value = request.form.get("email", "")

    if request.method == "POST":
        email = normalize_email(request.form.get("email"))
        password = request.form.get("password", "")
        if not email:
            errors["email"] = "Email address is required."
        if not password:
            errors["password"] = "Password is required."

        if not errors:
            user = UserRepository.get_by_email(email)
            if user is None or not user.check_password(password):
                errors["form"] = "Administrator email or password is incorrect."
            elif not user.is_admin:
                errors["form"] = "This account does not have administrator access."
            else:
                try:
                    user.last_login_at = _utcnow()
                    db.session.commit()
                except SQLAlchemyError:
                    db.session.rollback()
                    current_app.logger.warning(
                        "Could not update administrator last_login_at", exc_info=True
                    )

                if current_user.is_authenticated:
                    logout_user()
                session.clear()
                login_user(user, remember=False)
                session.permanent = True
                flash("Administrator session started.", "success")
                return redirect(url_for("admin.dashboard"))

    return render_template(
        "auth/admin_login.html",
        email_value=email_value,
        errors=errors,
    )
