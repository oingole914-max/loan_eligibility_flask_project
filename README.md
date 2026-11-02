# LoanLens — Loan Eligibility Prediction System

A complete Flask + machine-learning web application for demonstrating an end-to-end loan eligibility workflow. Users register, submit the 11 applicant and loan features used by the trained model, receive a real model prediction with probability, and revisit their saved assessments. Administrators get a separate role-protected dashboard with live application totals, a distribution chart, real evaluation metrics and application management.

The original trained pipeline, `loan_model.pkl`, is preserved and loaded from disk. The project does **not** retrain or replace the model during normal setup or while serving requests.

> **Academic disclaimer:** This is a BCA Semester V demonstration project. It is not a bank, a credit bureau, financial advice, or a real lending decision system. Never use it as the sole basis for an actual credit decision.

---

## 1. What is included

| Area | Implementation |
|---|---|
| Web framework | Flask 3.1 application factory with blueprints |
| Machine learning | Preserved `RandomForest` scikit-learn pipeline in `loan_model.pkl` |
| Model input contract | Exactly 11 features, validated on the server |
| Database | SQLite by default; MySQL 8 supported through `DATABASE_URL` |
| Authentication | Registration, customer login, separate admin login, logout |
| Passwords | Werkzeug salted password hashes; no plaintext passwords stored |
| Sessions | Flask-Login with strong session protection and CSRF protection |
| Customer workflow | Application form, prediction result, searchable history |
| Admin workflow | Dashboard, metrics, chart, application table, detail, CSV export, delete |
| Model metrics | Read from the actual `model_metrics.json` file; no invented values |
| UI | Responsive banking-style interface with locally vendored Bootstrap, Bootstrap Icons, Chart.js and Inter |
| Security | CSRF, secure headers/CSP, safe redirects, ownership checks, role checks |
| Verification | Pytest suite plus a live HTTP/API smoke test |

The UI works without an internet connection because all CSS, JavaScript and fonts are stored under `static/vendor/`.

---

## 2. Project structure

```text
loan_eligibility_flask_project/
├── app.py                      # Application factory, CLI, security headers, errors
├── config.py                   # Environment-backed configuration
├── extensions.py               # Database, login manager and CSRF instances
├── models.py                   # User and Application SQLAlchemy models
├── repositories.py             # Database queries, filters, pagination, aggregates
├── routes/
│   ├── main.py                 # Home page and /health
│   ├── auth.py                 # Register, login, admin login, logout
│   ├── applications.py         # Apply, result, history and detail views
│   ├── admin.py                # Admin dashboard, management, export, delete
│   └── api.py                  # Public JSON /predict endpoint
├── ml/
│   ├── predictor.py            # One-time model loading, feature contract, inference
│   ├── metrics.py              # Reads the real evaluation JSON
│   └── schema.py               # Accepted fields, options and validation bounds
├── utils/
│   ├── validators.py           # Registration and model-input validation
│   ├── decorators.py           # Admin-only route decorator
│   ├── security.py             # Safe same-host redirects
│   └── formatting.py           # Currency, date, percentage and text filters
├── templates/                  # Jinja templates for public, customer and admin pages
├── static/
│   ├── css/style.css           # Full responsive design system
│   ├── js/main.js              # Form UX, chart, reveal and print behaviour
│   ├── img/favicon.svg
│   └── vendor/                 # Offline Bootstrap, icons, Chart.js and font assets
├── database/schema.sql         # MySQL 8 schema and constraints
├── scripts/init_db.py          # Optional database/admin initialisation helper
├── tests/                      # Pytest model and web workflow tests
├── loan_model.pkl              # Preserved trained preprocessing + classifier pipeline
├── model_metrics.json          # Actual saved evaluation report
├── loan_prediction_dataset.csv # Historical 614-row training dataset
├── train_model.py              # Reproducible training script (do not run during setup)
├── test_model.py               # Live HTTP smoke test for a running app
├── pytest.ini
├── requirements.txt
├── .env.example
└── README.md
```

---

## 3. Requirements and compatibility

