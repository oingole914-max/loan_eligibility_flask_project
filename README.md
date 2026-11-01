# Loan Eligibility Prediction — Flask + Machine Learning

This project follows the fields and workflow in the supplied synopsis: gender, marital status, dependents, education, self-employment, applicant/co-applicant income, loan amount, loan term, credit history and property area.

## Important setup note

The package contains the complete reproducible training pipeline and Flask API. The fitted `loan_model.pkl` is created locally by `train_model.py` from the public 614-row Loan Prediction dataset. It is not possible to include a genuinely fitted pickle in this archive because the execution environment could not retrieve the CSV during packaging. Run the training command below once; after that, Flask loads the saved model directly and does not retrain on each request.

Dataset: https://huggingface.co/datasets/mariosyahirhalimm/loan_prediction_dataset
CSV: https://huggingface.co/datasets/mariosyahirhalimm/loan_prediction_dataset/raw/main/loan_prediction_dataset.csv

## 1. Install

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

## 2. Train and save the model (one time)

```bash
python train_model.py
```

This downloads `loan_prediction_dataset.csv` if it is not present, compares Logistic Regression, Decision Tree, Random Forest and Extra Trees using 5-fold cross-validation, evaluates a holdout set, selects the model with the best mean CV F1, then saves:

- `loan_model.pkl` — complete fitted preprocessing + classifier pipeline
- `model_metrics.json` — model comparison and holdout metrics

The saved pipeline includes missing-value imputation and categorical one-hot encoding. Do not preprocess the input separately in Flask.

## 3. Start Flask

```bash
python app.py
```

Open http://127.0.0.1:5000/ or call `POST http://127.0.0.1:5000/predict`.

## 4. Example JSON

```json
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
  "Property_Area": "Urban"
}
```

## 5. Test API

With Flask running in another terminal:

```bash
python test_model.py
```

## Notes

- `Loan_ID` is deliberately excluded because it is an identifier, not a meaningful applicant feature.
- `Dependents` accepts `0`, `1`, `2`, `3` or `3+`.
- `Credit_History`: 1 means the historical dataset marks credit history as meeting guidelines; 0 means it does not.
- The reported probability is the model's estimated probability for its predicted class, not a calibrated chance of bank approval.
- The public dataset is small, historical and may encode institutional/social biases. This is for academic demonstration and must not be used for real lending decisions.
- Pickle/joblib files should only be loaded from trusted sources. Re-train locally from the included script.
