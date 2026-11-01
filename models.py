"""SQLAlchemy models for users and loan applications."""
from __future__ import annotations

from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db, login_manager


def utcnow() -> datetime:
    """Return a naive UTC timestamp (portable across SQLite and MySQL)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(190), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user", index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    last_login_at = db.Column(db.DateTime, nullable=True)

    applications = db.relationship(
        "Application",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<User {self.email}>"


class Application(db.Model):
    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    applicant_name = db.Column(db.String(120), nullable=False)

    # Model inputs -------------------------------------------------------
    Gender = db.Column(db.String(10), nullable=False)
    Married = db.Column(db.String(3), nullable=False)
    Dependents = db.Column(db.String(3), nullable=False)
    Education = db.Column(db.String(20), nullable=False)
    Self_Employed = db.Column(db.String(3), nullable=False)
    ApplicantIncome = db.Column(db.Float, nullable=False)
    CoapplicantIncome = db.Column(db.Float, nullable=False)
    LoanAmount = db.Column(db.Float, nullable=False)
    Loan_Amount_Term = db.Column(db.Integer, nullable=False)
    Credit_History = db.Column(db.SmallInteger, nullable=False)
    Property_Area = db.Column(db.String(12), nullable=False)

    # Prediction output --------------------------------------------------
    prediction = db.Column(db.SmallInteger, nullable=False, index=True)
    eligibility_probability = db.Column(db.Float, nullable=False)
    prediction_confidence = db.Column(db.Float, nullable=False)
    model_name = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)

    user = db.relationship("User", back_populates="applications")

    __table_args__ = (
        db.Index("ix_applications_user_created", "user_id", "created_at"),
        db.Index("ix_applications_prediction_created", "prediction", "created_at"),
    )

    @property
    def is_eligible(self) -> bool:
        return self.prediction == 1

    @property
    def eligibility_label(self) -> str:
        return "Eligible" if self.is_eligible else "Not Eligible"

    @property
    def reference(self) -> str:
        return f"APP-{self.id:05d}" if self.id else "APP-PENDING"

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Application {self.reference} {self.eligibility_label}>"


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None
