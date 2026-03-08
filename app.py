from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, User, Prediction, Appointment, MedicalRecord, Message, Notification, Report
from datetime import datetime, timedelta
from sqlalchemy import func
import os
import pickle
import numpy as np

try:
    from addons.models import (
        SymptomEntry,
        MedicationReminder,
        MedicationAdherence,
        LabResult,
        FollowUpTask,
        SOSEvent,
    )
    ADDONS_AVAILABLE = True
except Exception:
    SymptomEntry = None
    MedicationReminder = None
    MedicationAdherence = None
    LabResult = None
    FollowUpTask = None
    SOSEvent = None
    ADDONS_AVAILABLE = False

app = Flask(__name__)

# --- Configuration ---
app.config['SECRET_KEY'] = 'maternal-guard-secret-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///maternalguard.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- Load ML Model ---
model = None
scaler = None
try:
    model_path = os.path.join(app.root_path, 'pregnancy_risk_model.pkl')
    scaler_path = os.path.join(app.root_path, 'scaler.pkl')
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    with open(scaler_path, 'rb') as f:
        scaler = pickle.load(f)
    print('ML model and scaler loaded')
except Exception as e:
    print(f'Warning: ML artifacts not loaded. Falling back to rule-based prediction. Error: {e}')

# Expose ML artifacts for addon modules without importing app.py from addons (avoids circular import).
app.config['ML_MODEL'] = model
app.config['ML_SCALER'] = scaler


RISK_ADVICE = {
    'High': 'Please consult your doctor as soon as possible for a detailed evaluation.',
    'Medium': 'Maintain regular checkups and monitor your health metrics closely.',
    'Low': 'Keep up healthy habits and continue with scheduled prenatal checkups.'
}


def is_doctor(user):
    return user.role in ('doctor', 'admin')


def normalize_risk(value):
    raw = (value or '').strip().lower()
    if raw.startswith('h'):
        return 'High'
    if raw.startswith('m'):
        return 'Medium'
    if raw.startswith('l'):
        return 'Low'
    return 'Unknown'


def parse_iso_datetime(value):
    if value in (None, ''):
        return None
    try:
        clean_value = str(value).replace('Z', '+00:00')
        return datetime.fromisoformat(clean_value)
    except ValueError:
        return None


def parse_iso_date(value):
    if value in (None, ''):
        return None
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError:
        try:
            return datetime.strptime(str(value), '%Y-%m-%d').date()
        except ValueError:
            return None


def can_access_user_data(target_user_id):
    return is_doctor(current_user) or current_user.id == target_user_id


def serialize_prediction(pred):
    risk_title = normalize_risk(pred.risk_level)
    risk_lower = risk_title.lower() if risk_title != 'Unknown' else 'unknown'

    diabetes_value = pred.diabetes
    if isinstance(diabetes_value, str):
        diabetes_flag = 1 if diabetes_value.strip().lower() in ('1', 'true', 'yes', 'y') else 0
    else:
        diabetes_flag = int(bool(diabetes_value)) if diabetes_value is not None else 0

    return {
        'id': pred.id,
        'user_id': pred.user_id,
        'user_name': pred.user_name or (pred.user.username if pred.user else None),
        'age': pred.age if pred.age is not None else 0,
        'bmi': float(pred.bmi) if pred.bmi is not None else 0.0,
        'systolic_bp': pred.systolic_bp if pred.systolic_bp is not None else 0,
        'diastolic_bp': pred.diastolic_bp if pred.diastolic_bp is not None else 0,
        'blood_sugar': float(pred.blood_sugar) if pred.blood_sugar is not None else 0.0,
        'body_temp': float(pred.body_temp) if pred.body_temp is not None else 0.0,
        'heart_rate': pred.heart_rate if pred.heart_rate is not None else 0,
        'diabetes': diabetes_flag,
        'risk_level': risk_lower,
        'predicted_risk': risk_title,
        'created_at': pred.created_at.isoformat() if pred.created_at else None,
    }


def serialize_appointment(appointment):
    return {
        'id': appointment.id,
        'patient_id': appointment.patient_id,
        'doctor_id': appointment.doctor_id,
        'patient_name': appointment.patient.username if appointment.patient else None,
        'doctor_name': appointment.doctor.username if appointment.doctor else None,
        'appointment_date': appointment.appointment_date.isoformat() if appointment.appointment_date else None,
        'reason': appointment.reason,
        'status': appointment.status,
        'created_at': appointment.created_at.isoformat() if appointment.created_at else None,
        'updated_at': appointment.updated_at.isoformat() if appointment.updated_at else None,
    }


def serialize_report(report):
    return {
        'id': report.id,
        'user_id': report.user_id,
        'report_type': report.report_type,
        'title': report.title,
        'content': report.content,
        'from_date': report.from_date.isoformat() if report.from_date else None,
        'to_date': report.to_date.isoformat() if report.to_date else None,
        'created_at': report.created_at.isoformat() if report.created_at else None,
        'updated_at': report.updated_at.isoformat() if report.updated_at else None,
    }


