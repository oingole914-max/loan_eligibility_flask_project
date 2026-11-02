from __future__ import annotations

import json
from pathlib import Path

import pytest

from ml.metrics import get_performance_summary
from ml.predictor import get_predictor, MODEL_FEATURES, PredictionResult, get_model_info
from ml.schema import FIELD_OPTIONS, MODEL_DEPENDENTS_MAP


@pytest.fixture(autouse=True)
def _application_context(app):
    with app.app_context():
        yield


def test_saved_model_loads_and_respects_feature_contract():
    predictor = get_predictor()
    info = get_model_info()
    assert info["ready"] is True
    assert info["model_name"] == "RandomForest"
    assert info["sklearn_version"] == "1.7.2"
    assert tuple(info["features"]) == MODEL_FEATURES
    assert info["feature_count"] == 11
    predictor.self_check()


def test_model_produces_real_probability_for_both_classes():
    predictor = get_predictor()
    eligible = predictor.predict(
        {
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
    )
    not_eligible = predictor.predict(
        {
            "Gender": "Female",
            "Married": "No",
            "Dependents": "2",
            "Education": "Not Graduate",
            "Self_Employed": "Yes",
            "ApplicantIncome": 2000,
            "CoapplicantIncome": 0,
            "LoanAmount": 200,
            "Loan_Amount_Term": 360,
            "Credit_History": 0,
            "Property_Area": "Rural",
        }
    )

    assert isinstance(eligible, PredictionResult)
    assert eligible.predicted_class == 1
    assert eligible.label == "Eligible"
    assert eligible.eligibility_probability > 0.5
    assert eligible.confidence == pytest.approx(eligible.eligibility_probability)
    assert 0 <= eligible.eligibility_probability <= 1

    assert not_eligible.predicted_class == 0
    assert not_eligible.label == "Not Eligible"
    assert not_eligible.eligibility_probability < 0.5
    assert not_eligible.confidence == pytest.approx(1 - not_eligible.eligibility_probability)


def test_dependents_three_plus_is_normalised_for_the_pipeline():
    predictor = get_predictor()
    base = {
        "Gender": "Male",
        "Married": "Yes",
        "Education": "Graduate",
        "Self_Employed": "No",
        "ApplicantIncome": 5849,
        "CoapplicantIncome": 0,
        "LoanAmount": 128,
        "Loan_Amount_Term": 360,
        "Credit_History": 1,
        "Property_Area": "Urban",
    }
    assert MODEL_DEPENDENTS_MAP["3+"] == "3"
    result = predictor.predict({**base, "Dependents": "3+"})
    assert result.predicted_class in (0, 1)


def test_all_categorical_values_are_valid_model_domains():
    assert FIELD_OPTIONS["Gender"] == ("Male", "Female")
    assert set(FIELD_OPTIONS["Dependents"]) == {"0", "1", "2", "3+"}
    assert set(FIELD_OPTIONS["Property_Area"]) == {"Urban", "Semiurban", "Rural"}


def test_metrics_summary_uses_actual_json_values():
    path = Path(__file__).resolve().parents[1] / "model_metrics.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    selected = raw["selected_model"]
    selected_values = raw["models"][selected]
    summary = get_performance_summary(path)

    assert summary["available"] is True
    assert summary["selected_model"] == selected
    assert summary["accuracy"] == selected_values["test_accuracy"]
    assert summary["precision"] == selected_values["test_precision"]
    assert summary["recall"] == selected_values["test_recall"]
    assert summary["f1"] == selected_values["test_f1"]
    assert summary["roc_auc"] == selected_values["test_roc_auc"]
    assert summary["confusion_matrix"] == selected_values["confusion_matrix"]
    assert len(summary["comparison"]) == len(raw["models"])


def test_missing_model_file_raises_clear_error(tmp_path):
    from ml.predictor import LoanPredictor, ModelLoadError

    with pytest.raises(ModelLoadError, match="not found"):
        LoanPredictor(tmp_path / "missing.pkl")