- **Python 3.10 or newer** (the application was verified with Python 3.14.4 on Windows).
- **scikit-learn 1.7.2 is required to load the included pickle.** Do not upgrade it without retraining and re-verifying the model.
- Windows PowerShell commands are shown first. On macOS/Linux, replace `.venv\Scripts\python.exe` with `.venv/bin/python`.

Main dependencies in `requirements.txt`:

```text
Flask==3.1.1
Flask-Login==0.6.3
Flask-SQLAlchemy==3.1.1
Flask-WTF==1.3.0
python-dotenv
PyMySQL
cryptography
joblib
pandas
numpy
scikit-learn==1.7.2
requests
pytest
```

`cryptography` is included because PyMySQL needs it for MySQL 8's default `caching_sha2_password` authentication.

---

## 4. Quick start (Windows PowerShell)

### 4.1 Open the project and create the virtual environment

```powershell
cd D:\loan_eligibility_flask_project

py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation for the current session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

If a prepared `.venv` already exists in this workspace, activate it and reinstall only if dependencies are missing.

### 4.2 Create `.env`

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the generated value into `SECRET_KEY=` in `.env`. The application refuses to start with an empty, short or example secret.

Set the administrator bootstrap values too:

```dotenv
ADMIN_NAME=System Administrator
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=Choose-A-Strong-Password1
```

`.env` is git-ignored. Never commit it. A local `.env` prepared for this workspace already exists; use its `ADMIN_EMAIL` and `ADMIN_PASSWORD` values when signing in locally.

### 4.3 Create the database and administrator

The default configuration uses SQLite at `instance/loan_eligibility.db`. Tables are normally created automatically on first startup, but these commands make the setup explicit:

```powershell
python -m flask --app app init-db
python -m flask --app app create-admin
```

`create-admin` uses `ADMIN_NAME`, `ADMIN_EMAIL` and `ADMIN_PASSWORD` from `.env`. If `ADMIN_PASSWORD` is blank, it prompts securely.

To reset an existing administrator's password or promote an existing account:

```powershell
python -m flask --app app create-admin --update
```

### 4.4 Run the application

```powershell
python app.py
```

or:

```powershell
python -m flask --app app run --debug
```

Open:

- Application: http://127.0.0.1:5000/
- Customer login: http://127.0.0.1:5000/login
- Administrator login: http://127.0.0.1:5000/admin/login
- Health check: http://127.0.0.1:5000/health

On startup the application:

1. validates the environment and database connection;
2. loads `loan_model.pkl` exactly once;
3. runs a model self-check;
4. reads `model_metrics.json` for the real evaluation display.

---

## 5. Running from VS Code

1. Open the folder in VS Code:

   ```powershell
   code D:\loan_eligibility_flask_project
   ```

2. Open the Command Palette (`Ctrl+Shift+P`) and choose **Python: Select Interpreter**.
3. Select:

   ```text
   .\.venv\Scripts\python.exe
   ```

4. Open **Terminal → New Terminal**. The prompt should appear in the project root.
5. If the virtual environment is not automatically active:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

6. Confirm the dependencies and model:

   ```powershell
   python -c "import sklearn; print(sklearn.__version__)"
   ```

   The result must be `1.7.2`.

7. Start the app:

   ```powershell
   python app.py
   ```

8. Open http://127.0.0.1:5000/ in a browser.

For the test suite, open a second terminal and select the same interpreter:

```powershell
python -m pytest -q
```

VS Code can also run the tests from the Testing sidebar after selecting pytest and the `.venv` interpreter.

---

## 6. Environment variables

| Variable | Purpose | Default / notes |
|---|---|---|
| `FLASK_APP` | Flask app entry point | `app.py` |
| `FLASK_DEBUG` | Development debug mode | `0`; keep off for normal use |
| `SECRET_KEY` | Flask session/CSRF signing secret | Required; at least 32 random characters |
| `HOST` | Development bind address | `127.0.0.1` |
| `PORT` | Development port | `5000` |
| `DATABASE_URL` | SQLAlchemy database URL | SQLite at `instance/loan_eligibility.db` |
| `AUTO_CREATE_DB` | Create tables automatically | `1` for first run; use `0` for production |
| `MODEL_PATH` | Path to trained pipeline | `loan_model.pkl` |
| `METRICS_PATH` | Path to evaluation report | `model_metrics.json` |
| `SESSION_COOKIE_SECURE` | HTTPS-only session cookie | `0` locally; set to `1` behind HTTPS |
| `ADMIN_NAME` | `create-admin` display name | `System Administrator` |
| `ADMIN_EMAIL` | `create-admin` email | Required for CLI bootstrap |
| `ADMIN_PASSWORD` | `create-admin` password | Required for non-interactive bootstrap |

Relative `MODEL_PATH` and `METRICS_PATH` values resolve from the project root.

---

## 7. Database setup

### 7.1 SQLite (default)

No separate database server is required. With `AUTO_CREATE_DB=1`, the file `instance/loan_eligibility.db` and its tables are created on startup. You can also run:

```powershell
python -m flask --app app init-db
```

The SQLite file is ignored by Git.

### 7.2 MySQL 8 (optional)

1. Create the database and tables using the supplied schema:

   ```powershell
   mysql -u root -p < database/schema.sql
   ```

2. Create a dedicated application user (example):

   ```sql
   CREATE USER 'loan_user'@'localhost' IDENTIFIED BY 'ChangeMe-Strong1';
   GRANT ALL PRIVILEGES ON loan_eligibility.* TO 'loan_user'@'localhost';
   FLUSH PRIVILEGES;
   ```

3. Set the connection URL in `.env`:

   ```dotenv
   DATABASE_URL=mysql+pymysql://loan_user:ChangeMe-Strong1@127.0.0.1:3306/loan_eligibility?charset=utf8mb4
   AUTO_CREATE_DB=0
   ```

   If the password contains URL-special characters such as `@`, `:`, `/` or `#`, percent-encode them.