def serialize_record(record):
    return {
        'id': record.id,
        'user_id': record.user_id,
        'file_name': record.file_name,
        'file_path': record.file_path,
        'record_type': record.record_type,
        'description': record.description,
        'created_at': record.created_at.isoformat() if record.created_at else None,
        'updated_at': record.updated_at.isoformat() if record.updated_at else None,
    }


def serialize_message(message):
    return {
        'id': message.id,
        'sender_id': message.sender_id,
        'sender_name': message.sender.username if message.sender else None,
        'recipient_id': message.recipient_id,
        'recipient_name': message.recipient.username if message.recipient else None,
        'content': message.body,
        'method': message.method,
        'is_read': bool(message.is_read),
        'created_at': message.created_at.isoformat() if message.created_at else None,
    }


def resolve_record_path(record_path):
    if not record_path:
        return None

    if os.path.isabs(record_path):
        return record_path

    normalized = record_path.replace('\\', '/').lstrip('/')
    if normalized.startswith('uploads/'):
        normalized = normalized[len('uploads/'):]

    return os.path.join(app.config['UPLOAD_FOLDER'], normalized)


def get_patient_portal_summary(user_id):
    now = datetime.utcnow()

    upcoming_appointments = Appointment.query.filter(
        Appointment.patient_id == user_id,
        Appointment.status.in_(('pending', 'confirmed')),
        ((Appointment.appointment_date == None) | (Appointment.appointment_date >= now))
    ).order_by(Appointment.appointment_date.asc()).limit(3).all()

    next_confirmed = Appointment.query.filter(
        Appointment.patient_id == user_id,
        Appointment.status == 'confirmed',
        Appointment.appointment_date != None,
        Appointment.appointment_date >= now
    ).order_by(Appointment.appointment_date.asc()).first()

    unread_messages = Message.query.filter_by(
        recipient_id=user_id,
        is_read=False
    ).count()

    return {
        'pending_appointments': Appointment.query.filter_by(patient_id=user_id, status='pending').count(),
        'confirmed_appointments': Appointment.query.filter_by(patient_id=user_id, status='confirmed').count(),
        'unread_messages': unread_messages,
        'next_appointment_text': (
            next_confirmed.appointment_date.strftime('%Y-%m-%d %H:%M')
            if next_confirmed and next_confirmed.appointment_date
            else 'No confirmed appointment'
        ),
        'upcoming_appointments': upcoming_appointments,
    }


def get_addon_dashboard_stats(user):
    if not ADDONS_AVAILABLE:
        return {'enabled': False}

    try:
        now = datetime.utcnow()
        stats = {'enabled': True}

        if user.role == 'patient':
            latest_symptom = (
                SymptomEntry.query.filter_by(user_id=user.id)
                .order_by(SymptomEntry.recorded_at.desc())
                .first()
            )
            latest_lab = (
                LabResult.query.filter_by(user_id=user.id)
                .order_by(LabResult.recorded_at.desc())
                .first()
            )
            open_followups = (
                FollowUpTask.query.filter(
                    FollowUpTask.user_id == user.id,
                    FollowUpTask.status.in_(('pending', 'overdue'))
                ).count()
            )
            active_reminders = MedicationReminder.query.filter_by(
                user_id=user.id,
                status='active'
            ).count()

            adherence_rows = (
                db.session.query(MedicationAdherence.was_taken)
                .join(MedicationReminder, MedicationAdherence.reminder_id == MedicationReminder.id)
                .filter(MedicationReminder.user_id == user.id)
                .order_by(MedicationAdherence.created_at.desc())
                .limit(100)
                .all()
            )
            adherence_total = len(adherence_rows)
            adherence_taken = sum(1 for row in adherence_rows if row[0])
            adherence_rate = round((adherence_taken / adherence_total) * 100.0, 1) if adherence_total else None

            recent_followups = (
                FollowUpTask.query.filter_by(user_id=user.id)
                .order_by(FollowUpTask.created_at.desc())
                .limit(5)
                .all()
            )

            stats.update(
                {
                    'latest_symptom_level': latest_symptom.alert_level if latest_symptom else 'none',
                    'latest_symptom_score': latest_symptom.alert_score if latest_symptom else None,
                    'latest_lab_status': latest_lab.status if latest_lab else 'none',
                    'latest_lab_name': latest_lab.test_name if latest_lab else None,
                    'open_followups': open_followups,
                    'active_reminders': active_reminders,
                    'adherence_rate': adherence_rate,
                    'recent_followups': recent_followups,
                    'sos_24h': SOSEvent.query.filter(
                        SOSEvent.user_id == user.id,
                        SOSEvent.triggered_at >= (now - timedelta(hours=24))
                    ).count(),
                }
            )
        else:
            alerts_24h = SymptomEntry.query.filter(
                SymptomEntry.recorded_at >= (now - timedelta(hours=24)),
                SymptomEntry.alert_level.in_(('high', 'critical'))
            ).count()
            sos_24h = SOSEvent.query.filter(
                SOSEvent.triggered_at >= (now - timedelta(hours=24))
            ).count()
            open_followups_total = FollowUpTask.query.filter(
                FollowUpTask.status.in_(('pending', 'overdue'))
            ).count()
            patients_with_open_followups = (
                db.session.query(FollowUpTask.user_id)
                .filter(FollowUpTask.status.in_(('pending', 'overdue')))
                .distinct()
                .count()
            )
            flagged_labs = LabResult.query.filter(
                LabResult.status.in_(('high', 'critical'))
            ).count()

            recent_followups = FollowUpTask.query.order_by(FollowUpTask.created_at.desc()).limit(8).all()

            stats.update(
                {
                    'alerts_24h': alerts_24h,
                    'sos_24h': sos_24h,
                    'open_followups': open_followups_total,
                    'patients_with_open_followups': patients_with_open_followups,
                    'flagged_labs': flagged_labs,
                    'recent_followups': recent_followups,
                }
            )

        return stats
    except Exception:
        return {'enabled': False}


