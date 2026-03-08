# PregnancyAI Addon Modules (Non-Destructive Extension)

This extension adds 8 modules without editing existing project files.

## How It Works

- Existing app remains unchanged.
- Addons are mounted by running `addon_server.py`.
- New API namespace: `/api/addons/...`
- New tables use `addon_` prefix, so there is no conflict with existing schema.

## Run

```bash
python addon_server.py
```

## Added Modules and APIs

### 1) Symptom Tracker + Alert Scoring
- `GET /api/addons/symptoms`
- `POST /api/addons/symptoms`

### 2) Medication & Supplement Reminder
- `GET /api/addons/medications`
- `POST /api/addons/medications`
- `GET /api/addons/medications/<id>/adherence`
- `POST /api/addons/medications/<id>/adherence`
- `GET /api/addons/medications/<id>/summary`

### 3) Nutrition and Weight Gain Tracker
- `GET /api/addons/nutrition/profile`
- `PUT /api/addons/nutrition/profile`
- `GET /api/addons/nutrition/logs`
- `POST /api/addons/nutrition/logs`
- `GET /api/addons/nutrition/insights`

### 4) Fetal Movement (Kick Count)
- `GET /api/addons/kick-count`
- `POST /api/addons/kick-count`

### 5) Lab Trend Analyzer
- `GET /api/addons/labs/results`
- `POST /api/addons/labs/results`
- `GET /api/addons/labs/trends`

### 6) High-Risk Follow-up Workflow
- `GET /api/addons/followups`
- `POST /api/addons/followups`
- `PUT /api/addons/followups/<id>`
- `POST /api/addons/followups/auto-from-latest`

### 7) Explainable AI Report
- `GET /api/addons/explainability/<prediction_id>`
- `GET /api/addons/explainability/reports`

### 8) Emergency SOS + Referral
- `GET /api/addons/sos/contacts`
- `POST /api/addons/sos/contacts`
- `DELETE /api/addons/sos/contacts/<id>`
- `POST /api/addons/sos/trigger`
- `GET /api/addons/sos/events`
- `GET /api/addons/sos/referrals`

## Notes

- Authentication uses existing Flask-Login sessions.
- Doctors/admins can query by `user_id` for most addon APIs.
- Explainability is generated from stored predictions; no changes were made to the existing prediction flow.

