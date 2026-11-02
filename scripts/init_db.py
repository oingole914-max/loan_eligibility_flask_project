r"""Initialise the configured database and optionally seed an administrator.

Usage (Windows PowerShell, from the project root):
    .\.venv\Scripts\Activate.ps1
    python scripts\init_db.py
    python scripts\init_db.py --with-admin
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from sqlalchemy.exc import SQLAlchemyError  # noqa: E402

from app import create_app  # noqa: E402
from extensions import db  # noqa: E402
from models import User  # noqa: E402
from repositories import UserRepository  # noqa: E402
from utils.validators import validate_applicant_name, validate_email, validate_password  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--with-admin",
        action="store_true",
        help="Also create the administrator configured by ADMIN_* in .env.",
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        try:
            db.create_all()
        except SQLAlchemyError:
            db.session.rollback()
            print("ERROR: Could not create database tables. Check DATABASE_URL.", file=sys.stderr)
            return 1
        print("Database tables are ready.")
        print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI'].split('@')[-1]}")

        if not args.with_admin:
            return 0

        name, name_error = validate_applicant_name(app.config.get("ADMIN_NAME"))
        email, email_error = validate_email(app.config.get("ADMIN_EMAIL"))
        password = app.config.get("ADMIN_PASSWORD") or ""
        password_error = validate_password(password)

        if name_error or email_error or password_error:
            print(
                "ERROR: Set valid ADMIN_NAME, ADMIN_EMAIL and ADMIN_PASSWORD in .env.",
                file=sys.stderr,
            )
            return 1

        existing = UserRepository.get_by_email(email)
        if existing:
            existing.full_name = name
            existing.role = "admin"
            existing.set_password(password)
            db.session.commit()
            print(f"Administrator updated: {email}")
        else:
            user = User(full_name=name, email=email, role="admin")
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            print(f"Administrator created: {email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
