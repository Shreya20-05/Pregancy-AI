import json
from datetime import datetime, timedelta

from addons.models import FollowUpTask


FEATURES = [
    "age",
    "bmi",
    "systolic_bp",
    "diastolic_bp",
    "blood_sugar",
    "body_temp",
    "heart_rate",
    "diabetes",
]

BASELINE = {
    "age": 28.0,
    "bmi": 24.0,
    "systolic_bp": 120.0,
    "diastolic_bp": 80.0,
    "blood_sugar": 95.0,
    "body_temp": 98.6,
    "heart_rate": 75.0,
    "diabetes": 0.0,
}

SCALE = {
    "age": 7.0,
    "bmi": 5.0,
    "systolic_bp": 20.0,
    "diastolic_bp": 12.0,
    "blood_sugar": 25.0,
    "body_temp": 1.5,
    "heart_rate": 15.0,
    "diabetes": 1.0,
}

DEFAULT_IMPORTANCE = {
    "age": 0.12,
    "bmi": 0.16,
    "systolic_bp": 0.2,
    "diastolic_bp": 0.12,
    "blood_sugar": 0.17,
    "body_temp": 0.06,
    "heart_rate": 0.09,
    "diabetes": 0.08,
}

LAB_THRESHOLDS = {
    "hemoglobin": {"low": 11.0, "critical_low": 7.0},
    "fasting_glucose": {"high": 95.0, "critical_high": 126.0, "low": 70.0},
    "postprandial_glucose": {"high": 140.0, "critical_high": 200.0},
    "systolic_bp": {"high": 140.0, "critical_high": 160.0, "low": 90.0},
    "diastolic_bp": {"high": 90.0, "critical_high": 110.0, "low": 60.0},
    "urine_protein": {"high": 30.0, "critical_high": 300.0},
}


def normalize_risk(value):
    raw = (value or "").strip().lower()
    if raw.startswith("h"):
        return "High"
    if raw.startswith("m"):
        return "Medium"
    if raw.startswith("l"):
        return "Low"
    return "Unknown"


def parse_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def clamp_int(value, min_value=0, max_value=3):
    try:
        casted = int(value)
    except (TypeError, ValueError):
        casted = min_value
    return max(min_value, min(max_value, casted))


def calculate_symptom_alert(payload):
    headache = clamp_int(payload.get("headache_severity"))
    swelling = clamp_int(payload.get("swelling_severity"))
    pain = clamp_int(payload.get("abdominal_pain_severity"))
    bleeding = parse_bool(payload.get("bleeding"))
    reduced_fetal_movement = parse_bool(payload.get("reduced_fetal_movement"))

    score = (headache * 2) + (swelling * 2) + (pain * 2)
    if bleeding:
        score += 8
    if reduced_fetal_movement:
        score += 6

    if score >= 14:
        level = "critical"
    elif score >= 9:
        level = "high"
    elif score >= 5:
        level = "medium"
    else:
        level = "low"

    advice = {
        "critical": "Immediate clinical review recommended.",
        "high": "Contact your doctor within 24 hours.",
        "medium": "Track symptoms closely and book follow-up if persistent.",
        "low": "Continue daily monitoring.",
    }[level]

    return {
        "headache_severity": headache,
        "swelling_severity": swelling,
        "abdominal_pain_severity": pain,
        "bleeding": bleeding,
        "reduced_fetal_movement": reduced_fetal_movement,
        "alert_score": score,
        "alert_level": level,
        "advice": advice,
    }


def _weekly_weight_gain_range(pre_preg_bmi):
    if pre_preg_bmi is None:
        return None
    if pre_preg_bmi < 18.5:
        return (0.44, 0.58)
    if pre_preg_bmi < 25:
        return (0.35, 0.50)
    if pre_preg_bmi < 30:
        return (0.23, 0.33)
    return (0.17, 0.27)


