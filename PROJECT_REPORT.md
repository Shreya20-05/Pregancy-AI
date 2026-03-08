# PROJECT REPORT

## INTRODUCTION

### 1.1 ABOUT THE PROJECT

PregnancyAI (MaternalGuard) is a web-based maternal health monitoring and risk-support platform built using Flask and SQLite. It provides separate patient and doctor workflows for prediction, communication, appointments, records, and reports.  
The project also includes a Care Hub module for symptom tracking, medication reminders, nutrition logs, kick-count monitoring, lab tracking, explainable AI, follow-up generation, and SOS support.

### 1.2 OBJECTIVE OF THE PROJECT

- Provide early and accessible maternal risk assessment support.
- Digitize patient-doctor interaction through one portal.
- Maintain longitudinal maternal health data in a structured database.
- Reduce missed follow-ups through automated workflows and notifications.
- Improve decision transparency through explainable prediction output.

### 1.3 SCOPE OF THE PROJECT

- Patient-side data entry and risk assessment.
- Doctor-side patient monitoring and communication.
- Appointment, reports, and medical record workflows.
- Addon-based daily monitoring modules through Care Hub APIs.
- Local deployment with SQLite and session-based authentication.

### 1.4 PROBLEM STATEMENT

Maternal care monitoring is often fragmented across notebooks, verbal updates, and isolated lab reports. This creates delayed risk detection, weak follow-up tracking, and communication gaps between patient and doctor.  
The system addresses this by integrating prediction, monitoring, communication, and follow-up automation in one application.

## MODULE DESCRIPTION

1. Authentication and Role Management (`patient`, `doctor`, `admin`)
2. Risk Prediction Module (8-vital input)
3. Dashboard and History Module
4. Appointment Management Module
5. Medical Records Module
6. Messaging Module
7. Reports Module
8. Notifications Module
9. Doctor Patient Management Module
10. Care Hub Addon Modules:
- Symptom Tracker
- Medication Reminder and Adherence
- Nutrition Tracking
- Kick Count Monitoring
- Lab Trend Analyzer
- Auto Follow-up Workflow
- Explainable AI Reports
- Emergency SOS and Referrals

## SYSTEM SPECIFICATION

### 2.1 HARDWARE SPECIFICATION

- Processor: Intel i3 (or higher)
- RAM: 8 GB minimum (16 GB recommended)
- Storage: 10 GB free disk space minimum
- Display: 1366x768 or higher
- Network: Internet/LAN required for external package install

### 2.2 SOFTWARE SPECIFICATION

- Operating System: Windows 10/11 or Linux
- Language: Python 3.10+
- Framework: Flask
- ORM: SQLAlchemy (Flask-SQLAlchemy)
- Authentication: Flask-Login
- Database: SQLite
- Frontend: HTML, Tailwind CSS (CDN), JavaScript
- ML Support: scikit-learn, NumPy

### 2.3 SOFTWARE DESCRIPTION

The project is implemented as a monolithic Flask application (`app.py`) with addon endpoints mounted under `/api/addons`.  
Core and addon models are persisted in SQLite.  
Jinja templates provide role-aware UI pages.  
Prediction uses a trained model (`pregnancy_risk_model.pkl`) with fallback rule logic if model artifacts are unavailable.

## SYSTEM STUDY

### 3.1 EXISTING SYSTEM

Conventional maternal monitoring in many contexts is manual or semi-digital, with fragmented records and limited proactive alerts.

### 3.1.1 LIMITATION OF EXISTING SYSTEM

- No centralized data view across visits.
- Weak follow-up tracking and reminder flow.
- Delayed communication and incident reporting.
- Limited explainability in risk assessment.
- No unified emergency escalation mechanism.

### 3.2 PROPOSED SYSTEM

MaternalGuard centralizes maternal data, prediction support, follow-up automation, doctor communication, and emergency handling in one platform.

### 3.2.1 ADVANTAGES OF PROPOSED SYSTEM

- Unified patient-doctor workflow.
- Faster risk visibility from structured vitals and history.
- Automated follow-up generation from latest records.
- Explainability output for prediction interpretation.
- Integrated SOS event logging and referral suggestions.
- Better traceability through database-backed records.

## SYSTEM DESIGN

### 4.1 ARCHITECTURE DESIGN

The system follows a three-layer architecture:

- Presentation Layer: Jinja templates (`templates/*.html`)
- Application Layer: Flask routes (`app.py`, `addons/routes.py`)
- Data Layer: SQLAlchemy models (`models.py`, `addons/models.py`) with SQLite

High-level flow:

```text
User -> Web UI -> Flask Routes -> Services/Validation -> SQLite DB -> JSON/HTML Response
```

