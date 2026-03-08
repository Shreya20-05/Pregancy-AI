import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app, db
from models import User

with app.app_context():
    doctor = User.query.filter_by(username='test_doctor').first()
    patient = User.query.filter_by(username='test_patient').first()
    if not doctor or not patient:
        print('Missing test users; run test_routes first')
        raise SystemExit(1)

    client = app.test_client()

    def as_user(u):
        with client.session_transaction() as sess:
            sess['user_id'] = u.id; sess['username'] = u.username; sess['role'] = u.role

    # Doctor creates a report for patient
    as_user(doctor)
    resp = client.post('/api/reports', json={
        'user_id': patient.id,
        'report_type': 'clinical_summary',
        'title': 'API Created Report',
        'content': 'Automated test report',
        'from_date': None,
        'to_date': None
    })
    print('/api/reports POST', resp.status_code, resp.get_json())

    # Patient tries to create a report (should be forbidden)
    as_user(patient)
    resp = client.post('/api/reports', json={
        'user_id': patient.id,
        'report_type': 'patient_health',
        'title': 'Patient Created',
        'content': 'Should be forbidden'
    })
    print('/api/reports POST as patient', resp.status_code, resp.get_json())

    # Send message from patient to doctor
    as_user(patient)
    resp = client.post('/api/messages', json={'receiver_id': doctor.id, 'content': 'Hello doc'})
    print('/api/messages POST', resp.status_code, resp.get_json())

    # Create medical record as patient
    resp = client.post('/api/medical-records', json={'user_id': patient.id, 'record_type': 'ultrasound', 'file_name': 'test.pdf', 'file_path': '/uploads/test.pdf', 'description': 'Test upload'})
    print('/api/medical-records POST', resp.status_code, resp.get_json())

    # Create appointment as patient
    from datetime import datetime, timedelta
    appt_date = (datetime.utcnow() + timedelta(days=7)).isoformat()
    resp = client.post('/api/appointments', json={'patient_id': patient.id, 'doctor_id': doctor.id, 'appointment_date': appt_date, 'reason': 'Checkup'})
    print('/api/appointments POST', resp.status_code, resp.get_json())

    print('Done')
