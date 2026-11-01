"""Single source of truth for the model's input contract.

These names and allowed values must match the trained dataset. The predictor
also checks the feature list stored inside ``loan_model.pkl`` at start-up.
"""
from __future__ import annotations

MODEL_FEATURES: tuple[str, ...] = (
    "Gender",
    "Married",
    "Dependents",
    "Education",
    "Self_Employed",
    "ApplicantIncome",
    "CoapplicantIncome",
    "LoanAmount",
    "Loan_Amount_Term",
    "Credit_History",
    "Property_Area",
)

NUMERIC_FEATURES: tuple[str, ...] = (
    "ApplicantIncome",
    "CoapplicantIncome",
    "LoanAmount",
    "Loan_Amount_Term",
    "Credit_History",
)

CATEGORICAL_FEATURES: tuple[str, ...] = tuple(
    field for field in MODEL_FEATURES if field not in NUMERIC_FEATURES
)

FIELD_LABELS: dict[str, str] = {
    "Gender": "Gender",
    "Married": "Marital status",
    "Dependents": "Dependents",
    "Education": "Education",
    "Self_Employed": "Self-employment",
    "ApplicantIncome": "Applicant income",
    "CoapplicantIncome": "Co-applicant income",
    "LoanAmount": "Loan amount",
    "Loan_Amount_Term": "Loan term",
    "Credit_History": "Credit history",
    "Property_Area": "Property area",
}

FIELD_OPTIONS: dict[str, tuple[str, ...]] = {
    "Gender": ("Male", "Female"),
    "Married": ("Yes", "No"),
    "Dependents": ("0", "1", "2", "3+"),
    "Education": ("Graduate", "Not Graduate"),
    "Self_Employed": ("Yes", "No"),
    "Property_Area": ("Urban", "Semiurban", "Rural"),
}

# (minimum, maximum) validation bounds. These are deliberately wider than
# the training data so ordinary applications are not blocked, while still
# rejecting impossible or abusive values.
NUMERIC_BOUNDS: dict[str, tuple[float, float]] = {
    "ApplicantIncome": (1, 10_000_000),
    "CoapplicantIncome": (0, 10_000_000),
    "LoanAmount": (1, 10_000),
    "Loan_Amount_Term": (12, 480),
    "Credit_History": (0, 1),
}

INTEGER_FEATURES = frozenset({"Loan_Amount_Term", "Credit_History"})

# The training script converted "3+" to "3" before fitting the encoder.
MODEL_DEPENDENTS_MAP = {"3+": "3"}
