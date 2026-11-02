"""Server-side validation for authentication and model inputs.

The browser's HTML validation is a convenience only; every value is validated
again here before it reaches the database or the model.
"""
from __future__ import annotations

import math
import re
from typing import Any, Mapping

from ml.schema import (
    FIELD_LABELS,
    FIELD_OPTIONS,
    INTEGER_FEATURES,
    MODEL_FEATURES,
    NUMERIC_BOUNDS,
)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")


def clean_name(raw: Any) -> str:
    return re.sub(r"\s+", " ", str(raw or "").strip())


def validate_applicant_name(raw: Any) -> tuple[str, str | None]:
    name = clean_name(raw)
    if not name:
        return name, "Applicant name is required."
    if len(name) < 2:
        return name, "Applicant name must be at least 2 characters."
    if len(name) > 120:
        return name, "Applicant name must be 120 characters or fewer."
    if CONTROL_CHAR_RE.search(name):
        return name, "Applicant name contains invalid characters."
    return name, None


def normalize_email(raw: Any) -> str:
    return str(raw or "").strip().lower()


def validate_email(raw: Any) -> tuple[str, str | None]:
    email = normalize_email(raw)
    if not email:
        return email, "Email address is required."
    if len(email) > 190:
        return email, "Email address is too long."
    if not EMAIL_RE.match(email):
        return email, "Enter a valid email address."
    return email, None


def validate_password(password: str, *, label: str = "Password") -> str | None:
    if not password:
        return f"{label} is required."
    if len(password) < 8:
        return f"{label} must be at least 8 characters."
    if len(password) > 128:
        return f"{label} must be 128 characters or fewer."
    if not re.search(r"[A-Za-z]", password):
        return f"{label} must contain at least one letter."
    if not re.search(r"\d", password):
        return f"{label} must contain at least one number."
    return None


def validate_registration(form: Mapping[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    cleaned: dict[str, str] = {}
    errors: dict[str, str] = {}

    name, error = validate_applicant_name(form.get("full_name"))
    cleaned["full_name"] = name
    if error:
        errors["full_name"] = error

    email, error = validate_email(form.get("email"))
    cleaned["email"] = email
    if error:
        errors["email"] = error

    password = str(form.get("password") or "")
    password_error = validate_password(password)
    if password_error:
        errors["password"] = password_error

    confirm = str(form.get("confirm_password") or "")
    if not confirm:
        errors["confirm_password"] = "Please confirm your password."
    elif password != confirm:
        errors["confirm_password"] = "Passwords do not match."

    return cleaned, errors


def _parse_number(
    field: str,
    raw: Any,
) -> tuple[float | int | None, str | None]:
    label = FIELD_LABELS[field]
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None, f"{label} is required."
    if isinstance(raw, bool):
        return None, f"{label} must be a number."

    if isinstance(raw, str):
        text = raw.strip().replace(",", "")
    else:
        text = str(raw)

    try:
        value = float(text)
    except (TypeError, ValueError):
        return None, f"{label} must be a valid number."
    if not math.isfinite(value):
        return None, f"{label} must be a finite number."

    minimum, maximum = NUMERIC_BOUNDS[field]
    if value < minimum or value > maximum:
        return None, f"{label} must be between {minimum:g} and {maximum:g}."

    if field in INTEGER_FEATURES:
        if not value.is_integer():
            return None, f"{label} must be a whole number."
        return int(value), None
    return value, None


def _parse_category(field: str, raw: Any) -> tuple[str | None, str | None]:
    label = FIELD_LABELS[field]
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None, f"{label} is required."
    value = str(raw).strip()
    allowed = FIELD_OPTIONS[field]
    lookup = {option.lower(): option for option in allowed}
    canonical = lookup.get(value.lower())
    if canonical is None:
        return None, f"Choose a valid {label.lower()} option."
    return canonical, None


def validate_model_input(payload: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    """Validate and normalise the 11 model fields.

    Returns ``(cleaned_features, errors)``. Unknown extra keys are ignored and
    never forwarded to the model.
    """
    cleaned: dict[str, Any] = {}
    errors: dict[str, str] = {}

    for field in MODEL_FEATURES:
        if field in NUMERIC_BOUNDS:
            value, error = _parse_number(field, payload.get(field))
        else:
            value, error = _parse_category(field, payload.get(field))

        if error:
            errors[field] = error
        else:
            cleaned[field] = value

    # Credit history is a binary flag even though it is numeric in the CSV.
    if "Credit_History" in cleaned and cleaned["Credit_History"] not in (0, 1):
        errors["Credit_History"] = "Credit history must be 0 or 1."
        cleaned.pop("Credit_History", None)

    return cleaned, errors


def validate_application_form(
    form: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, str]]:
    cleaned: dict[str, Any] = {}
    errors: dict[str, str] = {}

    name, error = validate_applicant_name(form.get("applicant_name"))
    cleaned["applicant_name"] = name
    if error:
        errors["applicant_name"] = error

    model_data, model_errors = validate_model_input(form)
    cleaned.update(model_data)
    errors.update(model_errors)
    return cleaned, errors


def validation_message(errors: Mapping[str, str]) -> str:
    if not errors:
        return ""
    if len(errors) == 1:
        return next(iter(errors.values()))
    return f"Please correct the {len(errors)} highlighted fields and try again."
