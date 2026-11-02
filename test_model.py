"""Live smoke test for the running Flask service.

Start the application in one terminal:
    .\\.venv\\Scripts\\python.exe app.py

Then run this script in another terminal:
    .\\.venv\\Scripts\\python.exe test_model.py
"""
from __future__ import annotations

import sys

import requests

BASE_URL = "http://127.0.0.1:5000"

VALID_APPLICATION = {
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


def main() -> int:
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=10)
        health.raise_for_status()
        health_data = health.json()
        assert health_data["status"] == "ok"
        assert health_data["database"] == "ok"
        assert health_data["model"]["ready"] is True
        assert health_data["model"]["feature_count"] == 11
        print(f"Health: OK ({health_data['model']['model_name']}, 11 features)")

        valid = requests.post(
            f"{BASE_URL}/predict", json=VALID_APPLICATION, timeout=10
        )
        valid.raise_for_status()
        valid_data = valid.json()
        assert valid_data["predicted_class"] in (0, 1)
        assert 0 <= valid_data["eligibility_probability"] <= 1
        print(
            "Valid prediction: "
            f"{valid_data['prediction']} "
            f"(eligibility probability "
            f"{valid_data['eligibility_probability'] * 100:.1f}%)"
        )

        invalid_payload = {
            **VALID_APPLICATION,
            "Credit_History": 7,
            "LoanAmount": -1,
        }
        invalid = requests.post(f"{BASE_URL}/predict", json=invalid_payload, timeout=10)
        assert invalid.status_code == 400, invalid.text
        invalid_data = invalid.json()
        assert "errors" in invalid_data
        print(f"Invalid prediction: correctly rejected with {len(invalid_data['errors'])} field errors")

        not_json = requests.post(
            f"{BASE_URL}/predict",
            data="not json",
            headers={"Content-Type": "text/plain"},
            timeout=10,
        )
        assert not_json.status_code == 400, not_json.text
        print("Non-JSON prediction request: correctly rejected")
    except requests.RequestException as exc:
        print(f"Could not reach {BASE_URL}: {exc}", file=sys.stderr)
        print("Start the app with: .\\.venv\\Scripts\\python.exe app.py", file=sys.stderr)
        return 1
    except (AssertionError, KeyError, ValueError) as exc:
        print(f"Smoke test failed: {exc}", file=sys.stderr)
        return 1

    print("\nLive smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
