"""Read the real evaluation output produced by ``train_model.py``.

No metric is calculated or invented here. If the file is missing or malformed
the dashboard explicitly reports that performance data is unavailable.
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PERFORMANCE_KEYS = (
    "test_accuracy",
    "test_precision",
    "test_recall",
    "test_f1",
    "test_roc_auc",
)


@lru_cache(maxsize=4)
def load_metrics(metrics_path: str | Path) -> dict[str, Any] | None:
    path = Path(metrics_path)
    if not path.exists():
        logger.warning("Metrics file not found at %s", path)
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read model metrics: %s", exc)
        return None
    if not isinstance(data, dict):
        logger.warning("Metrics file does not contain a JSON object.")
        return None
    return data


def get_performance_summary(metrics_path: str | Path) -> dict[str, Any]:
    """Return a validated, template-friendly summary of actual metrics."""
    data = load_metrics(str(Path(metrics_path).resolve()))
    if not data:
        return {
            "available": False,
            "reason": "model_metrics.json could not be loaded.",
        }

    selected_model = data.get("selected_model")
    models = data.get("models")
    if not selected_model or not isinstance(models, dict) or selected_model not in models:
        return {
            "available": False,
            "reason": "model_metrics.json does not contain a selected model.",
        }

    selected = models[selected_model]
    if not isinstance(selected, dict) or any(key not in selected for key in PERFORMANCE_KEYS):
        return {
            "available": False,
            "reason": "The selected model's evaluation values are incomplete.",
        }

    confusion = selected.get("confusion_matrix")
    if (
        not isinstance(confusion, list)
        or len(confusion) != 2
        or any(not isinstance(row, list) or len(row) != 2 for row in confusion)
    ):
        return {
            "available": False,
            "reason": "The selected model's confusion matrix is missing or invalid.",
        }

    comparison = []
    for name, values in models.items():
        if not isinstance(values, dict):
            continue
        comparison.append(
            {
                "name": name,
                "selected": name == selected_model,
                "cv_f1_mean": values.get("cv_f1_mean"),
                "cv_roc_auc_mean": values.get("cv_roc_auc_mean"),
                "cv_accuracy_mean": values.get("cv_accuracy_mean"),
                "test_accuracy": values.get("test_accuracy"),
                "test_precision": values.get("test_precision"),
                "test_recall": values.get("test_recall"),
                "test_f1": values.get("test_f1"),
                "test_roc_auc": values.get("test_roc_auc"),
            }
        )
    comparison.sort(key=lambda item: item.get("cv_f1_mean") or 0, reverse=True)

    return {
        "available": True,
        "dataset": data.get("dataset"),
        "rows_used": data.get("rows_used"),
        "target_distribution": data.get("target_distribution", {}),
        "selected_model": selected_model,
        "selection_metric": data.get("selection_metric"),
        "note": data.get("note"),
        "accuracy": selected["test_accuracy"],
        "precision": selected["test_precision"],
        "recall": selected["test_recall"],
        "f1": selected["test_f1"],
        "roc_auc": selected["test_roc_auc"],
        "confusion_matrix": confusion,
        "comparison": comparison,
    }
