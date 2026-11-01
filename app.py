from pathlib import Path
import joblib
import pandas as pd
from flask import Flask, request, jsonify, render_template

ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "loan_model.pkl"
app = Flask(__name__)

def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError("loan_model.pkl not found. Run: python train_model.py")
    return joblib.load(MODEL_PATH)

bundle = load_model()
pipeline = bundle["pipeline"]
FEATURES = bundle["feature_columns"]

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/health")
def health():
    return jsonify({"status": "ok", "model": bundle["model_name"]})

@app.post("/predict")
def predict():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Send applicant details as JSON."}), 400
    missing = [f for f in FEATURES if f not in payload]
    if missing:
        return jsonify({"error": "Missing fields", "fields": missing}), 400
    try:
        row = {f: payload[f] for f in FEATURES}
        row["Dependents"] = str(row["Dependents"]).replace("3+", "3")
        X = pd.DataFrame([row], columns=FEATURES)
        pred = int(pipeline.predict(X)[0])
        probability = float(pipeline.predict_proba(X)[0][pred])
        return jsonify({
            "prediction": "Eligible" if pred == 1 else "Not Eligible",
            "predicted_class": pred,
            "model_probability": round(probability, 4),
            "model": bundle["model_name"],
            "disclaimer": "Preliminary educational estimate only; not a loan approval decision."
        })
    except (TypeError, ValueError) as exc:
        return jsonify({"error": f"Invalid input: {exc}"}), 400

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
