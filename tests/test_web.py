from __future__ import annotations

import re

from extensions import db
from models import Application, User
from repositories import ApplicationRepository, UserRepository
from tests.helpers import (
    SAMPLE_APPLICATION,
    SAMPLE_APPLICATION_NOT_ELIGIBLE,
    csrf_token,
    login,
    login_admin,
    logout,
    make_user,
    seed_application,
    submit_application,
)


def test_public_pages_and_service_health(client):
    home = client.get("/")
    assert home.status_code == 200
    assert b"Important disclaimer" in home.data
    assert b"RandomForest" in home.data
    assert b"Machine-learning decision support" in home.data

    health = client.get("/health")
    assert health.status_code == 200
    payload = health.get_json()
    assert payload["status"] == "ok"
    assert payload["database"] == "ok"
    assert payload["model"]["ready"] is True
    assert payload["model"]["feature_count"] == 11

    for path in ("/login", "/register", "/admin/login"):
        response = client.get(path)
        assert response.status_code == 200, path

    protected = client.get("/apply")
    assert protected.status_code == 302
    assert "/login" in protected.headers["Location"]

    history = client.get("/history")
    assert history.status_code == 302
    assert "/login" in history.headers["Location"]


def test_csrf_protection_rejects_missing_token(client):
    response = client.post(
        "/login",
        data={"email": "nobody@example.com", "password": "Whatever1"},
    )
    assert response.status_code == 400
    assert b"form session expired" in response.data.lower()


def test_registration_duplicate_login_and_logout(app, client):
    token = csrf_token(client, "/register")
    weak = client.post(
        "/register",
        data={
            "csrf_token": token,
            "full_name": "Asha Verma",
            "email": "asha@example.com",
            "password": "short",
            "confirm_password": "short",
        },
    )
    assert weak.status_code == 200
    assert b"at least 8 characters" in weak.data

    token = csrf_token(client, "/register")
    created = client.post(
        "/register",
        data={
            "csrf_token": token,
            "full_name": "Asha Verma",
            "email": "Asha@Example.com",
            "password": "StrongPass1",
            "confirm_password": "StrongPass1",
        },
    )
    assert created.status_code == 302
    assert "/login" in created.headers["Location"]

    with app.app_context():
        user = UserRepository.get_by_email("asha@example.com")
        assert user is not None
        assert user.email == "asha@example.com"
        assert user.role == "user"
        assert user.password_hash != "StrongPass1"
        assert user.check_password("StrongPass1")
        user_id = user.id

    duplicate_token = csrf_token(client, "/register")
    duplicate = client.post(
        "/register",
        data={
            "csrf_token": duplicate_token,
            "full_name": "Another Name",
            "email": "ASHA@example.com",
            "password": "StrongPass2",
            "confirm_password": "StrongPass2",
        },
    )
    assert duplicate.status_code == 200
    assert b"already exists" in duplicate.data

    wrong = login(client, email="asha@example.com", password="WrongPass1")
    assert wrong.status_code == 200
    assert b"Email or password is incorrect" in wrong.data

    successful = login(client, email="asha@example.com", password="StrongPass1")
    assert successful.status_code == 302
    assert successful.headers["Location"].endswith("/history")

    with app.app_context():
        user = db.session.get(User, user_id)
        assert user.last_login_at is not None

    logout_response = logout(client)
    assert logout_response.status_code == 302
    assert client.get("/history").status_code == 302


def test_admin_role_protection_and_admin_login(app, client, user_id, admin_id):
    assert login(client, email="asha@example.com", password="StrongPass1").status_code == 302
    forbidden = client.get("/admin/")
    assert forbidden.status_code == 403
    assert b"This area is restricted" in forbidden.data

    regular_admin_attempt = login_admin(client, email="asha@example.com", password="StrongPass1")
    assert regular_admin_attempt.status_code == 200
    assert b"does not have administrator access" in regular_admin_attempt.data

    admin_login = login_admin(client, email="admin@example.com", password="AdminPass1")
    assert admin_login.status_code == 302
    assert admin_login.headers["Location"].endswith("/admin/")
    dashboard = client.get("/admin/")
    assert dashboard.status_code == 200
    assert b"Eligibility dashboard" in dashboard.data
    assert b"Model performance" in dashboard.data
    assert b"RandomForest" in dashboard.data
    assert b"82.1%" in dashboard.data
    assert b"87.5%" in dashboard.data


