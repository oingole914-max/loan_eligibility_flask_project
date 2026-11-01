"""Load the saved model once and run validated inference.

The persisted object is a complete scikit-learn Pipeline (imputation +
one-hot encoding + classifier). Flask must never pre-process inputs again.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
import sklearn

from .schema import MODEL_DEPENDENTS_MAP, MODEL_FEATURES

logger = logging.getLogger(__name__)

EXPECTED_SKLEARN_VERSION = "1.7.2"


class ModelLoadError(RuntimeError):
    """Raised when the saved model cannot be loaded or validated."""


class PredictionError(RuntimeError):
    """Raised when inference fails for a validated input."""


@dataclass(frozen=True)
class PredictionResult:
    predicted_class: int
    label: str
    eligibility_probability: float
    confidence: float
    model_name: str

    @property
    def model_probability(self) -> float:
        """Probability assigned to the predicted class (backwards compatible)."""
        return self.confidence

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["model_probability"] = self.model_probability
        return data


class LoanPredictor:
    """Thread-safe wrapper around the persisted preprocessing + model pipeline."""

    def __init__(self, model_path: str | Path) -> None:
        self.model_path = Path(model_path)
        self._lock = threading.Lock()
        self._bundle: dict[str, Any] | None = None
        self.pipeline: Any = None
        self.feature_columns: tuple[str, ...] = MODEL_FEATURES
        self.model_name: str = "Unknown model"
        self.classes: list[int] = []
        self.expected_sklearn_version = EXPECTED_SKLEARN_VERSION
        self.runtime_sklearn_version = sklearn.__version__
        self._load()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    def _load(self) -> None:
        if not self.model_path.exists():
            raise ModelLoadError(
                f"Model file was not found at {self.model_path}. "
                "Keep loan_model.pkl in the project root or set MODEL_PATH."
            )

        if self.runtime_sklearn_version != self.expected_sklearn_version:
            logger.warning(
                "loan_model.pkl was created with scikit-learn %s but the runtime "
                "is %s. Install requirements.txt to avoid compatibility problems.",
                self.expected_sklearn_version,
                self.runtime_sklearn_version,
            )

        try:
            loaded = joblib.load(self.model_path)
        except Exception as exc:  # noqa: BLE001 - surface a clear setup error
            raise ModelLoadError(
                "The saved model could not be loaded. Confirm that the pinned "
                "scikit-learn version is installed (see requirements.txt)."
            ) from exc

        if isinstance(loaded, dict):
            pipeline = loaded.get("pipeline")
            stored_features = loaded.get("feature_columns")
            model_name = loaded.get("model_name", "RandomForest")
            classes = loaded.get("classes")
            bundle = loaded
        else:
            # Support a bare fitted pipeline as a fallback, but still enforce
            # the known feature contract.
            pipeline = loaded
            stored_features = None
            model_name = type(loaded).__name__
            classes = None
            bundle = {"pipeline": pipeline, "model_name": model_name}

        if pipeline is None or not hasattr(pipeline, "predict"):
            raise ModelLoadError("loan_model.pkl does not contain a usable model pipeline.")
        if not hasattr(pipeline, "predict_proba"):
            raise ModelLoadError("The saved model does not support probability estimates.")

        if stored_features is not None:
            feature_list = [str(item) for item in stored_features]
            if tuple(feature_list) != MODEL_FEATURES:
                raise ModelLoadError(
                    "The model's stored feature columns do not match the application "
                    f"contract. Expected {list(MODEL_FEATURES)}, got {feature_list}."
                )

        pipeline_features = getattr(pipeline, "feature_names_in_", None)
        if pipeline_features is not None:
            pipeline_feature_list = [str(item) for item in pipeline_features]
            if tuple(pipeline_feature_list) != MODEL_FEATURES:
                raise ModelLoadError(
                    "The fitted pipeline expects different feature columns: "
                    f"{pipeline_feature_list}."
                )

        try:
            fitted_classes = [int(item) for item in pipeline.classes_]
        except Exception as exc:  # noqa: BLE001
            raise ModelLoadError("The model does not expose fitted classes.") from exc

        if sorted(fitted_classes) != [0, 1]:
            raise ModelLoadError(
                f"Expected binary classes [0, 1], found {fitted_classes}."
            )

        if classes is not None and [str(item) for item in classes] != [
            "Not Eligible",
            "Eligible",
        ]:
            raise ModelLoadError(
                "The model label mapping is not in the expected order: "
                f"{classes}."
            )

        self.pipeline = pipeline
        self._bundle = bundle
        self.model_name = str(model_name)
        self.classes = fitted_classes
        logger.info(
            "Loaded %s model from %s (scikit-learn %s).",
            self.model_name,
            self.model_path,
            self.runtime_sklearn_version,
        )

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------
    def predict(self, features: dict[str, Any]) -> PredictionResult:
        """Run one prediction. ``features`` must already be validated."""
        missing = [name for name in MODEL_FEATURES if name not in features]
        if missing:
            raise PredictionError(f"Missing model features: {', '.join(missing)}")

        row = {name: features[name] for name in MODEL_FEATURES}
        row["Dependents"] = MODEL_DEPENDENTS_MAP.get(
            str(row["Dependents"]).strip(), str(row["Dependents"]).strip()
        )

        frame = pd.DataFrame([row], columns=list(MODEL_FEATURES))

        try:
            with self._lock:
                predicted = int(self.pipeline.predict(frame)[0])
                probabilities = self.pipeline.predict_proba(frame)[0]
        except Exception as exc:  # noqa: BLE001 - never leak internals to users
            logger.exception("Model inference failed")
            raise PredictionError(
                "The prediction engine could not process this application."
            ) from exc

        try:
            class_probabilities = {
                int(label): float(probability)
                for label, probability in zip(self.pipeline.classes_, probabilities)
            }
        except Exception as exc:  # noqa: BLE001
            raise PredictionError("The model returned an unexpected probability format.") from exc

        if predicted not in (0, 1) or 1 not in class_probabilities:
            raise PredictionError("The model returned an unexpected class value.")

        eligibility_probability = class_probabilities[1]
        confidence = class_probabilities[predicted]

        return PredictionResult(
            predicted_class=predicted,
            label="Eligible" if predicted == 1 else "Not Eligible",
            eligibility_probability=eligibility_probability,
            confidence=confidence,
            model_name=self.model_name,
        )

    def self_check(self) -> None:
        """Fail fast at start-up if the pickled pipeline cannot actually predict."""
        sample = {
            "Gender": "Male",
            "Married": "Yes",
            "Dependents": "0",
            "Education": "Graduate",
            "Self_Employed": "No",
            "ApplicantIncome": 5849,
            "CoapplicantIncome": 0,
            "LoanAmount": 128,
            "Loan_Amount_Term": 360,
            "Credit_History": 1,
            "Property_Area": "Urban",
        }
        result = self.predict(sample)
        if result.predicted_class not in (0, 1) or not 0 <= result.eligibility_probability <= 1:
            raise ModelLoadError("The model start-up self-check returned invalid output.")
        logger.info("Model self-check passed (class=%s).", result.predicted_class)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------
    def info(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "model_path": str(self.model_path),
            "feature_count": len(MODEL_FEATURES),
            "features": list(MODEL_FEATURES),
            "classes": list(self.classes),
            "sklearn_version": self.runtime_sklearn_version,
            "expected_sklearn_version": self.expected_sklearn_version,
            "ready": True,
        }


@lru_cache(maxsize=4)
def _load_predictor(model_path: str) -> LoanPredictor:
    return LoanPredictor(model_path)


def get_predictor(model_path: str | Path | None = None) -> LoanPredictor:
    """Return the process-wide predictor, loading it only on first use."""
    if model_path is None:
        from flask import current_app

        model_path = current_app.config["MODEL_PATH"]
    return _load_predictor(str(Path(model_path).resolve()))


def get_model_info(model_path: str | Path | None = None) -> dict[str, Any]:
    return get_predictor(model_path).info()