def get_doctor_addon_clinical_data():
    if not ADDONS_AVAILABLE:
        return {'enabled': False}

    try:
        recent_symptoms = (
            SymptomEntry.query.filter(SymptomEntry.alert_level.in_(('high', 'critical')))
            .order_by(SymptomEntry.recorded_at.desc())
            .limit(10)
            .all()
        )
        recent_labs = (
            LabResult.query.filter(LabResult.status.in_(('high', 'critical')))
            .order_by(LabResult.recorded_at.desc())
            .limit(10)
            .all()
        )
        open_followups = (
            FollowUpTask.query.filter(FollowUpTask.status.in_(('pending', 'overdue')))
            .order_by(FollowUpTask.created_at.desc())
            .limit(15)
            .all()
        )
        recent_sos = SOSEvent.query.order_by(SOSEvent.triggered_at.desc()).limit(10).all()

        def username_for(user_id):
            user = db.session.get(User, user_id)
            return user.username if user else f'User {user_id}'

        return {
            'enabled': True,
            'recent_symptoms': [
                {
                    'patient_name': username_for(item.user_id),
                    'alert_level': item.alert_level,
                    'alert_score': item.alert_score,
                    'recorded_at': item.recorded_at,
                }
                for item in recent_symptoms
            ],
            'recent_labs': [
                {
                    'patient_name': username_for(item.user_id),
                    'test_name': item.test_name,
                    'value': item.value,
                    'unit': item.unit,
                    'status': item.status,
                    'recorded_at': item.recorded_at,
                }
                for item in recent_labs
            ],
            'open_followups': [
                {
                    'patient_name': username_for(item.user_id),
                    'title': item.title,
                    'priority': item.priority,
                    'status': item.status,
                    'created_at': item.created_at,
                }
                for item in open_followups
            ],
            'recent_sos': [
                {
                    'patient_name': username_for(item.user_id),
                    'message': item.message,
                    'location': item.location,
                    'triggered_at': item.triggered_at,
                }
                for item in recent_sos
            ],
        }
    except Exception:
        return {'enabled': False}


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# --- Auth Routes ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.form
        username = (data.get('username') or '').strip()
        email = (data.get('email') or '').strip()
        password = data.get('password') or ''
        role = data.get('role', 'patient')

        if not username or not email or not password:
            return render_template('register.html', error='All fields are required.')

        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Username already exists.')
        if User.query.filter_by(email=email).first():
            return render_template('register.html', error='Email already exists.')

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role=role
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            if user.role == 'patient':
                return redirect(url_for('predict'))
            return redirect(url_for('dashboard'))

        return render_template('login.html', error='Invalid credentials')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# --- Dashboard & Core Pages ---
@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    stats = {}
    addon_stats = get_addon_dashboard_stats(current_user)

    if current_user.role == 'patient':
        user_predictions = Prediction.query.filter_by(user_id=current_user.id)
        user_appointments = Appointment.query.filter_by(patient_id=current_user.id)
        user_records = MedicalRecord.query.filter_by(user_id=current_user.id)

        stats['total_predictions'] = user_predictions.count()
        stats['high_risk'] = user_predictions.filter(Prediction.risk_level.ilike('high%')).count()
        stats['appointments'] = user_appointments.count()
        stats['medical_records'] = user_records.count()

        recent_appointments = user_appointments.order_by(Appointment.appointment_date.desc()).limit(5).all()
        recent_predictions = user_predictions.order_by(Prediction.created_at.desc()).limit(5).all()
        recent_reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).limit(5).all()
    else:
        all_appointments = Appointment.query
        stats['total_patients'] = User.query.filter_by(role='patient').count()
        stats['pending_appointments'] = all_appointments.filter_by(status='pending').count()
        stats['confirmed_appointments'] = all_appointments.filter_by(status='confirmed').count()
        stats['reports_created'] = Report.query.count()

        recent_appointments = all_appointments.order_by(Appointment.appointment_date.desc()).limit(5).all()
        recent_predictions = []
        recent_reports = Report.query.order_by(Report.created_at.desc()).limit(5).all()

    return render_template(
        'dashboard.html',
        user=current_user,
        stats=stats,
        addon_stats=addon_stats,
        recent_appointments=recent_appointments,
        recent_predictions=recent_predictions,
        recent_reports=recent_reports
    )


