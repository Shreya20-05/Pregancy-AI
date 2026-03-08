# Care Hub User Guide

This guide explains what each Care Hub section does, what to enter, and what output you get.

## 1) What Care Hub Is

Care Hub is the monitoring panel at `/addons` for day-to-day maternal tracking.

It helps you:
- log symptoms and receive alert advice
- save medication reminders
- log nutrition and kick sessions
- save lab values with interpretation
- generate follow-up tasks
- generate explainability for a prediction
- trigger SOS with referral suggestions

## 2) Before You Use It

- Login first.
- Keep at least one prediction saved if you want to use Explainable AI.
- Open `http://127.0.0.1:5000/addons`.

## 3) Where Output Appears

After each action, you get output in two places:
- Status message below the card (quick success/fail message)
- `API Response Log` at the bottom (full JSON payload)

Use API Response Log for full details like IDs, advice, and analysis fields.

## 4) Module-by-Module Usage and Output

### Symptom Tracker

Input:
- Headache `0-3`
- Swelling `0-3`
- Pain `0-3`
- Bleeding checkbox
- Reduced fetal movement checkbox

Action:
- Click `Save Symptom`

Output:
- `entry` object saved with `alert_score` and `alert_level` (`low`, `medium`, `high`, `critical`)
- `advice` text
- For high/critical alerts, system may auto-create follow-up task and notification

### Medication Reminder

Input:
- Medication name
- Dosage
- Times CSV (example: `08:00,20:00`)

Action:
- Click `Create Reminder`

Output:
- `reminder` object saved with `id`, name, dosage, times, status

### Nutrition Log

Input:
- Weight
- Calories
- Protein
- Water

Action:
- Click `Save Nutrition`

Output:
- `log` object saved with nutrition values and date

### Kick Count

Input:
- Kicks count
- Duration (minutes)

Action:
- Click `Save Kick Session`

Output:
- `session` object saved
- `alert_flag` (true/false)
- `advice` message
- If movement is low, system may create follow-up task

### Lab Analyzer

Input:
- Test name (example: `hemoglobin`)
- Numeric value

Action:
- Click `Save Lab Result`

Output:
- `result` object saved with:
- `status` (`normal`, `high`, `low`, `critical`)
- `interpretation` text
- Abnormal values may create follow-up task

### Follow-up Workflow

Action:
- Click `Generate Auto Follow-ups`

Output:
- `created_count`
- `tasks` list created from latest prediction/symptom/lab data

### Explainable AI

Input:
- `Prediction ID`

Action:
- Click `Generate Explanation`

Output:
- `prediction_id`
- `risk_level`
- `summary`
- `top_factors` (main contributors)
- `all_factors` (full factor list)
- `generated_at`
- `report_id` (when saved)

### Emergency SOS

Input:
- Emergency message

Action:
- Click `Trigger SOS`

Output:
- `event` (SOS record)
- `contacts` (registered emergency contacts)
- `referrals` (nearest/default referral options)
- `recommended_action`

## 5) How to Get Prediction ID

Option 1 (fastest):
- Open `http://127.0.0.1:5000/api/predictions`
- Copy the `id` for the prediction you want to explain

Option 2:
- Open `/accuracy` to review prediction history, then match with API data if needed

## 6) Common Errors and Fixes

- `Prediction ID is required`:
- Enter a valid number in Explainable AI.

- `Failed to generate explanation`:
- ID does not exist, or prediction belongs to another user.

- `test_name is required`:
- Enter a lab test name before saving lab result.

- `value must be numeric`:
- Enter a numeric lab value.

- `Care Hub APIs not available`:
- Confirm app started correctly and addons blueprint is registered.

## 7) Recommended Daily Flow

1. Save Symptom.
2. Save Kick Count.
3. Save Nutrition.
4. Save any new Lab Result.
5. Run Auto Follow-ups.
6. Use Explainable AI for latest prediction when needed.