### 4.2 DATA FLOW DESIGN

1. User submits form data from UI.
2. Flask route validates and normalizes payload.
3. Business logic computes derived values (risk, alerts, advice, trends).
4. Data is persisted to database.
5. Response is returned to UI as HTML or JSON.
6. UI displays status and logs response details.

### 4.3 INPUT DESIGN

Key input groups:

- Risk prediction inputs: age, BMI, systolic BP, diastolic BP, blood sugar, body temperature, heart rate, diabetes.
- Appointment inputs: patient, doctor, date/time, reason.
- Messaging inputs: recipient, content, method.
- Care Hub inputs: symptom severity, medication timing, nutrition values, kick sessions, lab test/value, prediction ID, SOS message.

Input controls include numeric fields, date/time pickers, select boxes, and checkboxes with server-side validation.

### OUTPUT DESIGN

Key outputs:

- Risk category (`High`, `Medium`, `Low`) and guidance.
- Dashboard statistics and history summaries.
- Appointment, report, and message status updates.
- Care Hub structured outputs:
- symptom alert level and advice
- lab status and interpretation
- auto follow-up task list
- explainability factors and summary
- SOS event, contacts, and referral list

### TABLE DESIGN

Core tables:

- `users`
- `predictions`
- `appointments`
- `medical_records`
- `reports`
- `messages`
- `notifications`

Addon tables:

- `addon_symptom_entries`
- `addon_medication_reminders`
- `addon_medication_adherence`
- `addon_pregnancy_profiles`
- `addon_nutrition_logs`
- `addon_kick_count_sessions`
- `addon_lab_results`
- `addon_followup_tasks`
- `addon_explainability_reports`
- `addon_emergency_contacts`
- `addon_sos_events`

## SYSTEM TESTING

### 5.1 TESTING

Testing approach used:

- Functional testing of web routes and APIs
- Input validation testing (empty/invalid fields)
- Role-based access checks (patient vs doctor/admin)
- UI workflow testing on main templates
- Care Hub endpoint checks from `/addons`

Sample tested scenarios:

| Test Case | Input | Expected Result | Status |
|---|---|---|---|
| Login | Valid credentials | User redirected to dashboard | Pass |
| Prediction | Valid vitals | Prediction saved and shown | Pass |
| Prediction | Non-numeric required field | Error message | Pass |
| Appointment create | Valid data | Appointment created | Pass |
| Explainability | Valid prediction ID | Summary with factors | Pass |
| Explainability | Invalid prediction ID | Error response | Pass |
| SOS trigger | Message submitted | SOS event stored with response payload | Pass |

## SYSTEM IMPLEMENTATION AND MAINTENANCE

Implementation summary:

1. Install Python environment and dependencies.
2. Start app (`app.py`).
3. Initialize database tables via app startup (`db.create_all()`).
4. Register and use role-based accounts.
5. Execute workflows from UI and APIs.

Maintenance activities:

- Backup `instance/maternalguard.db` periodically.
- Monitor logs and API errors.
- Rotate secret/config values for production.
- Validate model/scaler artifacts after retraining.
- Review unresolved follow-up tasks and notifications.

## CONCLUSION

PregnancyAI (MaternalGuard) provides an integrated maternal health platform with prediction support, clinical communication, and workflow automation.  
It improves continuity of care by combining core maternal records with addon modules for daily monitoring and escalation.

## FUTURE ENHANCEMENT

- Add migration framework (Alembic/Flask-Migrate).
- Add automated unit/integration test suite in CI.
- Add richer analytics dashboards and trend charts.
- Add multilingual UI and accessibility improvements.
- Add mobile app and push notification support.
- Add stronger production security hardening and audit trails.
- Add export-ready report formats (PDF/CSV with templates).

## REFERENCE

1. Flask Documentation: https://flask.palletsprojects.com/
2. Flask-Login Documentation: https://flask-login.readthedocs.io/
3. SQLAlchemy Documentation: https://docs.sqlalchemy.org/
4. scikit-learn Documentation: https://scikit-learn.org/stable/
5. Tailwind CSS Documentation: https://tailwindcss.com/docs

## APPENDIX

### A. CODE

Primary source files:

- `app.py`
- `models.py`
- `auth.py`
- `addons/routes.py`
- `addons/services.py`
- `addons/models.py`
- `templates/*.html`

### B. SCREENSHOTS

Suggested screenshots to attach:

1. Login page
2. Patient dashboard
3. Risk prediction result
4. Prediction history (`/accuracy`)
5. Appointments module
6. Messages module
7. Reports module
8. Medical records module
9. Care Hub modules page (`/addons`)
10. SOS trigger response log

