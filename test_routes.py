import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app, db
from models import User, Prediction, Report, MedicalRecord

with app.app_context():
    # Ensure users
    doctor = User.query.filter_by(username='test_doctor').first()
    if not doctor:
        doctor = User(username='test_doctor', email='doc@example.com', role='doctor')
        doctor.set_password('pass')
        db.session.add(doctor); db.session.commit()
    patient = User.query.filter_by(username='test_patient').first()
    if not patient:
        patient = User(username='test_patient', email='pat@example.com', role='patient')
        patient.set_password('pass')
        db.session.add(patient); db.session.commit()

    # Create sample data
    if not Prediction.query.first():
        p = Prediction(user_id=patient.id, age=25, bmi=22.5, systolic_bp=110, diastolic_bp=70, blood_sugar=4.5, body_temp=36.6, heart_rate=70, diabetes=False, predicted_risk='Low', confidence=95)
        db.session.add(p); db.session.commit()
    if not Report.query.first():
        r = Report(user_id=patient.id, report_type='patient_health', title='Sample', content='Sample content')
        db.session.add(r); db.session.commit()
    if not MedicalRecord.query.first():
        m = MedicalRecord(user_id=patient.id, record_type='ultrasound', file_name='scan.pdf', file_path='/uploads/scan.pdf')
        db.session.add(m); db.session.commit()

    client = app.test_client()

    def as_user(u):
        with client.session_transaction() as sess:
            sess['user_id'] = u.id; sess['username'] = u.username; sess['role'] = u.role

    endpoints = [
        ('doctor', '/dashboard'),
        ('doctor', '/reports'),
        ('doctor', '/messages'),
        ('doctor', '/medical-records'),
        ('patient', '/dashboard'),
        ('patient', '/reports'),
        ('patient', '/messages'),
        ('patient', '/medical-records'),
    ]

    for role, ep in endpoints:
        u = doctor if role=='doctor' else patient
        as_user(u)
        resp = client.get(ep)
        print(role, ep, resp.status_code)

    # Test API endpoints
    as_user(doctor)
    print('/api/predictions', client.get('/api/predictions').status_code)
    print('/api/reports', client.get('/api/reports').status_code)
    print('/api/medical-records', client.get('/api/medical-records').status_code)

    print('Done')
