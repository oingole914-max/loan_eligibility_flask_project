"""Download the public 614-row Loan Prediction dataset, compare models, and save the best pipeline."""
from pathlib import Path
import json
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_validate
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, classification_report, confusion_matrix

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "loan_prediction_dataset.csv"
MODEL_PATH = ROOT / "loan_model.pkl"
METRICS_PATH = ROOT / "model_metrics.json"
DATA_URL = "https://huggingface.co/datasets/mariosyahirhalimm/loan_prediction_dataset/raw/main/loan_prediction_dataset.csv"

FEATURES = [
    "Gender", "Married", "Dependents", "Education", "Self_Employed",
    "ApplicantIncome", "CoapplicantIncome", "LoanAmount",
    "Loan_Amount_Term", "Credit_History", "Property_Area"
]
NUMERIC = ["ApplicantIncome", "CoapplicantIncome", "LoanAmount", "Loan_Amount_Term", "Credit_History"]
CATEGORICAL = [c for c in FEATURES if c not in NUMERIC]

def main():
    if not DATA_PATH.exists():
        print("Downloading the public loan prediction CSV...")
        pd.read_csv(DATA_URL).to_csv(DATA_PATH, index=False)
    df = pd.read_csv(DATA_PATH)
    required = FEATURES + ["Loan_Status"]
    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")
    df = df[required].copy()
    df["Dependents"] = df["Dependents"].replace({"3+": "3"})
    y = df.pop("Loan_Status").map({"Y": 1, "N": 0})
    valid = y.notna()
    X, y = df.loc[valid], y.loc[valid].astype(int)

    preprocessor = ColumnTransformer([
        ("numeric", Pipeline([("imputer", SimpleImputer(strategy="median"))]), NUMERIC),
        ("categorical", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore"))
        ]), CATEGORICAL)
    ])

    candidates = {
        "LogisticRegression": LogisticRegression(max_iter=2000, class_weight="balanced"),
        "DecisionTree": DecisionTreeClassifier(max_depth=4, min_samples_leaf=8, class_weight="balanced", random_state=42),
        "RandomForest": RandomForestClassifier(n_estimators=500, max_depth=5, min_samples_leaf=5,
                                               class_weight="balanced_subsample", random_state=42),
        "ExtraTrees": ExtraTreesClassifier(n_estimators=500, max_depth=5, min_samples_leaf=5,
                                           class_weight="balanced", random_state=42)
    }

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    results = {}
    fitted = {}
    for name, estimator in candidates.items():
        pipe = Pipeline([("preprocessor", preprocessor), ("model", estimator)])
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        scores = cross_validate(pipe, X_train, y_train, cv=cv,
                                scoring={"f1": "f1", "roc_auc": "roc_auc", "accuracy": "accuracy"})
        pipe.fit(X_train, y_train)
        pred = pipe.predict(X_test)
        proba = pipe.predict_proba(X_test)[:, 1]
        results[name] = {
            "cv_f1_mean": float(scores["test_f1"].mean()),
            "cv_roc_auc_mean": float(scores["test_roc_auc"].mean()),
            "cv_accuracy_mean": float(scores["test_accuracy"].mean()),
            "test_accuracy": float(accuracy_score(y_test, pred)),
            "test_precision": float(precision_score(y_test, pred, zero_division=0)),
            "test_recall": float(recall_score(y_test, pred, zero_division=0)),
            "test_f1": float(f1_score(y_test, pred, zero_division=0)),
            "test_roc_auc": float(roc_auc_score(y_test, proba)),
            "confusion_matrix": confusion_matrix(y_test, pred).tolist()
        }
        fitted[name] = pipe

    # Select using cross-validated F1 to reduce reliance on one small holdout split.
    best_name = max(results, key=lambda n: results[n]["cv_f1_mean"])
    best_pipeline = fitted[best_name]
    # Refit the selected pipeline on all labelled rows for deployment.
    best_pipeline.fit(X, y)
    joblib.dump({"pipeline": best_pipeline, "model_name": best_name,
                 "feature_columns": FEATURES, "classes": ["Not Eligible", "Eligible"]}, MODEL_PATH)
    report = {
        "dataset": DATA_URL,
        "rows_used": int(len(X)),
        "target_distribution": {str(k): int(v) for k, v in y.value_counts().sort_index().items()},
        "selected_model": best_name,
        "selection_metric": "mean 5-fold cross-validation F1",
        "models": results,
        "note": "Educational benchmark only. The public dataset is small and historical; this is not a bank underwriting model."
    }
    METRICS_PATH.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    print(f"\nSaved model: {MODEL_PATH}")

if __name__ == "__main__":
    main()
