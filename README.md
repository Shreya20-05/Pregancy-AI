# PregnancyAI (MaternalGuard)

PregnancyAI is a Flask-based maternal health platform with:

- Role-based portals for patients and doctors
- ML-assisted pregnancy risk prediction
- Appointment, messaging, reports, and medical record workflows
- Care Hub addon APIs for symptoms, medication adherence, nutrition, kick counts, lab trends, follow-ups, explainability, and SOS flows

The current codebase runs as a monolithic Flask app (`app.py`) with addon modules mounted under `/api/addons`.

## 1) Current Status

- Main app entrypoint: `app.py`
- Addon sidecar entrypoint: `addon_server.py`
- Database: SQLite (`instance/maternalguard.db`)
- Uploaded files: `uploads/`
- ML artifacts:
  - `pregnancy_risk_model.pkl`
  - `scaler.pkl`

Note: There is no committed `requirements.txt` or root `README.md` in the current repository state; this file documents the project based on the live source.

## 2) Feature Overview

### Core platform

- Authentication and role-based session access (`patient`, `doctor`, `admin`)
- Risk prediction workflow from 8 maternal vitals
- Dashboard and history views
- Appointment request + confirmation lifecycle
- In-app messaging with unread tracking
- Report generation (doctor-created)
- Medical record upload/download/delete
- Notification stream

### Care Hub addons (`/api/addons/*`)

- Symptom tracker with alert scoring
- Medication reminders and adherence logs
- Nutrition profile/logging and insight summary
- Kick count monitoring with alert flagging
- Lab result classification and trend analysis
- Follow-up task workflow (manual + auto-generated)
- Explainability reports for predictions
- SOS events, emergency contacts, and referral lookup

## 3) Tech Stack

- Backend: Flask, Flask-Login, Flask-SQLAlchemy
- ORM/DB: SQLAlchemy + SQLite
- ML: scikit-learn (RandomForestClassifier + StandardScaler), NumPy, pandas
- Frontend: Jinja2 templates, Tailwind CDN, Plotly CDN, Font Awesome

## 4) Repository Layout

```text
PregnancyAI/
  app.py
  addon_server.py
  models.py
  auth.py
  train_advanced_model.py
  predictive_analysis.py
  Maternal_Health_Risk.csv
  pregnancy_risk_model.pkl
  scaler.pkl
  addons/
    __init__.py
    models.py
    referrals.py
    routes.py
    services.py
  templates/
    *.html
  scripts/
    *.py
  instance/
    maternalguard.db
  uploads/
```

## 5) Setup and Run

## Prerequisites

- Python 3.10+ recommended
- Windows PowerShell examples below (adjust for macOS/Linux shell as needed)

## Install dependencies

Because `requirements.txt` is not present, install from imports:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install Flask Flask-Login Flask-SQLAlchemy numpy pandas scikit-learn matplotlib seaborn
```

If `python` is not on PATH, use your local interpreter directly (for example `.\.venv\Scripts\python.exe`).

## Start app

```powershell
.\.venv\Scripts\python.exe app.py
```

App starts at `http://127.0.0.1:5000` by default.

## Optional: retrain model

```powershell
.\.venv\Scripts\python.exe train_advanced_model.py
```

## Optional: sidecar-style addon entrypoint

```powershell
.\.venv\Scripts\python.exe addon_server.py
```

`app.py` already attempts to register addons, so this is mainly an alternate bootstrap path.

## 6) Configuration and Runtime Behavior

Current hard-coded settings in `app.py`:

- `SECRET_KEY = 'maternal-guard-secret-key-2026'`
- `SQLALCHEMY_DATABASE_URI = 'sqlite:///maternalguard.db'`
- `UPLOAD_FOLDER = <repo>/uploads`
- `debug=True` for local run

Startup behavior:

- Loads ML model/scaler if pickle files exist
- Falls back to rule-based risk classification if artifacts fail to load
- Runs `db.create_all()` at startup
- Registers Care Hub blueprint at `/api/addons`

## 7) Authentication and Roles

Session auth is provided by Flask-Login.

- Public routes: `/login`, `/register`
- Protected routes: most pages and all JSON APIs
- Patient users: scoped to own records for most operations
- Doctor/admin users: broader access, including patient directories and clinical views

For API clients, authenticate first using form login and reuse session cookies.

Example:

```bash
curl -c cookies.txt -X POST http://127.0.0.1:5000/login \
  -d "username=YOUR_USER" -d "password=YOUR_PASSWORD"

curl -b cookies.txt http://127.0.0.1:5000/api/predictions
```

## 8) ML Prediction Pipeline

Input features used by prediction flow (`/predict`):

- age
- bmi
- systolic_bp
- diastolic_bp
- blood_sugar
- body_temp
- heart_rate
- diabetes (0/1)

Model behavior:

- If model/scaler loaded: binary prediction from RandomForest (`High` vs `Low`)
- If not loaded: fallback heuristic marks `High` when any threshold is breached:
  - age >= 35
  - bmi >= 30
  - systolic_bp >= 140
  - diastolic_bp >= 90
  - blood_sugar >= 140
  - diabetes == 1

Prediction records are stored in `predictions` table.

## 9) Data Model Summary

Core models (`models.py`):