@app.route('/addons')
@login_required
def addons_dashboard():
    if current_user.role in ('doctor', 'admin'):
        clinical_data = get_doctor_addon_clinical_data()
        return render_template('addons_dashboard_doctor.html', user=current_user, clinical_data=clinical_data)
    addon_stats = get_addon_dashboard_stats(current_user)
    return render_template('addons_dashboard.html', user=current_user, addon_stats=addon_stats)


@app.route('/predict', methods=['GET', 'POST'])
@login_required
def predict():
    default_form_data = {
        'age': '',
        'bmi': '',
        'systolic_bp': '120',
        'diastolic_bp': '80',
        'blood_sugar': '95',
        'body_temp': '98.6',
        'heart_rate': '72',
        'diabetes': '0',
    }

    portal_summary = get_patient_portal_summary(current_user.id) if current_user.role == 'patient' else {}

    if request.method == 'POST':
        form_data = {key: (request.form.get(key) or '').strip() for key in default_form_data}
        for key in ('systolic_bp', 'diastolic_bp', 'blood_sugar', 'body_temp', 'heart_rate', 'diabetes'):
            if form_data[key] == '':
                form_data[key] = default_form_data[key]

        try:
            age = float(form_data['age'])
            bmi = float(form_data['bmi'])
            systolic_bp = float(form_data['systolic_bp'])
            diastolic_bp = float(form_data['diastolic_bp'])
            blood_sugar = float(form_data['blood_sugar'])
            body_temp = float(form_data['body_temp'])
            heart_rate = float(form_data['heart_rate'])
            diabetes = 1 if form_data['diabetes'] in ('1', 'true', 'yes', 'y') else 0
        except (TypeError, ValueError):
            portal_summary = get_patient_portal_summary(current_user.id) if current_user.role == 'patient' else {}
            return render_template(
                'index.html',
                user=current_user,
                error='Please enter valid numeric values for all required fields.',
                form_data=form_data,
                portal_summary=portal_summary,
            )

        raw_data = [
            age,
            bmi,
            systolic_bp,
            diastolic_bp,
            blood_sugar,
            body_temp,
            heart_rate,
            diabetes,
        ]

        if model is not None and scaler is not None:
            features = np.array([raw_data], dtype=float)
            scaled_features = scaler.transform(features)
            prediction = int(model.predict(scaled_features)[0])
            risk = 'High' if prediction == 1 else 'Low'
        else:
            risk = 'High' if (
                age >= 35
                or bmi >= 30
                or systolic_bp >= 140
                or diastolic_bp >= 90
                or blood_sugar >= 140
                or diabetes == 1
            ) else 'Low'

        advice = RISK_ADVICE.get(risk, RISK_ADVICE['Low'])

        new_prediction = Prediction(
            user_id=current_user.id,
            user_name=current_user.username,
            age=int(age) if age else None,
            bmi=bmi,
            risk_level=risk,
            systolic_bp=int(systolic_bp),
            diastolic_bp=int(diastolic_bp),
            blood_sugar=blood_sugar,
            body_temp=body_temp,
            heart_rate=int(heart_rate),
            diabetes=str(diabetes)
        )
        db.session.add(new_prediction)
        db.session.commit()
        portal_summary = get_patient_portal_summary(current_user.id) if current_user.role == 'patient' else {}

        return render_template(
            'index.html',
            user=current_user,
            prediction_text=risk,
            risk_class='high-risk' if risk == 'High' else 'low-risk',
            advice=advice,
            form_data=form_data,
            portal_summary=portal_summary,
        )

    return render_template('index.html', user=current_user, form_data=default_form_data, portal_summary=portal_summary)


@app.route('/accuracy')
@login_required
def accuracy():
    if is_doctor(current_user):
        predictions = Prediction.query.order_by(Prediction.created_at.desc()).all()
    else:
        predictions = Prediction.query.filter_by(user_id=current_user.id).order_by(Prediction.created_at.desc()).all()

    serialized_predictions = [serialize_prediction(pred) for pred in predictions]

    high_risk_count = sum(1 for pred in serialized_predictions if pred['risk_level'] == 'high')
    medium_risk_count = sum(1 for pred in serialized_predictions if pred['risk_level'] == 'medium')
    low_risk_count = sum(1 for pred in serialized_predictions if pred['risk_level'] == 'low')

    return render_template(
        'accuracy.html',
        user=current_user,
        predictions=serialized_predictions,
        high_risk_count=high_risk_count,
        medium_risk_count=medium_risk_count,
        low_risk_count=low_risk_count,
    )


# --- Appointments ---
@app.route('/appointments')
@login_required
def appointments():
    if is_doctor(current_user):
        appointments_data = Appointment.query.order_by(Appointment.appointment_date.desc()).all()
        doctors = []
    else:
        appointments_data = Appointment.query.filter_by(patient_id=current_user.id).order_by(Appointment.appointment_date.desc()).all()
        doctors = User.query.filter(User.role.in_(('doctor', 'admin'))).order_by(User.username.asc()).all()

    for appointment in appointments_data:
        appointment.doctor_name = appointment.doctor.username if appointment.doctor else None
        appointment.patient_name = appointment.patient.username if appointment.patient else None

    return render_template(
        'appointments.html',
        user=current_user,
        appointments=appointments_data,
        doctors=doctors,
    )