def nutrition_insight(profile, latest_log, previous_log=None):
    if profile is None or latest_log is None:
        return {
            "status": "insufficient_data",
            "message": "Profile and at least one nutrition log are required.",
        }

    if not profile.pre_pregnancy_weight_kg or not profile.height_cm:
        return {
            "status": "insufficient_data",
            "message": "Set pre-pregnancy weight and height in profile for weight guidance.",
        }

    height_m = profile.height_cm / 100.0
    if height_m <= 0:
        return {
            "status": "insufficient_data",
            "message": "Invalid profile height.",
        }

    pre_preg_bmi = profile.pre_pregnancy_weight_kg / (height_m * height_m)
    target_gain = _weekly_weight_gain_range(pre_preg_bmi)

    weight_delta = None
    if previous_log and previous_log.weight_kg is not None and latest_log.weight_kg is not None:
        days = max(1, (latest_log.logged_date - previous_log.logged_date).days)
        weekly_delta = (latest_log.weight_kg - previous_log.weight_kg) * (7.0 / days)
        weight_delta = weekly_delta
    else:
        weekly_delta = None

    if target_gain and weekly_delta is not None:
        low, high = target_gain
        if weekly_delta < low:
            trend = "below_target"
        elif weekly_delta > high:
            trend = "above_target"
        else:
            trend = "on_target"
    else:
        trend = "insufficient_data"

    return {
        "status": "ok",
        "pre_pregnancy_bmi": round(pre_preg_bmi, 2),
        "weekly_target_gain_kg": {
            "min": round(target_gain[0], 2) if target_gain else None,
            "max": round(target_gain[1], 2) if target_gain else None,
        },
        "weekly_observed_gain_kg": round(weight_delta, 2) if weight_delta is not None else None,
        "trend": trend,
    }


def evaluate_kick_count(kicks_count, duration_minutes):
    try:
        kicks = int(kicks_count)
    except (TypeError, ValueError):
        kicks = 0
    try:
        duration = int(duration_minutes)
    except (TypeError, ValueError):
        duration = 0

    alert = False
    note = "Within expected range."
    if duration >= 120 and kicks < 10:
        alert = True
        note = "Less than 10 movements in 2 hours. Seek clinical advice."
    elif duration >= 60 and kicks < 6:
        alert = True
        note = "Low movement count in 1 hour. Repeat count and contact doctor if persistent."

    return {"kicks_count": kicks, "duration_minutes": duration, "alert_flag": alert, "advice": note}


def classify_lab_result(test_name, value):
    test_key = (test_name or "").strip().lower().replace(" ", "_")
    try:
        reading = float(value)
    except (TypeError, ValueError):
        return ("normal", "Value accepted, no threshold configured for interpretation.")

    threshold = LAB_THRESHOLDS.get(test_key)
    if not threshold:
        return ("normal", "No specific threshold available for this test.")

    if "critical_high" in threshold and reading >= threshold["critical_high"]:
        return ("critical", "Critical high reading.")
    if "high" in threshold and reading >= threshold["high"]:
        return ("high", "Higher than recommended range.")
    if "critical_low" in threshold and reading <= threshold["critical_low"]:
        return ("critical", "Critical low reading.")
    if "low" in threshold and reading <= threshold["low"]:
        return ("low", "Lower than recommended range.")

    return ("normal", "Within configured range.")


def analyze_lab_trend(records):
    if not records:
        return {"trend": "insufficient_data", "delta": None}
    if len(records) == 1:
        return {"trend": "insufficient_data", "delta": 0.0}

    first = float(records[0].value)
    last = float(records[-1].value)
    delta = last - first

    base = abs(first) if first != 0 else 1.0
    pct = (delta / base) * 100.0

    if pct > 5:
        trend = "increasing"
    elif pct < -5:
        trend = "decreasing"
    else:
        trend = "stable"

    return {"trend": trend, "delta": round(delta, 3), "delta_percent": round(pct, 2)}


