from __future__ import annotations

import re

from extensions import db
from ml.predictor import get_predictor
from models import User
from repositories import ApplicationRepository

SAMPLE_APPLICATION = {
    "applicant_name": "Asha Verma",
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

SAMPLE_APPLICATION_NOT_ELIGIBLE = {
    "applicant_name": "Ravi Kumar",
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


def csrf_token(client, path: str) -> str:
    response = client.get(path)
    assert response.status_code == 200, f"GET {path} returned {response.status_code}"
    match = re.search(rb'name="csrf_token" value="([^"]+)"', response.data)
    assert match, f"No CSRF token found on {path}"
    return match.group(1).decode()


def register_and_login(client, *, name="Asha Verma", email="asha@example.com", password="StrongPass1"):
    token = csrf_token(client, "/register")
    response = client.post(
        "/register",
        data={
            "csrf_token": token,
            "full_name": name,
            "email": email,
            "password": password,
            "confirm_password": password,
        },
    )
    assert response.status_code == 302
    return login(client, email=email, password=password)


def login(client, *, email="asha@example.com", password="StrongPass1"):
    token = csrf_token(client, "/login")
    return client.post(
        "/login",
        data={"csrf_token": token, "email": email, "password": password},
        follow_redirects=False,
    )


def login_admin(client, *, email="admin@example.com", password="AdminPass1"):
    token = csrf_token(client, "/admin/login")
    return client.post(
        "/admin/login",
        data={"csrf_token": token, "email": email, "password": password},
        follow_redirects=False,
    )


def logout(client):
    token = csrf_token(client, "/apply")
    return client.post("/logout", data={"csrf_token": token}, follow_redirects=False)


def submit_application(client, data=None):
    payload = dict(data or SAMPLE_APPLICATION)
    token = csrf_token(client, "/apply")
    payload["csrf_token"] = token
    return client.post("/apply", data=payload, follow_redirects=False)


def make_user(app, *, name="Asha Verma", email="asha@example.com", password="StrongPass1", role="user"):
    with app.app_context():
        user = User(full_name=name, email=email.lower(), role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user.id


def seed_application(app, user_id: int, data=None):
    with app.app_context():
        user = db.session.get(User, user_id)
        source = dict(data or SAMPLE_APPLICATION)
        source.pop("applicant_name", None)
        applicant_name = (data or SAMPLE_APPLICATION).get("applicant_name", "Asha Verma")
        result = get_predictor().predict(source)
        application = ApplicationRepository.create(
            user,
            {**source, "applicant_name": applicant_name},
            result,
        )
        return application.id