@app.route('/api/appointments', methods=['GET', 'POST'])
@login_required
def api_appointments():
    if request.method == 'GET':
        if is_doctor(current_user):
            appointments_data = Appointment.query.order_by(Appointment.appointment_date.desc()).all()
        else:
            appointments_data = Appointment.query.filter_by(patient_id=current_user.id).order_by(Appointment.appointment_date.desc()).all()

        return jsonify([serialize_appointment(appointment) for appointment in appointments_data])

    data = request.get_json(silent=True) or {}

    if current_user.role == 'patient':
        patient_id = current_user.id
    else:
        patient_id = data.get('patient_id')

    if patient_id is None:
        return jsonify({'error': 'patient_id is required'}), 400

    try:
        patient_id = int(patient_id)
    except (TypeError, ValueError):
        return jsonify({'error': 'patient_id must be an integer'}), 400

    if not can_access_user_data(patient_id):
        return jsonify({'error': 'Forbidden'}), 403

    doctor_id = data.get('doctor_id')
    if doctor_id in ('', None):
        doctor_id = None
    else:
        try:
            doctor_id = int(doctor_id)
        except (TypeError, ValueError):
            return jsonify({'error': 'doctor_id must be an integer'}), 400

    assigned_doctor = None
    if doctor_id is not None:
        assigned_doctor = db.session.get(User, doctor_id)
        if assigned_doctor is None or not is_doctor(assigned_doctor):
            return jsonify({'error': 'doctor_id must belong to a doctor'}), 400

    appointment_date = parse_iso_datetime(data.get('appointment_date'))
    reason = (data.get('reason') or '').strip()
    if appointment_date is None:
        return jsonify({'error': 'appointment_date is required and must be ISO datetime'}), 400
    if not reason:
        return jsonify({'error': 'reason is required'}), 400

    status = (data.get('status') or ('confirmed' if doctor_id else 'pending')).strip().lower()
    if status not in {'pending', 'confirmed', 'cancelled', 'completed'}:
        status = 'pending'

    new_appointment = Appointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        appointment_date=appointment_date,
        reason=reason,
        status=status
    )
    db.session.add(new_appointment)

    if current_user.role == 'patient':
        if assigned_doctor:
            db.session.add(Notification(
                user_id=assigned_doctor.id,
                title='New Appointment Request',
                message=f'Patient {current_user.username} requested an appointment on {appointment_date.strftime("%Y-%m-%d %H:%M")}.',
                notification_type='appointment'
            ))
        else:
            doctors = User.query.filter(User.role.in_(('doctor', 'admin'))).all()
            for doctor in doctors:
                db.session.add(Notification(
                    user_id=doctor.id,
                    title='New Appointment Request',
                    message=f'Patient {current_user.username} requested an appointment on {appointment_date.strftime("%Y-%m-%d %H:%M")}.',
                    notification_type='appointment'
                ))
    else:
        db.session.add(Notification(
            user_id=patient_id,
            title='Appointment Scheduled',
            message=f'Dr. {current_user.username} scheduled your appointment for {appointment_date.strftime("%Y-%m-%d %H:%M")}.',
            notification_type='appointment'
        ))

    db.session.commit()

    return jsonify({'success': True, 'appointment': serialize_appointment(new_appointment)}), 201


@app.route('/api/appointments/<int:appointment_id>', methods=['PUT', 'DELETE'])
@login_required
def update_or_delete_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)

    if not (is_doctor(current_user) or appointment.patient_id == current_user.id):
        return jsonify({'error': 'Forbidden'}), 403

    if request.method == 'PUT':
        data = request.get_json(silent=True) or {}
        previous_status = appointment.status

        if 'status' in data:
            status = (data.get('status') or '').strip().lower()
            if status in {'pending', 'confirmed', 'cancelled', 'completed'}:
                appointment.status = status
                if status == 'confirmed' and is_doctor(current_user):
                    appointment.doctor_id = current_user.id

        if 'appointment_date' in data:
            parsed_date = parse_iso_datetime(data.get('appointment_date'))
            if parsed_date is not None:
                appointment.appointment_date = parsed_date

        if 'reason' in data:
            appointment.reason = data.get('reason')

        if appointment.status != previous_status:
            target_user_id = appointment.patient_id if is_doctor(current_user) else appointment.doctor_id
            if target_user_id:
                db.session.add(Notification(
                    user_id=target_user_id,
                    title='Appointment Updated',
                    message=f'Appointment status changed from {previous_status} to {appointment.status}.',
                    notification_type='appointment'
                ))

        db.session.commit()
        return jsonify({'success': True, 'appointment': serialize_appointment(appointment)})

    appointment.status = 'cancelled'

    target_user_id = appointment.patient_id if is_doctor(current_user) else appointment.doctor_id
    if target_user_id:
        db.session.add(Notification(
            user_id=target_user_id,
            title='Appointment Cancelled',
            message='An appointment was cancelled. Please review your schedule.',
            notification_type='appointment'
        ))

    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/appointments/<int:appointment_id>/accept', methods=['POST'])