- `User`: account identity, role, contact fields
- `Prediction`: risk assessment records per patient
- `Appointment`: patient-doctor scheduling and status
- `MedicalRecord`: file metadata and categorization
- `Report`: doctor-authored patient reports
- `Message`: direct user-to-user messages
- `Notification`: per-user alert/notice feed

Addon models (`addons/models.py`):

- `SymptomEntry`
- `MedicationReminder`
- `MedicationAdherence`
- `PregnancyProfile`
- `NutritionLog`
- `KickCountSession`
- `LabResult`
- `FollowUpTask`
- `ExplainabilityReport`
- `EmergencyContact`
- `SOSEvent`

Addon tables are prefixed with `addon_`.

## 10) Route and API Reference

## Web/UI routes

- `GET /` and `GET /dashboard`
- `GET,POST /register`
- `GET,POST /login`
- `GET /logout`
- `GET,POST /predict`
- `GET /accuracy`
- `GET /history`
- `GET /appointments`
- `GET /messages`
- `GET /reports`
- `GET /medical-records`
- `GET /medical_records` (alias)
- `GET /addons`
- `GET /doctor/patients`
- `GET /doctor/notifications`

## Core JSON APIs

All endpoints below require authenticated session.

- `GET,POST /api/appointments`
  - `GET`: doctor/admin sees all; patient sees own
  - `POST`: create appointment request/schedule
- `PUT,DELETE /api/appointments/<appointment_id>`
  - `PUT`: update status/date/reason
  - `DELETE`: marks status `cancelled`
- `POST /api/appointments/<appointment_id>/accept`
  - doctor/admin confirms and claims appointment

- `GET,POST /api/messages`
  - `GET ?with_user=<id>` returns conversation and marks unread from that user as read
  - `POST` sends message
- `GET /api/messages/unread-summary`
- `POST /api/send-message` (alternate message create endpoint)

- `GET,POST /api/reports`
  - `POST` allowed only for doctor/admin

- `GET,POST /api/medical-records`
  - Supports JSON metadata creation and multipart file uploads
- `GET /api/medical-records/<record_id>/download`
- `DELETE /api/medical-records/<record_id>`

- `GET /api/doctors`
- `GET /api/patients` (doctor/admin only)
- `GET /api/predictions`
- `GET /api/users/<user_id>`
- `GET /api/stats`
- `GET /api/notifications`
- `PUT /api/notifications/<notification_id>`

## Care Hub addon APIs (`/api/addons`)

- `GET /api/addons/meta`
- `GET,POST /api/addons/symptoms`
- `GET,POST /api/addons/medications`
- `GET,POST /api/addons/medications/<reminder_id>/adherence`
- `GET /api/addons/medications/<reminder_id>/summary`
- `GET,PUT /api/addons/nutrition/profile`
- `GET,POST /api/addons/nutrition/logs`
- `GET /api/addons/nutrition/insights`
- `GET,POST /api/addons/kick-count`
- `GET,POST /api/addons/labs/results`
- `GET /api/addons/labs/trends`
- `GET,POST /api/addons/followups`
- `PUT /api/addons/followups/<task_id>`
- `POST /api/addons/followups/auto-from-latest`
- `GET /api/addons/explainability/<prediction_id>`
- `GET /api/addons/explainability/reports`
- `GET,POST /api/addons/sos/contacts`
- `DELETE /api/addons/sos/contacts/<contact_id>`
- `POST /api/addons/sos/trigger`
- `GET /api/addons/sos/events`
- `GET /api/addons/sos/referrals`

## 11) Notifications and Automation Flows

The app automatically creates notifications and follow-up records in several flows:

- Appointment created/updated/cancelled/accepted
- Report creation (patient notification)
- High/critical symptom entry
- SOS trigger
- Auto follow-up generation from:
  - latest high-risk prediction
  - latest high/critical symptom
  - latest flagged lab result

## 12) Scripts and Validation

Repository contains utility scripts in `scripts/` for audits, route checks, and template rendering.

Important: Several scripts appear to reference older model APIs/fields (for example `set_password`, old prediction/report fields) and may fail against the current schema.

Recommended safe checks:

- Start app and validate critical pages manually
- Exercise APIs via authenticated requests
- Validate addon endpoints from `/addons` page (built-in API tester UI)

## 13) Troubleshooting

- Login loop or 401 behavior:
  - Confirm browser/session cookies are enabled.

- Prediction falls back unexpectedly:
  - Ensure `pregnancy_risk_model.pkl` and `scaler.pkl` are present and readable.

- File download returns 404:
  - Verify stored `file_path` exists under `uploads/` and file was not deleted.

- Addon APIs unavailable:
  - Check startup logs for blueprint registration errors.

- Database mismatch errors after model changes:
  - Backup `instance/maternalguard.db`, then recreate DB for local development.

## 14) Production Hardening Checklist

Before production deployment, address these items:

- Move secret key to environment variable
- Disable debug mode
- Add pinned dependency file (`requirements.txt` or `pyproject.toml`)
- Add migrations (Flask-Migrate/Alembic) instead of raw `create_all()`
- Enforce stricter access checks for user-detail endpoints
- Add automated tests with current schema and CI execution
- Replace demo referral directory with verified emergency/clinical contacts

---

For source-level details, start with:

- `app.py`
- `models.py`
- `addons/routes.py`
- `addons/services.py`
- `addons/models.py`
