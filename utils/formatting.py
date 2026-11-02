"""Jinja-friendly display formatting helpers."""
from __future__ import annotations

from datetime import datetime
from typing import Any


def format_percent(value: Any, digits: int = 1) -> str:
    if value is None:
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    return f"{number * 100:.{digits}f}%"


def format_number(value: Any, digits: int = 0) -> str:
    if value is None:
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    return f"{number:,.{digits}f}"


def _indian_group(integer: int) -> str:
    text = str(abs(integer))
    if len(text) <= 3:
        return text
    last_three = text[-3:]
    remaining = text[:-3]
    groups = []
    while len(remaining) > 2:
        groups.insert(0, remaining[-2:])
        remaining = remaining[:-2]
    if remaining:
        groups.insert(0, remaining)
    return ",".join(groups) + "," + last_three


def format_inr(value: Any) -> str:
    """Format a rupee amount using Indian digit grouping."""
    if value is None:
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    rounded = int(round(number))
    sign = "-" if rounded < 0 else ""
    return f"{sign}₹{_indian_group(rounded)}"


def format_inr_thousands(value: Any) -> str:
    """The public dataset stores LoanAmount in thousands of rupees."""
    if value is None:
        return "—"
    try:
        return format_inr(float(value) * 1000)
    except (TypeError, ValueError):
        return "—"


def format_datetime(value: datetime | None, fmt: str = "%d %b %Y, %I:%M %p") -> str:
    if value is None:
        return "—"
    try:
        return f"{value.strftime(fmt)} UTC"
    except (AttributeError, ValueError):
        return "—"


def format_date(value: datetime | None, fmt: str = "%d %b %Y") -> str:
    if value is None:
        return "—"
    try:
        return value.strftime(fmt)
    except (AttributeError, ValueError):
        return "—"


def format_loan_term(months: Any) -> str:
    if months is None:
        return "—"
    try:
        total = int(months)
    except (TypeError, ValueError):
        return "—"
    if total % 12 == 0 and total >= 12:
        years = total // 12
        return f"{years} year{'s' if years != 1 else ''} ({total} months)"
    return f"{total} months"


def initials(name: str | None) -> str:
    if not name:
        return "U"
    parts = [part for part in name.strip().split() if part]
    if not parts:
        return "U"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def title_case(value: str | None) -> str:
    return value.title() if value else "—"
