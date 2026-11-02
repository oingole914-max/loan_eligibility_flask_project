"""Route access-control decorators."""
from __future__ import annotations

from functools import wraps
from typing import Any, Callable, TypeVar, cast

from flask import abort
from flask_login import current_user, login_required

F = TypeVar("F", bound=Callable[..., Any])


def admin_required(view: F) -> F:
    """Require an authenticated user whose role is exactly ``admin``."""

    @wraps(view)
    @login_required
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if not getattr(current_user, "is_admin", False):
            abort(403)
        return view(*args, **kwargs)

    return cast(F, wrapped)
