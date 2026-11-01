import requests

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
    "Property_Area": "Urban"
}
response = requests.post("http://127.0.0.1:5000/predict", json=sample, timeout=10)
print(response.status_code)
print(response.json())