4. Initialise/verify the schema and create the admin:

   ```powershell
   python -m flask --app app init-db
   python -m flask --app app create-admin
   ```

5. Start the app and check `/health`; the database field should be `ok`.

The application also normalises a plain `mysql://...` URL to the PyMySQL dialect. `database/schema.sql` is the authoritative MySQL schema. The recorded verification run for this project used SQLite; test the MySQL path against your own MySQL 8 server before deployment.

### 7.3 Schema overview

```text
users 1 ─────────< applications
```

**`users`**

| Column | Notes |
|---|---|
| `id` | Primary key |
| `full_name` | Display name |
| `email` | Unique, lower-cased login identifier |
| `password_hash` | Werkzeug salted hash |
| `role` | `user` or `admin` |
| `created_at` | Naive UTC timestamp |
| `last_login_at` | Updated after successful login |

**`applications`**

| Column group | Columns |
|---|---|
| Ownership | `id`, `user_id` (FK to `users.id`, cascade delete), `applicant_name` |
| Model inputs | `Gender`, `Married`, `Dependents`, `Education`, `Self_Employed`, `ApplicantIncome`, `CoapplicantIncome`, `LoanAmount`, `Loan_Amount_Term`, `Credit_History`, `Property_Area` |
| Outputs | `prediction` (0/1), `eligibility_probability`, `prediction_confidence`, `model_name` |
| Audit | `created_at` |

Indexes cover user history, recent applications, prediction filters and user/created-date lookups. The MySQL schema adds check constraints for the binary prediction fields and probability ranges.

---

## 8. The machine-learning model

### 8.1 Model contract

The persisted object is a complete scikit-learn `Pipeline` containing numeric imputation, categorical imputation/one-hot encoding and a fitted `RandomForestClassifier`. Flask does not preprocess the features again. The pipeline's stored feature list is checked at startup against the application contract.

The 11 accepted features are:

| Feature | Accepted values | Notes |
|---|---|---|
| `Gender` | `Male`, `Female` | Categorical |
| `Married` | `Yes`, `No` | Categorical |
| `Dependents` | `0`, `1`, `2`, `3+` | `3+` is normalised to `3` for the saved pipeline |
| `Education` | `Graduate`, `Not Graduate` | Categorical |
| `Self_Employed` | `Yes`, `No` | Categorical |
| `ApplicantIncome` | 1 to 10,000,000 | Monthly income in the dataset's rupee unit |
| `CoapplicantIncome` | 0 to 10,000,000 | Monthly income |
| `LoanAmount` | 1 to 10,000 | Stored in thousands: `128` means ₹1,28,000 |
| `Loan_Amount_Term` | 12 to 480; whole number | Months |
| `Credit_History` | `0` or `1` | Binary historical credit indicator |
| `Property_Area` | `Urban`, `Semiurban`, `Rural` | Categorical |