@login_required
def accept_appointment(appointment_id):
    if not is_doctor(current_user):
        return jsonify({'error': 'Only doctors can accept appointments'}), 403

    appointment = Appointment.query.get_or_404(appointment_id)
    appointment.status = 'confirmed'
    appointment.doctor_id = current_user.id

    notification = Notification(
        user_id=appointment.patient_id,
        title='Appointment Confirmed',
        message=f'Your appointment request has been confirmed by Dr. {current_user.username}.',
        notification_type='appointment'
    )
    db.session.add(notification)
    db.session.commit()

    return jsonify({'success': True, 'appointment': serialize_appointment(appointment)})


# --- Messages ---
@app.route('/messages')
@login_required
def messages():
    users = User.query.filter(User.id != current_user.id).order_by(User.username.asc()).all()
    unread_rows = db.session.query(
        Message.sender_id,
        func.count(Message.id)
    ).filter(
        Message.recipient_id == current_user.id,
        Message.is_read == False
    ).group_by(Message.sender_id).all()

    unread_counts = {sender_id: count for sender_id, count in unread_rows}

    return render_template(
        'messages.html',
        user=current_user,
        conversations=users,
        unread_counts=unread_counts,
    )


@app.route('/api/messages', methods=['GET', 'POST'])
@login_required
def api_messages():
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        receiver_id = data.get('receiver_id') or data.get('recipient_id')
        content = (data.get('content') or data.get('message') or '').strip()

        if receiver_id is None or not content:
            return jsonify({'error': 'receiver_id and content are required'}), 400

        try:
            receiver_id = int(receiver_id)
        except (TypeError, ValueError):
            return jsonify({'error': 'receiver_id must be an integer'}), 400

        recipient = db.session.get(User, receiver_id)
        if recipient is None:
            return jsonify({'error': 'Recipient not found'}), 404

        method = data.get('contact_method') or data.get('method') or 'in_app'
        if data.get('send_as_email'):
            method = 'email'

        message = Message(
            sender_id=current_user.id,
            recipient_id=receiver_id,
            body=content,
            method=method
        )
        db.session.add(message)
        db.session.commit()
        return jsonify({'success': True, 'message': serialize_message(message)}), 201

    with_user = request.args.get('with_user', type=int)

    if with_user:
        messages_data = Message.query.filter(
            ((Message.sender_id == current_user.id) & (Message.recipient_id == with_user)) |
            ((Message.sender_id == with_user) & (Message.recipient_id == current_user.id))
        ).order_by(Message.created_at.asc()).all()

        unread_messages = Message.query.filter(
            Message.sender_id == with_user,
            Message.recipient_id == current_user.id,
            Message.is_read == False
        ).all()
        for unread in unread_messages:
            unread.is_read = True
        if unread_messages:
            db.session.commit()
    else:
        messages_data = Message.query.filter(
            (Message.sender_id == current_user.id) | (Message.recipient_id == current_user.id)
        ).order_by(Message.created_at.desc()).all()

    return jsonify([serialize_message(message) for message in messages_data])


@app.route('/api/messages/unread-summary')
@login_required
def unread_message_summary():
    unread_rows = db.session.query(
        Message.sender_id,
        func.count(Message.id)
    ).filter(
        Message.recipient_id == current_user.id,
        Message.is_read == False
    ).group_by(Message.sender_id).all()

    return jsonify({str(sender_id): count for sender_id, count in unread_rows})


@app.route('/api/send-message', methods=['POST'])
@login_required
def send_message():
    data = request.get_json(silent=True) or {}
    recipient_id = data.get('recipient_id')
    method = (data.get('method') or 'in_app').strip().lower()
    message_body = (data.get('message') or '').strip()

    if recipient_id is None or not message_body:
        return jsonify({'error': 'recipient_id and message are required'}), 400

    try:
        recipient_id = int(recipient_id)
    except (TypeError, ValueError):
        return jsonify({'error': 'recipient_id must be an integer'}), 400

    recipient = db.session.get(User, recipient_id)
    if recipient is None:
        return jsonify({'error': 'Recipient not found'}), 404

    message = Message(
        sender_id=current_user.id,
        recipient_id=recipient_id,
        body=message_body,
        method=method
    )
    db.session.add(message)
    db.session.commit()

    return jsonify({'success': True, 'message': serialize_message(message)}), 201


# --- Reports ---
@app.route('/reports')
@login_required
def reports():
    if is_doctor(current_user):
        reports_data = Report.query.order_by(Report.created_at.desc()).all()
    else:
        reports_data = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).all()

    return render_template('reports.html', user=current_user, reports=reports_data)