def _importance_from_model(model):
    if model is None or not hasattr(model, "feature_importances_"):
        return DEFAULT_IMPORTANCE
    raw = list(model.feature_importances_)
    if len(raw) != len(FEATURES):
        return DEFAULT_IMPORTANCE
    return {feature: float(raw[idx]) for idx, feature in enumerate(FEATURES)}


def explain_prediction(prediction, model=None):
    importance = _importance_from_model(model)

    values = {
        "age": float(prediction.age or 0.0),
        "bmi": float(prediction.bmi or 0.0),
        "systolic_bp": float(prediction.systolic_bp or 0.0),
        "diastolic_bp": float(prediction.diastolic_bp or 0.0),
        "blood_sugar": float(prediction.blood_sugar or 0.0),
        "body_temp": float(prediction.body_temp or 0.0),
        "heart_rate": float(prediction.heart_rate or 0.0),
        "diabetes": 1.0
        if str(prediction.diabetes or "").strip().lower() in {"1", "true", "yes", "y"}
        else 0.0,
    }

    contributions = []
    for feature in FEATURES:
        diff = values[feature] - BASELINE[feature]
        normalized = diff / SCALE[feature]
        weighted = normalized * importance[feature]
        contributions.append(
            {
                "feature": feature,
                "value": round(values[feature], 3),
                "baseline": BASELINE[feature],
                "importance": round(importance[feature], 4),
                "effect": round(weighted, 4),
                "direction": "upward_risk" if weighted > 0 else "downward_risk",
            }
        )

    contributions.sort(key=lambda item: abs(item["effect"]), reverse=True)
    top_factors = contributions[:3]

    risk = normalize_risk(prediction.risk_level)
    if risk == "High":
        summary = "Prediction is elevated mainly due to the top upward risk contributors."
    elif risk == "Low":
        summary = "Prediction is low because major contributors are near baseline."
    else:
        summary = "Prediction explanation generated with heuristic contribution scoring."

    return {
        "prediction_id": prediction.id,
        "risk_level": risk,
        "summary": summary,
        "top_factors": top_factors,
        "all_factors": contributions,
        "generated_at": datetime.utcnow().isoformat(),
    }


def serialize_explainability_payload(payload):
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


def create_followup_tasks_from_prediction(prediction):
    risk = normalize_risk(prediction.risk_level)
    if risk != "High":
        return []

    now = datetime.utcnow()
    return [
        FollowUpTask(
            user_id=prediction.user_id,
            related_prediction_id=prediction.id,
            source="risk_prediction",
            title="Urgent obstetric review",
            description="Schedule consultation to review elevated risk indicators.",
            priority="high",
            due_date=now + timedelta(days=1),
        ),
        FollowUpTask(
            user_id=prediction.user_id,
            related_prediction_id=prediction.id,
            source="risk_prediction",
            title="Repeat vitals and glucose check",
            description="Repeat BP, blood sugar, and symptom check.",
            priority="high",
            due_date=now + timedelta(days=2),
        ),
    ]


def create_followup_task_from_symptom(user_id, alert_level):
    if alert_level not in {"high", "critical"}:
        return None

    now = datetime.utcnow()
    return FollowUpTask(
        user_id=user_id,
        source="symptom",
        title="Symptom escalation follow-up",
        description="High symptom alert detected. Clinical review recommended.",
        priority="critical" if alert_level == "critical" else "high",
        due_date=now + timedelta(hours=6 if alert_level == "critical" else 24),
    )


def create_followup_task_from_lab(user_id, test_name, status):
    if status not in {"high", "critical", "low"}:
        return None

    return FollowUpTask(
        user_id=user_id,
        source="lab",
        title=f"Review lab result: {test_name}",
        description=f"Lab result flagged as {status}. Repeat or review with clinician.",
        priority="critical" if status == "critical" else "medium",
        due_date=datetime.utcnow() + timedelta(days=1),
    )