`Loan_ID` is deliberately excluded because it is an identifier, not a predictive feature.

### 8.2 Preserved model file

During this project the pickle was **not retrained or modified**. Its SHA-256 is:

```text
47A889CC758F2B62A81BED4EA1BD6534ED2384CB61578B62166AEDC61D92BB09
```

`train_model.py` is included for reproducibility and coursework explanation. Running it will retrain the model, overwrite `loan_model.pkl` and replace `model_metrics.json`; do not run it during normal setup unless you intentionally want a new model.

### 8.3 Actual evaluation results

The selected model is **RandomForest**, chosen by mean 5-fold cross-validation F1 during training. The values below are the actual holdout-test values stored in `model_metrics.json`; they are not generated by the web application.

| Metric | Value |
|---|---|
| Accuracy | 82.1% (0.821138) |
| Precision | 84.6% (0.846154) |
| Recall | 90.6% (0.905882) |
| F1 score | 87.5% (0.875000) |
| ROC-AUC | 81.9% (0.818885) |

Confusion matrix (holdout test set):

|  | Predicted not eligible | Predicted eligible |
|---|---:|---:|
| Actual not eligible | 24 (TN) | 14 (FP) |
| Actual eligible | 8 (FN) | 77 (TP) |

Dataset size: 614 labelled records. Target distribution: 422 eligible / 192 not eligible. The deployed pipeline was refit on all labelled rows after the holdout evaluation, as recorded by `train_model.py`.

### 8.4 Prediction behaviour

- `eligibility_probability` is the model's estimated probability for the eligible class.
- `prediction_confidence` is the probability attached to whichever class was predicted.
- The decision threshold is 50%.
- A probability is a statistical output, not a calibrated bank approval probability.

---

## 9. Application routes

| Method | Route | Access | Purpose |
|---|---|---|---|
| GET | `/` | Public | Marketing-style home page with real model snapshot |
| GET | `/health` | Public | Application, model and database health |
| GET/POST | `/register` | Public | Create a customer account |
| GET/POST | `/login` | Public | Customer sign-in |
| POST | `/logout` | Authenticated | Clear the session |
| GET/POST | `/admin/login` | Public | Separate administrator sign-in |
| GET/POST | `/apply` | Customer/admin | Submit the 11-feature eligibility form |
| GET | `/result/<id>` | Owner/admin | Full prediction result and application summary |
| GET | `/history` | Authenticated | Search, filter, sort and page saved assessments |
| GET | `/history/<id>` | Owner/admin | Saved result detail |
| GET | `/admin/` | Admin | Totals, chart, recent applications, real metrics |
| GET | `/admin/applications` | Admin | All applications with search/filter/pagination |
| GET | `/admin/applications/<id>` | Admin | Administrator result view |
| GET | `/admin/applications/export` | Admin | Filter-aware CSV export |
| POST | `/admin/applications/<id>/delete` | Admin | Delete a record with CSRF protection |
| POST | `/predict` | Public JSON API | Stateless prediction for coursework/API testing |

Customer application records are visible only to their owner; administrators have a separate role-restricted view. A non-owner receiving another customer's application gets a 404 rather than confirmation that the record exists.

---

## 10. JSON API

### Request

