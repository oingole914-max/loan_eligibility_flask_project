"""Database query helpers, kept separate from route and template logic."""
from __future__ import annotations

from typing import Any

from sqlalchemy import String, case, cast, func, or_, select, true

from extensions import db
from models import Application, User


def _escaped_like(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


class UserRepository:
    @staticmethod
    def get_by_email(email: str) -> User | None:
        statement = select(User).where(func.lower(User.email) == email.strip().lower())
        return db.session.execute(statement).scalar_one_or_none()

    @staticmethod
    def get_by_id(user_id: int) -> User | None:
        return db.session.get(User, user_id)

    @staticmethod
    def create(full_name: str, email: str, password: str, *, role: str = "user") -> User:
        user = User(full_name=full_name, email=email.lower(), role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user


class ApplicationRepository:
    @staticmethod
    def create(user: User, data: dict[str, Any], prediction: Any) -> Application:
        application = Application(
            user_id=user.id,
            applicant_name=data["applicant_name"],
            Gender=data["Gender"],
            Married=data["Married"],
            Dependents=data["Dependents"],
            Education=data["Education"],
            Self_Employed=data["Self_Employed"],
            ApplicantIncome=data["ApplicantIncome"],
            CoapplicantIncome=data["CoapplicantIncome"],
            LoanAmount=data["LoanAmount"],
            Loan_Amount_Term=data["Loan_Amount_Term"],
            Credit_History=data["Credit_History"],
            Property_Area=data["Property_Area"],
            prediction=prediction.predicted_class,
            eligibility_probability=prediction.eligibility_probability,
            prediction_confidence=prediction.confidence,
            model_name=prediction.model_name,
        )
        db.session.add(application)
        db.session.commit()
        return application

    @staticmethod
    def get(application_id: int) -> Application | None:
        return db.session.get(Application, application_id)

    @staticmethod
    def get_for_user(application_id: int, user_id: int) -> Application | None:
        statement = select(Application).where(
            Application.id == application_id,
            Application.user_id == user_id,
        )
        return db.session.execute(statement).scalar_one_or_none()

    # ------------------------------------------------------------------
    # Filtering and pagination
    # ------------------------------------------------------------------
    @staticmethod
    def _apply_filters(
        statement: Any,
        *,
        user_id: int | None = None,
        query: str = "",
        status: str = "all",
        admin_search: bool = False,
    ) -> Any:
        if user_id is not None:
            statement = statement.where(Application.user_id == user_id)

        status = (status or "all").lower()
        if status == "eligible":
            statement = statement.where(Application.prediction == 1)
        elif status in {"not_eligible", "ineligible"}:
            statement = statement.where(Application.prediction == 0)

        query = (query or "").strip()
        if query:
            pattern = f"%{_escaped_like(query)}%"
            conditions = [
                Application.applicant_name.ilike(pattern, escape="\\"),
                cast(Application.id, String).ilike(pattern, escape="\\"),
            ]
            if admin_search:
                conditions.append(User.email.ilike(pattern, escape="\\"))
                conditions.append(User.full_name.ilike(pattern, escape="\\"))
                statement = statement.join(User, Application.user_id == User.id)
            statement = statement.where(or_(*conditions))

        return statement

    @staticmethod
    def paginate_for_user(
        user_id: int,
        *,
        query: str = "",
        status: str = "all",
        sort: str = "newest",
        page: int = 1,
        per_page: int = 8,
    ) -> Any:
        statement = select(Application).where(Application.user_id == user_id)
        statement = ApplicationRepository._apply_filters(
            statement, user_id=user_id, query=query, status=status
        )
        if sort == "oldest":
            statement = statement.order_by(Application.created_at.asc(), Application.id.asc())
        else:
            statement = statement.order_by(Application.created_at.desc(), Application.id.desc())
        return db.paginate(statement, page=page, per_page=per_page, error_out=False)

    @staticmethod
    def paginate_all(
        *,
        query: str = "",
        status: str = "all",
        page: int = 1,
        per_page: int = 12,
    ) -> Any:
        statement = select(Application)
        statement = ApplicationRepository._apply_filters(
            statement, query=query, status=status, admin_search=True
        )
        statement = statement.order_by(Application.created_at.desc(), Application.id.desc())
        return db.paginate(statement, page=page, per_page=per_page, error_out=False)

    @staticmethod
    def all_filtered(*, query: str = "", status: str = "all") -> list[Application]:
        statement = select(Application)
        statement = ApplicationRepository._apply_filters(
            statement, query=query, status=status, admin_search=True
        )
        statement = statement.order_by(Application.created_at.desc(), Application.id.desc())
        return list(db.session.execute(statement).scalars().all())

    # ------------------------------------------------------------------
    # Aggregates
    # ------------------------------------------------------------------
    @staticmethod
    def _stats(statement: Any) -> dict[str, Any]:
        row = db.session.execute(
            select(
                func.count(Application.id),
                func.coalesce(
                    func.sum(case((Application.prediction == 1, 1), else_=0)), 0
                ),
                func.coalesce(
                    func.sum(case((Application.prediction == 0, 1), else_=0)), 0
                ),
                func.avg(Application.eligibility_probability),
            ).select_from(Application).where(statement)
        ).one()
        total, eligible, ineligible, average = row
        return {
            "total": int(total or 0),
            "eligible": int(eligible or 0),
            "ineligible": int(ineligible or 0),
            "average_probability": float(average) if average is not None else None,
            "eligible_rate": (float(eligible) / float(total)) if total else None,
        }

    @staticmethod
    def stats_for_user(user_id: int) -> dict[str, Any]:
        return ApplicationRepository._stats(Application.user_id == user_id)

    @staticmethod
    def dashboard_stats() -> dict[str, Any]:
        return ApplicationRepository._stats(true())

    @staticmethod
    def recent(limit: int = 8) -> list[Application]:
        statement = (
            select(Application)
            .order_by(Application.created_at.desc(), Application.id.desc())
            .limit(limit)
        )
        return list(db.session.execute(statement).scalars().all())

    @staticmethod
    def count() -> int:
        return int(db.session.scalar(select(func.count(Application.id))) or 0)
