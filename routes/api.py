"""JSON prediction endpoint retained for programmatic testing."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from extensions import csrf
from ml.predictor import PredictionError, get_predictor
from ml.schema import MODEL_FEATURES
from utils.validators import validate_model_input, validation_message

bp = Blueprint("api", __name__)

DISCLAIMER = (
    "Preliminary educational estimate only. This is not a loan approval, "
    "credit decision, or financial advice."
)


@bp.post("/predict")
@csrf.exempt
def predict():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return (
            jsonify(
                {
                    "error": "Send applicant details as a JSON object.",
                    "required_features": list(MODEL_FEATURES),
                }
            ),
            400,
        )

    cleaned, errors = validate_model_input(payload)
    if errors:
        return (
            jsonify(
                {
                    "error": "Validation failed.",
                    "message": validation_message(errors),
                    "errors": errors,
                    "fields": list(errors.keys()),
                    "required_features": list(MODEL_FEATURES),
                }
            ),
            400,
        )

    try:
        result = get_predictor().predict(cleaned)
    except PredictionError:
        current_app.logger.exception("Prediction API failed")
        return (
            jsonify(
                {
                    "error": "The prediction service is temporarily unavailable.",
                }
            ),
            503,
        )

    return jsonify(
        {
            "prediction": result.label,
            "predicted_class": result.predicted_class,
            "model_probability": round(result.confidence, 4),
            "prediction_confidence": round(result.confidence, 4),
            "eligibility_probability": round(result.eligibility_probability, 4),
            "model": result.model_name,
            "disclaimer": DISCLAIMER,
        }
    )