```http
POST /predict
Content-Type: application/json

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

### Actual response for the sample above

```json
{
  "prediction": "Eligible",
  "predicted_class": 1,
  "model_probability": 0.6153,
  "prediction_confidence": 0.6153,
  "eligibility_probability": 0.6153,
  "model": "RandomForest",
  "disclaimer": "Preliminary educational estimate only. This is not a loan approval, credit decision, or financial advice."
}
```

Invalid or missing fields return HTTP 400 with an `errors` object keyed by field name. The endpoint does not save records; the web form saves authenticated customer submissions.

---

## 11. Admin setup and use

1. Set `ADMIN_NAME`, `ADMIN_EMAIL` and `ADMIN_PASSWORD` in `.env`.
2. Run:

   ```powershell
   python -m flask --app app create-admin
   ```

3. Open `/admin/login` and sign in with those credentials.
4. The admin dashboard provides:
   - total, eligible, not-eligible and average-probability cards;
   - a Chart.js doughnut chart driven by real database counts;
   - the eight most recent applications;
   - the saved RandomForest holdout metrics, confusion matrix and algorithm comparison;
   - application search by name, email or reference, outcome filtering, pagination, detail view, CSV export and delete.

If an account with that email already exists:

```powershell
python -m flask --app app create-admin --update
```

This promotes it to `admin` and resets its password.

---

## 12. Feature list

### Customer features

- Secure registration and login with server-side validation and hashed passwords.
- All 11 model inputs with clear units, accepted values and validation errors.
- Live household income, loan amount and term preview while filling the form.
- One prediction per application using the preserved saved pipeline.
- Real eligibility probability, prediction confidence and decision threshold.
- Full application summary, model name, reference and UTC timestamp.
- Print-friendly result page.
- Search by applicant name or reference; filter by outcome; sort newest/oldest; pagination.
- Private history with ownership checks.

### Administrator features

- Separate administrator login and role-based access control.
- Live dashboard totals and outcome distribution.
- Recent applications with links to full result details.
- Actual model metrics, confusion matrix and algorithm comparison read from `model_metrics.json`.
- Application search by name, email or reference; outcome filters; pagination.
- Full administrator result view.
- Filter-aware CSV export.
- Permanent delete with confirmation and CSRF protection.

### System features

- Single model load at process startup with compatibility and self-check.
- Strict 11-feature model contract; extra JSON keys are ignored and never forwarded.
- Friendly 400, 403, 404, 413, 500 and CSRF error pages; JSON errors for API requests.
- Health endpoint for model/database checks.
- CSRF protection, secure cookies options, security headers and CSP.
- SQLite zero-config fallback; MySQL 8 URL and schema support.
- CLI commands for database initialisation and administrator creation.
- Offline-capable frontend assets.
- Test suite and live API smoke test.

---

## 13. Testing and verification

### Automated tests

From the project root:

```powershell
python -m pytest -q
```

Recorded result for this workspace:

```text
17 passed
```

The suite covers:

- model loading, saved feature contract and sklearn version;
- real probabilities for eligible and not-eligible applications;
- `3+` dependent normalisation;
- metrics matching `model_metrics.json`;
- public pages, health, protected-route redirects and 404s;
- CSRF rejection;
- registration, duplicate email handling, password hashing and login/logout;
- customer/admin role separation;
- valid and invalid application submission, ownership isolation and admin viewing;
- history search, filters, sorting, pagination and detail;
- admin dashboard data/chart markers, CSV export and delete;
- JSON API contract and validation.

### Live smoke test

With the app running in another terminal:

```powershell
python test_model.py
```

Recorded output:

```text
Health: OK (RandomForest, 11 features)
Valid prediction: Eligible (eligibility probability 61.5%)
Invalid prediction: correctly rejected with 2 field errors
Non-JSON prediction request: correctly rejected

