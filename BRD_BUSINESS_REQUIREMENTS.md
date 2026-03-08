# Business Requirements Document (BRD)

## Project
PregnancyAI (MaternalGuard)

## Version
1.0

## Date
March 8, 2026

## Prepared For
Project stakeholders (Product Owner, Clinical Users, Engineering Team)

## 1. Executive Summary
PregnancyAI (MaternalGuard) is a web-based maternal health platform that supports pregnant patients and care providers through risk assessment, communication, appointments, reports, and emergency escalation support.  
The system combines core care workflows with Care Hub modules for day-to-day monitoring (symptoms, medication adherence, nutrition, kick count, lab trends, follow-ups, explainability, and SOS).

The business objective is to reduce delayed maternal risk detection and fragmented follow-up by providing a unified digital care workflow.

## 2. Business Problem
Current maternal care workflows are often fragmented across paper notes, isolated lab updates, and ad-hoc communication. This leads to:
- Delayed detection of high-risk indicators
- Missed or delayed follow-ups
- Low continuity between patient-reported data and doctor action
- Weak emergency escalation and traceability

## 3. Business Goals and Objectives
1. Provide early risk visibility from maternal vitals and trends.
2. Centralize patient-doctor coordination in one platform.
3. Improve follow-up compliance using reminders, tasks, and notifications.
4. Maintain structured longitudinal maternal records.
5. Support safer escalation in urgent scenarios (SOS workflow).
6. Improve trust with explainable prediction outputs.

## 4. Stakeholders
- Pregnant Patients (primary end users)
- Doctors/Clinicians (primary clinical users)
- Admin users (operational governance)
- Product/Operations team (adoption and KPI ownership)
- Engineering/QA team (delivery and maintenance)

## 5. In-Scope vs Out-of-Scope

### In Scope (Current Product Scope)
- Role-based login and registration (`patient`, `doctor`, `admin`)
- Prediction from 8 maternal health inputs
- Patient and doctor dashboards
- Appointment request, acceptance, update, cancellation workflows
- In-app messaging and unread tracking
- Medical record upload/download/delete
- Doctor-authored report creation and patient access
- Notification center
- Care Hub modules:
  - Symptom tracker with alert levels
  - Medication reminders and adherence logs
  - Nutrition profile, logs, and insights
  - Kick count tracking with alert flagging
  - Lab result classification and trend analysis
  - Follow-up task management and auto-generation
  - Explainability summaries for predictions
  - SOS event capture, emergency contacts, referral suggestions

### Out of Scope (For this BRD baseline release)
- Native iOS/Android apps
- External EHR/HIS integration
- Insurance/billing workflows
- Telemedicine video consultation
- Full enterprise IAM/SSO integration

## 6. Business Requirements

### 6.1 Access and Identity
- `BR-01` The system must support account registration and secure login for patient, doctor, and admin roles.
- `BR-02` The system must enforce role-based access so patient data is only visible to permitted users.
- `BR-03` The system must support session-based authenticated access for all protected workflows and APIs.

### 6.2 Maternal Risk Assessment
- `BR-04` The system must capture 8 maternal indicators (age, BMI, systolic BP, diastolic BP, blood sugar, body temperature, heart rate, diabetes flag) and return a risk output.
- `BR-05` The system must store each prediction with timestamp and patient linkage for longitudinal tracking.
- `BR-06` The system must provide human-readable care guidance based on risk output.
- `BR-07` If model artifacts are unavailable, the system must still provide risk assessment via fallback rules.

### 6.3 Care Coordination
- `BR-08` Patients must be able to request appointments; doctors must be able to accept/manage status.
- `BR-09` The platform must support patient-doctor in-app messaging with unread indicators.
- `BR-10` Doctors must be able to create structured reports for patients; patients must be notified.
- `BR-11` The platform must support medical record upload and authorized retrieval/deletion.

### 6.4 Alerts, Follow-up, and Escalation
- `BR-12` The system must generate notifications for critical care events (appointments, reports, symptom/SOS alerts).
- `BR-13` The system must support follow-up task creation (manual and auto-generated from high-risk signals).
- `BR-14` The system must provide SOS trigger capture with emergency contact and referral response payload.

### 6.5 Care Hub Monitoring
- `BR-15` The system must support symptom logging and severity-based alert scoring.
- `BR-16` The system must support medication reminder creation and adherence tracking.
- `BR-17` The system must support nutrition profile management and trend-based insight output.
- `BR-18` The system must support fetal kick count logging with low-movement alerts.
- `BR-19` The system must support lab result classification and trend analysis.
- `BR-20` The system must support explainability output for saved predictions.

### 6.6 Reporting and Operational Visibility
- `BR-21` The system must provide patient-level and doctor-level dashboards for ongoing monitoring.
- `BR-22` The system must provide API-accessible summaries for predictions, appointments, records, messages, reports, and notifications.
- `BR-23` The system must support history views for longitudinal review.

## 7. Functional Requirements (High-Level)

### 7.1 User and Session Management
- `FR-01` Register user accounts with unique username/email.
- `FR-02` Authenticate users and route by role.
- `FR-03` Persist authenticated sessions and enforce login-required routes.

### 7.2 Core Clinical Workflow
- `FR-04` Create and store prediction record from form input.
- `FR-05` Display prediction history and aggregated counts.
- `FR-06` Allow appointment create/read/update/cancel/accept lifecycle.
- `FR-07` Allow message send/read and unread summary.
- `FR-08` Allow doctor report creation and patient report retrieval.
- `FR-09` Allow record upload (multipart), metadata save, download, and delete.