def test_application_submission_result_ownership_and_admin_view(app, client, user_id):
    assert login(client).status_code == 302
    form = client.get("/apply")
    assert form.status_code == 200
    for field in (
        "Gender",
        "Married",
        "Dependents",
        "Education",
        "Self_Employed",
        "ApplicantIncome",
        "CoapplicantIncome",
        "LoanAmount",
        "Loan_Amount_Term",
        "Credit_History",
        "Property_Area",
    ):
        assert f'name="{field}"'.encode() in form.data

    response = submit_application(client)
    assert response.status_code == 302
    match = re.search(r"/result/(\d+)", response.headers["Location"])
    assert match
    application_id = int(match.group(1))

    with app.app_context():
        application = db.session.get(Application, application_id)
        assert application is not None
        assert application.applicant_name == "Asha Verma"
        assert application.Gender == "Male"
        assert application.ApplicantIncome == 5849
        assert application.Credit_History == 1
        assert application.prediction == 1
        assert 0.5 <= application.eligibility_probability <= 1
        assert application.prediction_confidence == application.eligibility_probability
        assert application.model_name == "RandomForest"

    result = client.get(response.headers["Location"])
    assert result.status_code == 200
    assert b"Prediction result" in result.data
    assert b"Eligible" in result.data
    assert b"Eligibility probability" in result.data
    assert b"61.5%" in result.data
    assert b"RandomForest" in result.data
    assert b"UTC" in result.data
    assert b"APP-00001" in result.data

    history = client.get("/history")
    assert history.status_code == 200
    assert b"APP-00001" in history.data
    assert b"Asha Verma" in history.data

    second_id = make_user(
        app, name="Second User", email="second@example.com", password="SecondPass1"
    )
    assert second_id != user_id
    logout(client)
    assert login(client, email="second@example.com", password="SecondPass1").status_code == 302
    other_result = client.get(f"/result/{application_id}")
    assert other_result.status_code == 404

    make_user(
        app,
        name="System Administrator",
        email="admin@example.com",
        password="AdminPass1",
        role="admin",
    )
    admin_login = login_admin(client, email="admin@example.com", password="AdminPass1")
    assert admin_login.status_code == 302
    admin_view = client.get(f"/admin/applications/{application_id}")
    assert admin_view.status_code == 200
    assert b"Administrator view" in admin_view.data


def test_application_validation_rejects_missing_and_invalid_values(app, client, user_id):
    assert login(client).status_code == 302

    with app.app_context():
        before = db.session.query(Application).count()
    assert before == 0

    missing_token = csrf_token(client, "/apply")
    missing_payload = dict(SAMPLE_APPLICATION)
    missing_payload["csrf_token"] = missing_token
    del missing_payload["ApplicantIncome"]
    del missing_payload["Credit_History"]
    missing = client.post("/apply", data=missing_payload)
    assert missing.status_code == 200
    assert b"could not submit" in missing.data.lower()
    assert b"Applicant income is required" in missing.data
    assert b"Credit history is required" in missing.data

    invalid_token = csrf_token(client, "/apply")
    invalid_payload = dict(SAMPLE_APPLICATION)
    invalid_payload.update(
        {
            "csrf_token": invalid_token,
            "Gender": "Unknown",
            "ApplicantIncome": "-5",
            "LoanAmount": "abc",
            "Loan_Amount_Term": "0",
            "Credit_History": "2",
        }
    )
    invalid = client.post("/apply", data=invalid_payload)
    assert invalid.status_code == 200
    assert b"Choose a valid gender option" in invalid.data
    assert b"Applicant income must be between" in invalid.data
    assert b"Loan amount must be a valid number" in invalid.data
    assert b"Loan term must be between" in invalid.data
    assert b"Credit history must be between" in invalid.data

    with app.app_context():
        assert db.session.query(Application).count() == 0


def test_history_search_filter_sort_and_pagination(app, client, user_id):
    assert login(client, email="asha@example.com", password="StrongPass1").status_code == 302
    first_id = seed_application(app, user_id, SAMPLE_APPLICATION)
    second_id = seed_application(app, user_id, SAMPLE_APPLICATION_NOT_ELIGIBLE)
    third_data = dict(SAMPLE_APPLICATION)
    third_data["applicant_name"] = "Meera Shah"
    third_id = seed_application(app, user_id, third_data)

    history = client.get("/history")
    assert history.status_code == 200
    assert b"Asha Verma" in history.data
    assert b"Ravi Kumar" in history.data
    assert b"Meera Shah" in history.data
    assert b"Total assessments" in history.data

    search = client.get("/history?q=Ravi")
    assert search.status_code == 200
    assert b"Ravi Kumar" in search.data
    assert b"1 result matches" in search.data
    assert b"APP-00001" not in search.data
    assert b"APP-00003" not in search.data

    eligible = client.get("/history?status=eligible")
    assert eligible.status_code == 200
    assert b"2 results match" in eligible.data
    assert b"APP-00002" not in eligible.data

    ineligible = client.get("/history?status=not_eligible")
    assert ineligible.status_code == 200
    assert b"1 result matches" in ineligible.data
    assert b"APP-00001" not in ineligible.data
    assert b"APP-00003" not in ineligible.data

    by_id = client.get(f"/history?q={second_id}")
    assert by_id.status_code == 200
    assert b"Ravi Kumar" in by_id.data

    page_one = client.get("/history?sort=newest&page=1")
    page_two = client.get("/history?sort=newest&page=2")
    assert page_one.status_code == 200
    assert page_two.status_code == 200
    assert b"Page 1 of 2" in page_one.data
    assert b"Page 2 of 2" in page_two.data

    detail = client.get(f"/history/{third_id}")
    assert detail.status_code == 200
    assert b"Meera Shah" in detail.data
    assert b"Prediction record" in detail.data