@app.route('/api/reports', methods=['GET', 'POST'])
@login_required
def api_reports():
    if request.method == 'GET':
        if is_doctor(current_user):
            reports_data = Report.query.order_by(Report.created_at.desc()).all()
        else:
            reports_data = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).all()

        return jsonify([serialize_report(report) for report in reports_data])

    if not is_doctor(current_user):
        return jsonify({'error': 'Only doctors can create reports'}), 403

    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id')
    report_type = (data.get('report_type') or '').strip()
    title = (data.get('title') or '').strip()
    content = (data.get('content') or '').strip()

    if user_id is None or not title or not content:
        return jsonify({'error': 'user_id, title and content are required'}), 400

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return jsonify({'error': 'user_id must be an integer'}), 400

    patient = db.session.get(User, user_id)
    if patient is None:
        return jsonify({'error': 'Patient not found'}), 404

    report = Report(
        user_id=user_id,
        report_type=report_type,
        title=title,
        content=content,
        from_date=parse_iso_date(data.get('from_date')),
        to_date=parse_iso_date(data.get('to_date')),
    )
    db.session.add(report)
    db.session.commit()

    notification = Notification(
        user_id=user_id,
        title='New Report Available',
        message=f'A new {report_type.replace("_", " ")} report has been generated for you.',
        notification_type='report'
    )
    db.session.add(notification)
    db.session.commit()

    return jsonify({'success': True, 'report': serialize_report(report)}), 201


# --- Medical Records ---
@app.route('/medical-records')
@app.route('/medical_records')
@login_required
def medical_records():
    if is_doctor(current_user):
        records = MedicalRecord.query.order_by(MedicalRecord.created_at.desc()).all()
    else:
        records = MedicalRecord.query.filter_by(user_id=current_user.id).order_by(MedicalRecord.created_at.desc()).all()

    return render_template('medical_records.html', user=current_user, records=records)


@app.route('/api/medical-records', methods=['GET', 'POST'])
@login_required
def api_medical_records():
    if request.method == 'GET':
        if is_doctor(current_user):
            records = MedicalRecord.query.order_by(MedicalRecord.created_at.desc()).all()
        else:
            records = MedicalRecord.query.filter_by(user_id=current_user.id).order_by(MedicalRecord.created_at.desc()).all()

        return jsonify([serialize_record(record) for record in records])

    if request.is_json:
        data = request.get_json(silent=True) or {}
        user_id = data.get('user_id', current_user.id)
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return jsonify({'error': 'user_id must be an integer'}), 400

        if not can_access_user_data(user_id):
            return jsonify({'error': 'Forbidden'}), 403

        file_name = (data.get('file_name') or '').strip()
        file_path = (data.get('file_path') or '').strip()
        if not file_name or not file_path:
            return jsonify({'error': 'file_name and file_path are required'}), 400

        record = MedicalRecord(
            user_id=user_id,
            file_name=file_name,
            file_path=file_path,
            record_type=(data.get('record_type') or 'other').strip(),
            description=(data.get('description') or '').strip()
        )
    else:
        uploaded_file = request.files.get('file')
        if uploaded_file is None or uploaded_file.filename == '':
            return jsonify({'error': 'No file uploaded'}), 400

        raw_user_id = request.form.get('user_id', current_user.id)
        try:
            user_id = int(raw_user_id)
        except (TypeError, ValueError):
            return jsonify({'error': 'Invalid user_id'}), 400

        if not can_access_user_data(user_id):
            return jsonify({'error': 'Forbidden'}), 403

        safe_filename = secure_filename(uploaded_file.filename)
        unique_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{safe_filename}"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        uploaded_file.save(save_path)

        record = MedicalRecord(
            user_id=user_id,
            file_name=safe_filename,
            file_path=unique_name,
            record_type=(request.form.get('record_type') or 'other').strip(),
            description=(request.form.get('description') or '').strip()
        )

    db.session.add(record)
    db.session.commit()

    return jsonify({'success': True, 'record': serialize_record(record)}), 201


@app.route('/api/medical-records/<int:record_id>/download')
@login_required
def download_medical_record(record_id):
    record = MedicalRecord.query.get_or_404(record_id)

    if not can_access_user_data(record.user_id):
        return jsonify({'error': 'Forbidden'}), 403

    absolute_path = resolve_record_path(record.file_path)
    if absolute_path is None or not os.path.exists(absolute_path):
        return jsonify({'error': 'File not found'}), 404

    directory = os.path.dirname(absolute_path)
    filename = os.path.basename(absolute_path)
    return send_from_directory(directory, filename, as_attachment=True, download_name=record.file_name)


@app.route('/api/medical-records/<int:record_id>', methods=['DELETE'])
@login_required
def delete_medical_record(record_id):
    record = MedicalRecord.query.get_or_404(record_id)

    if not (is_doctor(current_user) or record.user_id == current_user.id):
        return jsonify({'error': 'Forbidden'}), 403

    absolute_path = resolve_record_path(record.file_path)
    if absolute_path and os.path.exists(absolute_path):
        upload_root = os.path.abspath(app.config['UPLOAD_FOLDER'])
        target = os.path.abspath(absolute_path)
        if target.startswith(upload_root):
            try:
                os.remove(target)
            except OSError:
                pass

    db.session.delete(record)
    db.session.commit()
    return jsonify({'success': True})


