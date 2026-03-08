import json
from datetime import datetime, date

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from addons.models import (
    EmergencyContact,
    ExplainabilityReport,
    FollowUpTask,
    KickCountSession,
    LabResult,
    MedicationAdherence,
    MedicationReminder,
    NutritionLog,
    PregnancyProfile,
    SOSEvent,
    SymptomEntry,
)
from addons.referrals import REFERRAL_DIRECTORY
from addons.services import (
    analyze_lab_trend,
    calculate_symptom_alert,
    classify_lab_result,
    create_followup_task_from_lab,
    create_followup_task_from_symptom,
    create_followup_tasks_from_prediction,
    evaluate_kick_count,
    explain_prediction,
    nutrition_insight,
    parse_bool,
    serialize_explainability_payload,
)
from models import Notification, Prediction, User, db

addon_bp = Blueprint("addons", __name__, url_prefix="/api/addons")


def _is_doctor(user):
    return user.role in ("doctor", "admin")


def _get_loaded_model():
    return current_app.config.get("ML_MODEL")


def _parse_date(value):
    if value in (None, ""):
        return None
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError:
        try:
            return datetime.strptime(str(value), "%Y-%m-%d").date()
        except ValueError:
            return None


def _parse_datetime(value):
    if value in (None, ""):
        return None
    try:
        clean = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(clean)
    except ValueError:
        return None


def _target_user_id_from_payload(payload):
    if _is_doctor(current_user):
        raw = payload.get("user_id", current_user.id)
    else:
        raw = current_user.id

    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _user_scope_from_query():
    if _is_doctor(current_user):
        raw = request.args.get("user_id")
        if raw is None:
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return current_user.id
    return current_user.id


def _serialize_symptom(entry):
    return {
        "id": entry.id,
        "user_id": entry.user_id,
        "recorded_at": entry.recorded_at.isoformat() if entry.recorded_at else None,
        "headache_severity": entry.headache_severity,
        "swelling_severity": entry.swelling_severity,
        "abdominal_pain_severity": entry.abdominal_pain_severity,
        "bleeding": bool(entry.bleeding),
        "reduced_fetal_movement": bool(entry.reduced_fetal_movement),
        "notes": entry.notes,
        "alert_score": entry.alert_score,
        "alert_level": entry.alert_level,
    }


def _serialize_medication(reminder):
    times = []
    if reminder.times_csv:
        times = [item.strip() for item in reminder.times_csv.split(",") if item.strip()]
    return {
        "id": reminder.id,
        "user_id": reminder.user_id,
        "medication_name": reminder.medication_name,
        "dosage": reminder.dosage,
        "instructions": reminder.instructions,
        "times": times,
        "start_date": reminder.start_date.isoformat() if reminder.start_date else None,
        "end_date": reminder.end_date.isoformat() if reminder.end_date else None,
        "status": reminder.status,
        "created_at": reminder.created_at.isoformat() if reminder.created_at else None,
    }


def _serialize_adherence(log):
    return {
        "id": log.id,
        "reminder_id": log.reminder_id,
        "scheduled_for": log.scheduled_for.isoformat() if log.scheduled_for else None,
        "taken_at": log.taken_at.isoformat() if log.taken_at else None,
        "was_taken": bool(log.was_taken),
        "notes": log.notes,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


def _serialize_profile(profile):
    if profile is None:
        return None
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "pre_pregnancy_weight_kg": profile.pre_pregnancy_weight_kg,
        "height_cm": profile.height_cm,
        "gestational_week": profile.gestational_week,
        "due_date": profile.due_date.isoformat() if profile.due_date else None,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }


def _serialize_nutrition_log(log):
    return {
        "id": log.id,
        "user_id": log.user_id,
        "logged_date": log.logged_date.isoformat() if log.logged_date else None,
        "weight_kg": log.weight_kg,
        "calories_kcal": log.calories_kcal,
        "protein_g": log.protein_g,
        "water_liters": log.water_liters,
        "notes": log.notes,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


def _serialize_kick_session(session):
    return {
        "id": session.id,
        "user_id": session.user_id,
        "session_start": session.session_start.isoformat() if session.session_start else None,
        "session_end": session.session_end.isoformat() if session.session_end else None,
        "kicks_count": session.kicks_count,
        "duration_minutes": session.duration_minutes,
        "alert_flag": bool(session.alert_flag),
        "notes": session.notes,
        "created_at": session.created_at.isoformat() if session.created_at else None,
    }


def _serialize_lab(result):
    return {
        "id": result.id,
        "user_id": result.user_id,
        "test_name": result.test_name,
        "value": result.value,
        "unit": result.unit,
        "recorded_at": result.recorded_at.isoformat() if result.recorded_at else None,
        "status": result.status,
        "interpretation": result.interpretation,
        "notes": result.notes,
        "created_at": result.created_at.isoformat() if result.created_at else None,
    }


def _serialize_followup(task):
    return {
        "id": task.id,
        "user_id": task.user_id,
        "related_prediction_id": task.related_prediction_id,
        "source": task.source,
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "status": task.status,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


def _serialize_contact(contact):
    return {
        "id": contact.id,
        "user_id": contact.user_id,
        "name": contact.name,
        "relation": contact.relation,
        "phone": contact.phone,
        "is_primary": bool(contact.is_primary),
        "created_at": contact.created_at.isoformat() if contact.created_at else None,
    }


def _serialize_sos_event(event):
    return {
        "id": event.id,
        "user_id": event.user_id,
        "message": event.message,
        "location": event.location,
        "status": event.status,
        "triggered_at": event.triggered_at.isoformat() if event.triggered_at else None,
    }


@addon_bp.route("/meta")
@login_required
def addon_meta():
    return jsonify(
        {
            "modules": [
                "symptom_tracker",
                "medication_reminders",
                "nutrition_tracker",
                "kick_count_monitor",
                "lab_trend_analyzer",
                "high_risk_followup_workflow",
                "explainable_ai_reports",
                "emergency_sos_referral",
            ]
        }
    )


@addon_bp.route("/symptoms", methods=["GET", "POST"])
@login_required
def addon_symptoms():
    if request.method == "GET":
        target_user_id = _user_scope_from_query()
        query = SymptomEntry.query.order_by(SymptomEntry.recorded_at.desc())
        if target_user_id is not None:
            query = query.filter_by(user_id=target_user_id)
        return jsonify([_serialize_symptom(item) for item in query.limit(200).all()])

    payload = request.get_json(silent=True) or {}
    target_user_id = _target_user_id_from_payload(payload)
    if target_user_id is None:
        return jsonify({"error": "Invalid user_id"}), 400

    user = db.session.get(User, target_user_id)
    if user is None:
        return jsonify({"error": "User not found"}), 404

    evaluated = calculate_symptom_alert(payload)
    entry = SymptomEntry(
        user_id=target_user_id,
        recorded_at=_parse_datetime(payload.get("recorded_at")) or datetime.utcnow(),
        headache_severity=evaluated["headache_severity"],
        swelling_severity=evaluated["swelling_severity"],
        abdominal_pain_severity=evaluated["abdominal_pain_severity"],
        bleeding=evaluated["bleeding"],
        reduced_fetal_movement=evaluated["reduced_fetal_movement"],
        notes=(payload.get("notes") or "").strip(),
        alert_score=evaluated["alert_score"],
        alert_level=evaluated["alert_level"],
    )
    db.session.add(entry)

    task = create_followup_task_from_symptom(target_user_id, evaluated["alert_level"])
    if task is not None:
        db.session.add(task)

    if evaluated["alert_level"] in {"high", "critical"}:
        db.session.add(
            Notification(
                user_id=target_user_id,
                title="Symptom Alert",
                message=f"Symptom alert level: {evaluated['alert_level']}. {evaluated['advice']}",
                notification_type="alert",
            )
        )

    db.session.commit()

    return jsonify({"success": True, "entry": _serialize_symptom(entry), "advice": evaluated["advice"]}), 201


@addon_bp.route("/medications", methods=["GET", "POST"])
@login_required
def addon_medications():
    if request.method == "GET":
        target_user_id = _user_scope_from_query()
        query = MedicationReminder.query.order_by(MedicationReminder.created_at.desc())
        if target_user_id is not None:
            query = query.filter_by(user_id=target_user_id)
        return jsonify([_serialize_medication(reminder) for reminder in query.limit(200).all()])

    payload = request.get_json(silent=True) or {}
    target_user_id = _target_user_id_from_payload(payload)
    if target_user_id is None:
        return jsonify({"error": "Invalid user_id"}), 400

    medication_name = (payload.get("medication_name") or "").strip()
    if not medication_name:
        return jsonify({"error": "medication_name is required"}), 400

    times = payload.get("times")
    if isinstance(times, list):
        times_csv = ",".join([str(item).strip() for item in times if str(item).strip()])
    else:
        times_csv = str(payload.get("times_csv") or "").strip()

    reminder = MedicationReminder(
        user_id=target_user_id,
        medication_name=medication_name,
        dosage=(payload.get("dosage") or "").strip(),
        instructions=(payload.get("instructions") or "").strip(),
        times_csv=times_csv,
        start_date=_parse_date(payload.get("start_date")) or date.today(),
        end_date=_parse_date(payload.get("end_date")),
        status=(payload.get("status") or "active").strip().lower(),
    )
    db.session.add(reminder)
    db.session.commit()
    return jsonify({"success": True, "reminder": _serialize_medication(reminder)}), 201


@addon_bp.route("/medications/<int:reminder_id>/adherence", methods=["GET", "POST"])
@login_required
def addon_medication_adherence(reminder_id):
    reminder = MedicationReminder.query.get_or_404(reminder_id)
    if not (_is_doctor(current_user) or reminder.user_id == current_user.id):
        return jsonify({"error": "Forbidden"}), 403

    if request.method == "GET":
        logs = (
            MedicationAdherence.query.filter_by(reminder_id=reminder_id)
            .order_by(MedicationAdherence.created_at.desc())
            .all()
        )
        return jsonify([_serialize_adherence(log) for log in logs])

    payload = request.get_json(silent=True) or {}
    was_taken = parse_bool(payload.get("was_taken", True))
    scheduled_for = _parse_datetime(payload.get("scheduled_for"))

    adherence = MedicationAdherence(
        reminder_id=reminder_id,
        scheduled_for=scheduled_for,
        taken_at=datetime.utcnow() if was_taken else None,
        was_taken=was_taken,
        notes=(payload.get("notes") or "").strip(),
    )
    db.session.add(adherence)
    db.session.commit()
    return jsonify({"success": True, "adherence": _serialize_adherence(adherence)}), 201


@addon_bp.route("/medications/<int:reminder_id>/summary")
@login_required
def addon_medication_summary(reminder_id):
    reminder = MedicationReminder.query.get_or_404(reminder_id)
    if not (_is_doctor(current_user) or reminder.user_id == current_user.id):
        return jsonify({"error": "Forbidden"}), 403

    logs = MedicationAdherence.query.filter_by(reminder_id=reminder_id).all()
    total = len(logs)
    taken = sum(1 for log in logs if log.was_taken)
    adherence_rate = round((taken / total) * 100.0, 2) if total else None

    return jsonify(
        {
            "reminder": _serialize_medication(reminder),
            "total_logs": total,
            "taken_logs": taken,
            "adherence_rate": adherence_rate,
        }
    )


@addon_bp.route("/nutrition/profile", methods=["GET", "PUT"])
@login_required
def addon_nutrition_profile():
    if request.method == "GET":
        target_user_id = _user_scope_from_query() or current_user.id
        profile = PregnancyProfile.query.filter_by(user_id=target_user_id).first()
        return jsonify(_serialize_profile(profile))

    payload = request.get_json(silent=True) or {}
    target_user_id = _target_user_id_from_payload(payload)
    if target_user_id is None:
        return jsonify({"error": "Invalid user_id"}), 400

    profile = PregnancyProfile.query.filter_by(user_id=target_user_id).first()
    if profile is None:
        profile = PregnancyProfile(user_id=target_user_id)
        db.session.add(profile)

    if "pre_pregnancy_weight_kg" in payload:
        profile.pre_pregnancy_weight_kg = payload.get("pre_pregnancy_weight_kg")
    if "height_cm" in payload:
        profile.height_cm = payload.get("height_cm")
    if "gestational_week" in payload:
        profile.gestational_week = payload.get("gestational_week")
    if "due_date" in payload:
        profile.due_date = _parse_date(payload.get("due_date"))

    db.session.commit()
    return jsonify({"success": True, "profile": _serialize_profile(profile)})


@addon_bp.route("/nutrition/logs", methods=["GET", "POST"])
@login_required
def addon_nutrition_logs():
    if request.method == "GET":
        target_user_id = _user_scope_from_query() or current_user.id
        logs = (
            NutritionLog.query.filter_by(user_id=target_user_id)
            .order_by(NutritionLog.logged_date.desc())
            .limit(200)
            .all()
        )
        return jsonify([_serialize_nutrition_log(log) for log in logs])

    payload = request.get_json(silent=True) or {}
    target_user_id = _target_user_id_from_payload(payload)
    if target_user_id is None:
        return jsonify({"error": "Invalid user_id"}), 400

    log = NutritionLog(
        user_id=target_user_id,
        logged_date=_parse_date(payload.get("logged_date")) or date.today(),
        weight_kg=payload.get("weight_kg"),
        calories_kcal=payload.get("calories_kcal"),
        protein_g=payload.get("protein_g"),
        water_liters=payload.get("water_liters"),
        notes=(payload.get("notes") or "").strip(),
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({"success": True, "log": _serialize_nutrition_log(log)}), 201


@addon_bp.route("/nutrition/insights")
@login_required
def addon_nutrition_insights():
    target_user_id = _user_scope_from_query() or current_user.id
    profile = PregnancyProfile.query.filter_by(user_id=target_user_id).first()
    logs = (
        NutritionLog.query.filter_by(user_id=target_user_id)
        .order_by(NutritionLog.logged_date.desc())
        .limit(2)
        .all()
    )
    latest = logs[0] if len(logs) >= 1 else None
    previous = logs[1] if len(logs) >= 2 else None
    return jsonify(nutrition_insight(profile, latest, previous))


@addon_bp.route("/kick-count", methods=["GET", "POST"])
@login_required
def addon_kick_count():
    if request.method == "GET":
        target_user_id = _user_scope_from_query() or current_user.id
        sessions = (
            KickCountSession.query.filter_by(user_id=target_user_id)
            .order_by(KickCountSession.session_start.desc())
            .limit(200)
            .all()
        )
        return jsonify([_serialize_kick_session(session) for session in sessions])

    payload = request.get_json(silent=True) or {}
    target_user_id = _target_user_id_from_payload(payload)
    if target_user_id is None:
        return jsonify({"error": "Invalid user_id"}), 400

    session_start = _parse_datetime(payload.get("session_start")) or datetime.utcnow()
    session_end = _parse_datetime(payload.get("session_end")) or datetime.utcnow()
    duration = int(max(0, (session_end - session_start).total_seconds() // 60))
    provided_duration = payload.get("duration_minutes")
    if provided_duration is not None:
        try:
            duration = int(provided_duration)
        except (TypeError, ValueError):
            pass

    evaluation = evaluate_kick_count(payload.get("kicks_count"), duration)
    session = KickCountSession(
        user_id=target_user_id,
        session_start=session_start,
        session_end=session_end,
        kicks_count=evaluation["kicks_count"],
        duration_minutes=evaluation["duration_minutes"],
        alert_flag=evaluation["alert_flag"],
        notes=(payload.get("notes") or "").strip(),
    )
    db.session.add(session)

    if evaluation["alert_flag"]:
        task = create_followup_task_from_symptom(target_user_id, "high")
        if task is not None:
            task.title = "Reduced fetal movement follow-up"
            db.session.add(task)

    db.session.commit()
    return jsonify({"success": True, "session": _serialize_kick_session(session), "advice": evaluation["advice"]}), 201


@addon_bp.route("/labs/results", methods=["GET", "POST"])
@login_required
def addon_lab_results():
    if request.method == "GET":
        target_user_id = _user_scope_from_query() or current_user.id
        test_name = request.args.get("test_name")
        query = LabResult.query.filter_by(user_id=target_user_id).order_by(LabResult.recorded_at.asc())
        if test_name:
            query = query.filter(LabResult.test_name.ilike(test_name))
        return jsonify([_serialize_lab(result) for result in query.limit(500).all()])

    payload = request.get_json(silent=True) or {}
    target_user_id = _target_user_id_from_payload(payload)
    if target_user_id is None:
        return jsonify({"error": "Invalid user_id"}), 400

    test_name = (payload.get("test_name") or "").strip()
    if not test_name:
        return jsonify({"error": "test_name is required"}), 400

    try:
        value = float(payload.get("value"))
    except (TypeError, ValueError):
        return jsonify({"error": "value must be numeric"}), 400

    status, interpretation = classify_lab_result(test_name, value)
    result = LabResult(
        user_id=target_user_id,
        test_name=test_name,
        value=value,
        unit=(payload.get("unit") or "").strip(),
        recorded_at=_parse_datetime(payload.get("recorded_at")) or datetime.utcnow(),
        status=status,
        interpretation=interpretation,
        notes=(payload.get("notes") or "").strip(),
    )
    db.session.add(result)

    task = create_followup_task_from_lab(target_user_id, test_name, status)
    if task is not None:
        db.session.add(task)

    db.session.commit()
    return jsonify({"success": True, "result": _serialize_lab(result)}), 201


@addon_bp.route("/labs/trends")
@login_required
def addon_lab_trends():
    target_user_id = _user_scope_from_query() or current_user.id
    test_name = request.args.get("test_name")

    if test_name:
        records = (
            LabResult.query.filter_by(user_id=target_user_id, test_name=test_name)
            .order_by(LabResult.recorded_at.asc())
            .all()
        )
        return jsonify({"test_name": test_name, "analysis": analyze_lab_trend(records), "count": len(records)})

    grouped = {}
    records = (
        LabResult.query.filter_by(user_id=target_user_id)
        .order_by(LabResult.test_name.asc(), LabResult.recorded_at.asc())
        .all()
    )
    for record in records:
        grouped.setdefault(record.test_name, []).append(record)

    return jsonify(
        {
            key: {"analysis": analyze_lab_trend(value), "count": len(value)}
            for key, value in grouped.items()
        }
    )


@addon_bp.route("/followups", methods=["GET", "POST"])
@login_required
def addon_followups():
    if request.method == "GET":
        target_user_id = _user_scope_from_query() or current_user.id
        query = FollowUpTask.query.order_by(FollowUpTask.created_at.desc())
        if target_user_id is not None:
            query = query.filter_by(user_id=target_user_id)
        return jsonify([_serialize_followup(task) for task in query.limit(300).all()])

    payload = request.get_json(silent=True) or {}
    target_user_id = _target_user_id_from_payload(payload)
    if target_user_id is None:
        return jsonify({"error": "Invalid user_id"}), 400

    title = (payload.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    task = FollowUpTask(
        user_id=target_user_id,
        related_prediction_id=payload.get("related_prediction_id"),
        source=(payload.get("source") or "manual").strip(),
        title=title,
        description=(payload.get("description") or "").strip(),
        priority=(payload.get("priority") or "medium").strip().lower(),
        status=(payload.get("status") or "pending").strip().lower(),
        due_date=_parse_datetime(payload.get("due_date")),
    )
    db.session.add(task)
    db.session.commit()
    return jsonify({"success": True, "task": _serialize_followup(task)}), 201


@addon_bp.route("/followups/<int:task_id>", methods=["PUT"])
@login_required
def addon_update_followup(task_id):
    task = FollowUpTask.query.get_or_404(task_id)
    if not (_is_doctor(current_user) or task.user_id == current_user.id):
        return jsonify({"error": "Forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    if "title" in payload:
        task.title = (payload.get("title") or "").strip()
    if "description" in payload:
        task.description = (payload.get("description") or "").strip()
    if "priority" in payload:
        task.priority = (payload.get("priority") or "").strip().lower()
    if "status" in payload:
        task.status = (payload.get("status") or "").strip().lower()
    if "due_date" in payload:
        task.due_date = _parse_datetime(payload.get("due_date"))
    if task.status == "completed":
        task.completed_at = datetime.utcnow()

    db.session.commit()
    return jsonify({"success": True, "task": _serialize_followup(task)})


@addon_bp.route("/followups/auto-from-latest", methods=["POST"])
@login_required
def addon_auto_followups():
    payload = request.get_json(silent=True) or {}
    target_user_id = _target_user_id_from_payload(payload)
    if target_user_id is None:
        return jsonify({"error": "Invalid user_id"}), 400

    created = []
    latest_prediction = (
        Prediction.query.filter_by(user_id=target_user_id).order_by(Prediction.created_at.desc()).first()
    )
    if latest_prediction is not None:
        created.extend(create_followup_tasks_from_prediction(latest_prediction))

    latest_symptom = (
        SymptomEntry.query.filter_by(user_id=target_user_id).order_by(SymptomEntry.recorded_at.desc()).first()
    )
    if latest_symptom is not None:
        symptom_task = create_followup_task_from_symptom(target_user_id, latest_symptom.alert_level)
        if symptom_task is not None:
            created.append(symptom_task)

    latest_lab = LabResult.query.filter_by(user_id=target_user_id).order_by(LabResult.recorded_at.desc()).first()
    if latest_lab is not None:
        lab_task = create_followup_task_from_lab(target_user_id, latest_lab.test_name, latest_lab.status)
        if lab_task is not None:
            created.append(lab_task)

    for task in created:
        db.session.add(task)
    db.session.commit()

    return jsonify({"success": True, "created_count": len(created), "tasks": [_serialize_followup(t) for t in created]})


@addon_bp.route("/explainability/<int:prediction_id>")
@login_required
def addon_explainability(prediction_id):
    prediction = Prediction.query.get_or_404(prediction_id)
    if not (_is_doctor(current_user) or prediction.user_id == current_user.id):
        return jsonify({"error": "Forbidden"}), 403

    payload = explain_prediction(prediction, _get_loaded_model())
    save = parse_bool(request.args.get("save"))
    if save:
        report = ExplainabilityReport(
            user_id=prediction.user_id,
            prediction_id=prediction.id,
            summary_json=serialize_explainability_payload(payload),
        )
        db.session.add(report)
        db.session.commit()
        payload["report_id"] = report.id

    return jsonify(payload)


@addon_bp.route("/explainability/reports")
@login_required
def addon_explainability_reports():
    target_user_id = _user_scope_from_query() or current_user.id
    query = ExplainabilityReport.query.order_by(ExplainabilityReport.created_at.desc())
    if target_user_id is not None:
        query = query.filter_by(user_id=target_user_id)

    results = []
    for item in query.limit(200).all():
        try:
            parsed = json.loads(item.summary_json)
        except json.JSONDecodeError:
            parsed = None
        results.append(
            {
                "id": item.id,
                "user_id": item.user_id,
                "prediction_id": item.prediction_id,
                "summary": parsed,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
        )
    return jsonify(results)


@addon_bp.route("/sos/contacts", methods=["GET", "POST"])
@login_required
def addon_sos_contacts():
    if request.method == "GET":
        target_user_id = _user_scope_from_query() or current_user.id
        contacts = EmergencyContact.query.filter_by(user_id=target_user_id).order_by(EmergencyContact.created_at.desc()).all()
        return jsonify([_serialize_contact(contact) for contact in contacts])

    payload = request.get_json(silent=True) or {}
    target_user_id = _target_user_id_from_payload(payload)
    if target_user_id is None:
        return jsonify({"error": "Invalid user_id"}), 400

    name = (payload.get("name") or "").strip()
    phone = (payload.get("phone") or "").strip()
    if not name or not phone:
        return jsonify({"error": "name and phone are required"}), 400

    is_primary = parse_bool(payload.get("is_primary", False))
    if is_primary:
        EmergencyContact.query.filter_by(user_id=target_user_id, is_primary=True).update({"is_primary": False})

    contact = EmergencyContact(
        user_id=target_user_id,
        name=name,
        relation=(payload.get("relation") or "").strip(),
        phone=phone,
        is_primary=is_primary,
    )
    db.session.add(contact)
    db.session.commit()
    return jsonify({"success": True, "contact": _serialize_contact(contact)}), 201


@addon_bp.route("/sos/contacts/<int:contact_id>", methods=["DELETE"])
@login_required
def addon_delete_sos_contact(contact_id):
    contact = EmergencyContact.query.get_or_404(contact_id)
    if not (_is_doctor(current_user) or contact.user_id == current_user.id):
        return jsonify({"error": "Forbidden"}), 403

    db.session.delete(contact)
    db.session.commit()
    return jsonify({"success": True})


@addon_bp.route("/sos/trigger", methods=["POST"])
@login_required
def addon_trigger_sos():
    payload = request.get_json(silent=True) or {}
    target_user_id = _target_user_id_from_payload(payload)
    if target_user_id is None:
        return jsonify({"error": "Invalid user_id"}), 400

    event = SOSEvent(
        user_id=target_user_id,
        message=(payload.get("message") or "Emergency support required.").strip(),
        location=(payload.get("location") or "").strip(),
        status="triggered",
    )
    db.session.add(event)

    db.session.add(
        Notification(
            user_id=target_user_id,
            title="Emergency SOS Triggered",
            message="SOS event has been recorded. Contact emergency services immediately.",
            notification_type="alert",
        )
    )

    contacts = EmergencyContact.query.filter_by(user_id=target_user_id).all()
    city_filter = (payload.get("city") or "").strip().lower()
    state_filter = (payload.get("state") or "").strip().lower()

    referrals = []
    for item in REFERRAL_DIRECTORY:
        city_ok = not city_filter or item["city"].strip().lower() == city_filter
        state_ok = not state_filter or item["state"].strip().lower() == state_filter
        if city_ok and state_ok:
            referrals.append(item)
    if not referrals:
        referrals = REFERRAL_DIRECTORY[:3]

    db.session.commit()
    return jsonify(
        {
            "success": True,
            "event": _serialize_sos_event(event),
            "contacts": [_serialize_contact(contact) for contact in contacts],
            "referrals": referrals,
            "recommended_action": "Call local emergency services and notify your doctor immediately.",
        }
    ), 201


@addon_bp.route("/sos/events")
@login_required
def addon_sos_events():
    target_user_id = _user_scope_from_query() or current_user.id
    events = SOSEvent.query.filter_by(user_id=target_user_id).order_by(SOSEvent.triggered_at.desc()).limit(200).all()
    return jsonify([_serialize_sos_event(event) for event in events])


@addon_bp.route("/sos/referrals")
@login_required
def addon_sos_referrals():
    city_filter = (request.args.get("city") or "").strip().lower()
    state_filter = (request.args.get("state") or "").strip().lower()

    filtered = []
    for item in REFERRAL_DIRECTORY:
        city_ok = not city_filter or item["city"].strip().lower() == city_filter
        state_ok = not state_filter or item["state"].strip().lower() == state_filter
        if city_ok and state_ok:
            filtered.append(item)

    return jsonify(filtered if filtered else REFERRAL_DIRECTORY[:5])