### 7.3 Care Hub Workflow
- `FR-10` Symptom POST must compute alert score and level.
- `FR-11` Medication adherence logs must support taken/not-taken entries and adherence summaries.
- `FR-12` Nutrition insight must compute guidance from profile + logs.
- `FR-13` Kick count POST must return alert flag and advice.
- `FR-14` Lab result POST must classify status and interpretation.
- `FR-15` Auto follow-up endpoint must generate tasks from latest risk/symptom/lab records.
- `FR-16` Explainability endpoint must return factor-level summary and optionally persist report.
- `FR-17` SOS trigger endpoint must persist event and return contacts + referrals.

## 8. Non-Functional Requirements
- `NFR-01` Availability target: 99.0% monthly uptime for hosted deployment.
- `NFR-02` Performance target: 95% of standard read requests should complete within 2 seconds under normal load.
- `NFR-03` Security: Password hashing at rest, authenticated route protection, and role-based access controls.
- `NFR-04` Data integrity: Transactional writes for critical workflows (prediction, appointments, alerts, SOS, reports).
- `NFR-05` Usability: Responsive UI for desktop/mobile form factors.
- `NFR-06` Maintainability: Clear module separation between core app and addon services.
- `NFR-07` Observability: Error logging and event traceability for clinical workflows.
- `NFR-08` Backup and recovery: Scheduled backup strategy for persistent database and upload files.

## 9. Business Rules
- `RULE-01` Prediction inputs must be numeric for required fields.
- `RULE-02` Appointment statuses are constrained to `pending`, `confirmed`, `cancelled`, `completed`.
- `RULE-03` Only doctors/admins can create patient reports.
- `RULE-04` Access to patient-specific artifacts must follow role and ownership checks.
- `RULE-05` High/critical symptom and SOS events must trigger alert-type notifications.
- `RULE-06` Follow-up tasks can be generated automatically from high-risk signals.

## 10. Assumptions
- Users (patients/doctors) have basic internet/browser access.
- Clinicians will actively review alerts, follow-ups, and messages.
- ML model artifacts are periodically retrained/validated by project owners.
- Referral directories are curated and reviewed by operations stakeholders.

## 11. Constraints
- Current architecture is a monolithic Flask app with SQLite persistence.
- Session-based authentication is used (no federated identity in baseline).
- Baseline deployment is suitable for pilot/small-scale rollout; enterprise scaling needs follow-on work.
- Regulatory compliance hardening (audit-grade controls, formal data retention policy, encryption key governance) requires dedicated phase.

## 12. Dependencies
- Python/Flask runtime environment
- SQLAlchemy + database file availability
- Trained model and scaler artifacts for ML inference path
- File storage path for uploaded records
- Clinical/operations ownership of response workflows

## 13. Risks and Mitigations
- `RISK-01` False reassurance or alert fatigue from prediction/alerts.  
  `Mitigation:` Keep clinical review mandatory and include clear advisory language.
- `RISK-02` Unauthorized data exposure risk.  
  `Mitigation:` Enforce stricter authorization tests and periodic access audits.
- `RISK-03` Missed follow-up despite generated task.  
  `Mitigation:` Escalation reminders and unresolved-task monitoring.
- `RISK-04` Inaccurate referral/contact data in emergency flows.  
  `Mitigation:` Scheduled verification and source ownership.
- `RISK-05` Data loss in local DB/file storage failures.  
  `Mitigation:` Backup policy and recovery drills.

## 14. Success Metrics (KPIs)
- `KPI-01` % of active patients completing at least one weekly check-in (prediction or Care Hub entry).
- `KPI-02` Median time from high-risk alert to first clinician action.
- `KPI-03` Follow-up task completion rate within due date.
- `KPI-04` Appointment confirmation rate and no-show reduction.
- `KPI-05` Patient engagement rate in messaging and record updates.
- `KPI-06` SOS response acknowledgment time (operational process metric).

## 15. Acceptance Criteria for BRD Sign-Off
1. All stakeholder roles and business goals are represented and approved.
2. In-scope modules match implemented product capabilities.
3. Core and Care Hub requirements are uniquely identified and testable.
4. Non-functional targets and risk controls are documented and agreed.
5. KPI set is approved by product and clinical stakeholders.

## 16. Priority Roadmap (Business View)

### Must-Have (Baseline/Pilot)
- Role-based access and core workflows
- Risk prediction + history
- Appointments, messages, reports, records
- Notifications + critical alerting
- Care Hub symptom/lab/follow-up/SOS flows

### Should-Have (Next Release)
- Stronger authorization hardening and audit logging
- Database migrations and deployment automation
- Enhanced dashboard analytics and operational SLA tracking

### Could-Have (Future)
- Mobile app and push notifications
- External EHR/EMR integrations
- Multi-language support and advanced accessibility features

## 17. Traceability Snapshot (Business Requirement to Product Area)
- `BR-01` to `BR-03`: Auth, role controls, protected APIs
- `BR-04` to `BR-07`: Prediction module and history/statistics
- `BR-08` to `BR-11`: Appointments, messaging, reports, medical records
- `BR-12` to `BR-14`: Notifications, follow-ups, SOS emergency flow
- `BR-15` to `BR-20`: Care Hub modules
- `BR-21` to `BR-23`: Dashboards, history, APIs

---

This BRD defines the business baseline for PregnancyAI (MaternalGuard) and can be used for stakeholder review, sprint-level requirement breakdown, and test planning.