# --- Supporting APIs ---
@app.route('/api/doctors')
@login_required
def api_doctors():
    doctors = User.query.filter(User.role.in_(('doctor', 'admin'))).order_by(User.username.asc()).all()
    return jsonify([
        {
            'id': doctor.id,
            'username': doctor.username,
            'email': doctor.email,
            'phone_number': doctor.phone_number,
            'role': doctor.role,
        }
        for doctor in doctors
    ])


@app.route('/api/patients')
@login_required
def api_patients():
    if not is_doctor(current_user):
        return jsonify({'error': 'Only doctors can view patient directory'}), 403

    patients = User.query.filter_by(role='patient').order_by(User.username.asc()).all()
    return jsonify([
        {
            'id': patient.id,
            'username': patient.username,
            'email': patient.email,
            'phone_number': patient.phone_number,
        }
        for patient in patients
    ])


@app.route('/api/predictions')
@login_required
def api_predictions():
    if is_doctor(current_user):
        predictions = Prediction.query.order_by(Prediction.created_at.desc()).all()
    else:
        predictions = Prediction.query.filter_by(user_id=current_user.id).order_by(Prediction.created_at.desc()).all()

    return jsonify([serialize_prediction(pred) for pred in predictions])


@app.route('/api/users/<int:user_id>')
@login_required
def api_user_details(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'phone_number': user.phone_number,
        'role': user.role,
    })


@app.route('/api/stats')
@login_required
def api_stats():
    if is_doctor(current_user):
        predictions = Prediction.query.all()
    else:
        predictions = Prediction.query.filter_by(user_id=current_user.id).all()

    total = len(predictions)
    high_risk = 0
    low_risk = 0
    age_values = []
    users = set()

    for pred in predictions:
        normalized = normalize_risk(pred.risk_level)
        if normalized == 'High':
            high_risk += 1
        elif normalized == 'Low':
            low_risk += 1

        if pred.age is not None:
            age_values.append(pred.age)
        if pred.user_id is not None:
            users.add(pred.user_id)

    average_age = (sum(age_values) / len(age_values)) if age_values else 0

    return jsonify({
        'total': total,
        'high_risk': high_risk,
        'low_risk': low_risk,
        'average_age': average_age,
        'unique_patients': len(users),
    })


@app.route('/api/notifications')
@login_required
def api_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return jsonify([
        {
            'id': notif.id,
            'title': notif.title,
            'message': notif.message,
            'notification_type': notif.notification_type,
            'is_read': notif.is_read,
            'created_at': notif.created_at.isoformat() if notif.created_at else None,
        }
        for notif in notifications
    ])


@app.route('/api/notifications/<int:notification_id>', methods=['PUT'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)

    if notification.user_id != current_user.id:
        return jsonify({'error': 'Forbidden'}), 403

    notification.is_read = True
    db.session.commit()
    return jsonify({'success': True})


# --- Doctor Views ---
@app.route('/doctor/patients')
@login_required
def doctor_patients():
    if not is_doctor(current_user):
        return render_template('error.html', message='Access denied. Doctor account required.'), 403

    predictions = Prediction.query.order_by(Prediction.created_at.desc()).all()
    for prediction in predictions:
        prediction.predicted_risk = normalize_risk(prediction.risk_level)

    return render_template('doctor_dashboard_enhanced.html', user=current_user, predictions=predictions)


@app.route('/doctor/notifications')
@login_required
def doctor_notifications():
    if not is_doctor(current_user):
        return render_template('error.html', message='Access denied. Doctor account required.'), 403

    pending_appointments = Appointment.query.filter_by(status='pending').order_by(Appointment.created_at.desc()).all()
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()

    return render_template(
        'doctor_notifications.html',
        user=current_user,
        appointments=pending_appointments,
        notifications=notifications,
    )


@app.route('/history')
@login_required
def history():
    page = request.args.get('page', 1, type=int)

    if is_doctor(current_user):
        query = Prediction.query.order_by(Prediction.created_at.desc())
    else:
        query = Prediction.query.filter_by(user_id=current_user.id).order_by(Prediction.created_at.desc())

    predictions_page = query.paginate(page=page, per_page=20, error_out=False)
    for prediction in predictions_page.items:
        prediction.predicted_risk = normalize_risk(prediction.risk_level)
        prediction.confidence = 100.0
        if prediction.blood_sugar is None:
            prediction.blood_sugar = 0.0
        if prediction.bmi is None:
            prediction.bmi = 0.0

    return render_template('history.html', user=current_user, predictions=predictions_page)


# --- Care Hub Module Bootstrap (integrated into main app runtime) ---
try:
    from addons import models as addon_models  # noqa: F401
    from addons.routes import addon_bp

    if addon_bp.name not in app.blueprints:
        app.register_blueprint(addon_bp)
        print('Care Hub modules registered at /api/addons')
except Exception as addon_bootstrap_error:
    print(f'Warning: Care Hub modules failed to load: {addon_bootstrap_error}')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