Live smoke test passed.
```

### Browser/workflow verification

The complete workflow was exercised against the running server, including registration, customer login, application submission, result/history pages, customer denial on `/admin/`, administrator login, dashboard rendering, CSV export, deletion and logout. Desktop (1440×1050) and mobile (390×844) layouts were visually checked; the chart rendered and no browser console errors were reported.

The MySQL code path and schema are provided, but the verification run used SQLite because no MySQL service was available in the build environment.

---

## 14. Security notes

- Passwords use Werkzeug's salted password hashing; plaintext passwords are never stored.
- Flask-WTF CSRF protection is enabled for HTML forms. The stateless `/predict` JSON endpoint is intentionally CSRF-exempt and does not persist data.
- Login sessions use Flask-Login's strong session protection; the session is cleared on login and logout.
- Admin routes use an explicit role decorator. Customers receive 403; anonymous users are redirected to login.
- Application detail routes enforce record ownership; admins have a separate permitted path.
- Redirect targets after login are checked to remain on the same host.
- Responses include `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy` and a restrictive Content Security Policy.
- Authenticated pages are marked `Cache-Control: no-store`.
- The app avoids exposing internal exception text to users and logs errors server-side.
- Set `SESSION_COOKIE_SECURE=1` when serving over HTTPS.

For a real deployment, add rate limiting, email verification, password reset, MFA and a reverse proxy/WSGI server. These are outside the academic scope.

---

## 15. Limitations

- **Not a lending system.** The model performs a statistical classification from historical application fields. It does not verify income, identity, documents, credit history or affordability and does not approve or reject a loan.
- **Small historical dataset.** The 614-row public dataset is limited and may contain sampling or social biases. Results should not be generalised to real applicants.
- **No calibration or fairness audit.** The displayed probability is not calibrated to bank approval rates, and no formal disparity/fairness testing has been performed.
- **Exact pickle dependency.** The saved model was created with scikit-learn 1.7.2. Upgrading scikit-learn without retraining may make the pickle unloadable or change behaviour.
- **Academic authentication.** Email verification, password recovery, MFA, account lockout and login rate limiting are not included.
- **No schema migrations.** Tables are created directly. A production deployment should use Alembic/Flask-Migrate.
- **SQLite is single-node.** Use MySQL for a multi-user or server deployment, and test the MySQL environment there.
- **Public API.** `/predict` is deliberately unauthenticated for easy coursework testing; it should be rate-limited or disabled in a public deployment.
- **No edit history/audit trail.** Administrators can inspect, export and delete application records, but changes to records are not versioned.

---

## 16. Troubleshooting

### `RuntimeError: SECRET_KEY is missing, too short...`

Set a random value of at least 32 characters in `.env`:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Restart the app.

### Model unpickling error or `SimpleImputer`/`_fill_dtype` error

The pickle requires scikit-learn **1.7.2**:

```powershell
python -m pip install --force-reinstall scikit-learn==1.7.2
python -c "import sklearn; print(sklearn.__version__)"
```

Do not substitute a different major/minor version.

### `No module named ...`

Activate `.venv` and install the requirements:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### Admin account already exists

Use:

```powershell
python -m flask --app app create-admin --update
```

### MySQL connection/authentication error

- Confirm MySQL is running and `DATABASE_URL` uses `mysql+pymysql://`.
- Confirm the database and user exist and have privileges.
- Percent-encode special characters in the password.
- Ensure `cryptography` is installed (it is in `requirements.txt`).

### CSRF/session-expired message

Refresh the page and resubmit. Make sure cookies are enabled and the app is accessed through the configured host/port rather than switching between `localhost` and `127.0.0.1`.

### SQLite database is locked

Close other Python/Flask processes using the same database, then retry. SQLite is intended for local single-node use.

---

## 17. Reproducing training (optional)

Only do this if you intentionally want to replace the preserved model:

```powershell
python train_model.py
```

The script:

1. downloads the public dataset if the CSV is absent;
2. compares Logistic Regression, Decision Tree, Random Forest and Extra Trees;
3. selects the best mean 5-fold cross-validation F1;
4. evaluates on a stratified holdout set;
5. refits the selected pipeline on all labelled rows;
6. writes `loan_model.pkl` and `model_metrics.json`.

After training, confirm the pickle loads under scikit-learn 1.7.2 and rerun the full test suite. The preserved SHA-256 documented above will no longer apply once you retrain.

---

## 18. Dataset and references

- Dataset CSV: included locally as `loan_prediction_dataset.csv`
- Dataset source: <https://huggingface.co/datasets/mariosyahirhalimm/loan_prediction_dataset>
- Original features: Gender, Married, Dependents, Education, Self_Employed, ApplicantIncome, CoapplicantIncome, LoanAmount, Loan_Amount_Term, Credit_History, Property_Area
- Target used by this project: `Loan_Status` (`Y` → 1 Eligible, `N` → 0 Not Eligible)

---

## 19. Academic use

This project is intended for coursework demonstration of:

- supervised binary classification;
- a persisted preprocessing + model pipeline;
- Flask application structure and REST-style JSON prediction;
- relational data modelling, authentication, authorization and validation;
- responsible communication of model metrics and limitations.

Do not present the model output as a real bank decision or financial recommendation.
