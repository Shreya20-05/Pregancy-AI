from datetime import datetime, date

from models import db


class SymptomEntry(db.Model):
    __tablename__ = "addon_symptom_entries"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    headache_severity = db.Column(db.Integer, default=0)
    swelling_severity = db.Column(db.Integer, default=0)
    abdominal_pain_severity = db.Column(db.Integer, default=0)
    bleeding = db.Column(db.Boolean, default=False)
    reduced_fetal_movement = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)

    alert_score = db.Column(db.Integer, default=0)
    alert_level = db.Column(db.String(20), default="low")


class MedicationReminder(db.Model):
    __tablename__ = "addon_medication_reminders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    medication_name = db.Column(db.String(120), nullable=False)
    dosage = db.Column(db.String(80))
    instructions = db.Column(db.Text)
    times_csv = db.Column(db.String(255))  # HH:MM,HH:MM
    start_date = db.Column(db.Date, default=date.today)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(20), default="active")  # active/inactive
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MedicationAdherence(db.Model):
    __tablename__ = "addon_medication_adherence"

    id = db.Column(db.Integer, primary_key=True)
    reminder_id = db.Column(
        db.Integer,
        db.ForeignKey("addon_medication_reminders.id"),
        nullable=False,
        index=True,
    )
    scheduled_for = db.Column(db.DateTime)
    taken_at = db.Column(db.DateTime)
    was_taken = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PregnancyProfile(db.Model):
    __tablename__ = "addon_pregnancy_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True, index=True)
    pre_pregnancy_weight_kg = db.Column(db.Float)
    height_cm = db.Column(db.Float)
    gestational_week = db.Column(db.Integer)
    due_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NutritionLog(db.Model):
    __tablename__ = "addon_nutrition_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    logged_date = db.Column(db.Date, default=date.today, index=True)
    weight_kg = db.Column(db.Float)
    calories_kcal = db.Column(db.Float)
    protein_g = db.Column(db.Float)
    water_liters = db.Column(db.Float)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class KickCountSession(db.Model):
    __tablename__ = "addon_kick_count_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    session_start = db.Column(db.DateTime, nullable=False)
    session_end = db.Column(db.DateTime, nullable=False)
    kicks_count = db.Column(db.Integer, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    alert_flag = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class LabResult(db.Model):
    __tablename__ = "addon_lab_results"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    test_name = db.Column(db.String(120), nullable=False, index=True)
    value = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(30))
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    status = db.Column(db.String(20), default="normal")  # low/normal/high/critical
    interpretation = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class FollowUpTask(db.Model):
    __tablename__ = "addon_followup_tasks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    related_prediction_id = db.Column(db.Integer, db.ForeignKey("predictions.id"))
    source = db.Column(db.String(30), default="manual")
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    priority = db.Column(db.String(20), default="medium")  # low/medium/high/critical
    status = db.Column(db.String(20), default="pending")  # pending/completed/overdue
    due_date = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ExplainabilityReport(db.Model):
    __tablename__ = "addon_explainability_reports"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    prediction_id = db.Column(db.Integer, db.ForeignKey("predictions.id"), nullable=False, index=True)
    summary_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class EmergencyContact(db.Model):
    __tablename__ = "addon_emergency_contacts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    relation = db.Column(db.String(50))
    phone = db.Column(db.String(30), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SOSEvent(db.Model):
    __tablename__ = "addon_sos_events"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    message = db.Column(db.Text)
    location = db.Column(db.String(255))
    status = db.Column(db.String(30), default="triggered")
    triggered_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