def test_repository_filters_preserve_real_outcomes(app, user_id):
    with app.app_context():
        sample = dict(SAMPLE_APPLICATION)
        sample.pop("applicant_name")
        seed_application(app, user_id, SAMPLE_APPLICATION)
        seed_application(app, user_id, SAMPLE_APPLICATION_NOT_ELIGIBLE)
        stats = ApplicationRepository.stats_for_user(user_id)
        assert stats["total"] == 2
        assert stats["eligible"] == 1
        assert stats["ineligible"] == 1
        assert stats["average_probability"] is not None

        pagination = ApplicationRepository.paginate_for_user(
            user_id, query="Ravi", status="all", page=1, per_page=10
        )
        assert pagination.total == 1
        assert pagination.items[0].applicant_name == "Ravi Kumar"


def test_admin_dashboard_metrics_chart_export_and_delete(app, client, user_id, admin_id):
    first_id = seed_application(app, user_id, SAMPLE_APPLICATION)
    second_id = seed_application(app, user_id, SAMPLE_APPLICATION_NOT_ELIGIBLE)

    assert login_admin(client).status_code == 302
    dashboard = client.get("/admin/")
    assert dashboard.status_code == 200
    assert b'data-eligible="1"' in dashboard.data
    assert b'data-ineligible="1"' in dashboard.data
    assert b"Eligibility distribution" in dashboard.data
    assert b"Model performance" in dashboard.data
    assert b"82.1%" in dashboard.data
    assert b"84.6%" in dashboard.data
    assert b"90.6%" in dashboard.data
    assert b"87.5%" in dashboard.data
    assert b"81.9%" in dashboard.data
    assert b"Confusion matrix" in dashboard.data
    assert b"True negative" in dashboard.data
    assert b"False positive" in dashboard.data
    assert b"True positive" in dashboard.data

    apps = client.get("/admin/applications")
    assert apps.status_code == 200
    assert b"Asha Verma" in apps.data
    assert b"Ravi Kumar" in apps.data

    filtered = client.get("/admin/applications?q=Ravi&status=not_eligible")
    assert filtered.status_code == 200
    assert b"Ravi Kumar" in filtered.data
    assert b"Asha Verma" not in filtered.data

    export = client.get("/admin/applications/export")
    assert export.status_code == 200
    assert export.headers["Content-Type"].startswith("text/csv")
    assert "attachment" in export.headers["Content-Disposition"]
    assert export.data.startswith(b"\xef\xbb\xbf")
    assert b"Reference,Applicant name" in export.data
    assert b"APP-00001" in export.data
    assert b"Eligible" in export.data

    with app.app_context():
        before = db.session.query(Application).count()
    token = csrf_token(client, "/admin/applications")
    deleted = client.post(
        f"/admin/applications/{first_id}/delete",
        data={"csrf_token": token},
    )
    assert deleted.status_code == 302
    with app.app_context():
        assert db.session.query(Application).count() == before - 1
        assert db.session.get(Application, first_id) is None
        assert db.session.get(Application, second_id) is not None


def test_api_prediction_contract_and_validation(client):
    valid = client.post("/predict", json={k: v for k, v in SAMPLE_APPLICATION.items() if k != "applicant_name"})
    assert valid.status_code == 200
    payload = valid.get_json()
    assert payload["prediction"] == "Eligible"
    assert payload["predicted_class"] == 1
    assert 0 <= payload["eligibility_probability"] <= 1
    assert payload["model_probability"] == payload["prediction_confidence"]
    assert payload["model"] == "RandomForest"
    assert "disclaimer" in payload

    missing = client.post("/predict", json={"Gender": "Male"})
    assert missing.status_code == 400
    body = missing.get_json()
    assert body["error"] == "Validation failed."
    assert "ApplicantIncome" in body["fields"]
    assert "Credit_History" in body["fields"]

    invalid = client.post(
        "/predict",
        json={
            "Gender": "Male",
            "Married": "Yes",
            "Dependents": "0",
            "Education": "Graduate",
            "Self_Employed": "No",
            "ApplicantIncome": -10,
            "CoapplicantIncome": 0,
            "LoanAmount": 100,
            "Loan_Amount_Term": 360,
            "Credit_History": 5,
            "Property_Area": "Urban",
        },
    )
    assert invalid.status_code == 400
    assert "ApplicantIncome" in invalid.get_json()["fields"]
    assert "Credit_History" in invalid.get_json()["fields"]

    not_json = client.post("/predict", data="not json", content_type="text/plain")
    assert not_json.status_code == 400


def test_unknown_application_and_unknown_page(client):
    missing = client.get("/this-page-does-not-exist")
    assert missing.status_code == 404
    assert b"We could not find that page" in missing.data

    assert client.get("/pretend").status_code == 404
