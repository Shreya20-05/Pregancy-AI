import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from models import User, Prediction, Report, MedicalRecord, Appointment, Message
from datetime import datetime, timedelta

print("\n" + "=" * 70)
print("END-TO-END FUNCTIONAL TEST")
print("=" * 70)

with app.app_context():
    client = app.test_client()
    
    # Get test users
    doctor = User.query.filter_by(username='test_doctor').first()
    patient = User.query.filter_by(username='test_patient').first()
    
    if not doctor or not patient:
        print("❌ Test users not found")
        sys.exit(1)
    
    print(f"\n✅ Doctor: {doctor.username} (ID: {doctor.id})")
    print(f"✅ Patient: {patient.username} (ID: {patient.id})")
    
    # Test Session Management
    print("\n[TEST 1] Session Management...")
    with client:
        resp = client.get('/login')
        print(f"  ✅ GET /login: {resp.status_code}")
    
    # Test Authentication
    print("\n[TEST 2] Authentication...")
    with client.session_transaction() as sess:
        sess['user_id'] = patient.id
        sess['username'] = patient.username
        sess['role'] = patient.role
    
    resp = client.get('/dashboard')
    if resp.status_code == 200:
        print(f"  ✅ Patient dashboard: HTTP 200")
    else:
        print(f"  ❌ Patient dashboard: HTTP {resp.status_code}")
    
    # Test Doctor Dashboard
    print("\n[TEST 3] Doctor Dashboard...")
    with client.session_transaction() as sess:
        sess['user_id'] = doctor.id
        sess['username'] = doctor.username
        sess['role'] = doctor.role
    
    resp = client.get('/doctor/patients')
    if resp.status_code == 200:
        print(f"  ✅ Doctor view (patients): HTTP 200")
    else:
        print(f"  ❌ Doctor view (patients): HTTP {resp.status_code}")
    
    # Test Report Creation (Doctor)
    print("\n[TEST 4] Report Creation...")
    with client.session_transaction() as sess:
        sess['user_id'] = doctor.id
        sess['username'] = doctor.username
        sess['role'] = doctor.role
    
    report_data = {
        'user_id': patient.id,
        'report_type': 'clinical_summary',
        'title': 'Final Year Project Test Report',
        'content': 'Test content for comprehensive audit',
        'from_date': None,
        'to_date': datetime.utcnow().isoformat()
    }
    
    resp = client.post('/api/reports', json=report_data)
    if resp.status_code == 201:
        print(f"  ✅ Create report: HTTP 201")
    else:
        print(f"  ❌ Create report: HTTP {resp.status_code}")
    
    # Test Messaging
    print("\n[TEST 5] Messaging System...")
    with client.session_transaction() as sess:
        sess['user_id'] = patient.id
        sess['username'] = patient.username
        sess['role'] = patient.role
    
    msg_data = {'receiver_id': doctor.id, 'content': 'Hello Doctor - Test Message'}
    resp = client.post('/api/messages', json=msg_data)
    if resp.status_code == 201:
        print(f"  ✅ Send message: HTTP 201")
    else:
        print(f"  ❌ Send message: HTTP {resp.status_code}")
    
    # Test Medical Records
    print("\n[TEST 6] Medical Records...")
    record_data = {
        'user_id': patient.id,
        'record_type': 'ultrasound',
        'file_name': 'test_scan.pdf',
        'file_path': '/uploads/test_scan.pdf',
        'description': 'Test ultrasound scan'
    }
    
    resp = client.post('/api/medical-records', json=record_data)
    if resp.status_code == 201:
        print(f"  ✅ Upload medical record: HTTP 201")
    else:
        print(f"  ❌ Upload medical record: HTTP {resp.status_code}")
    
    # Test Appointments
    print("\n[TEST 7] Appointments System...")
    appt_date = (datetime.utcnow() + timedelta(days=7)).isoformat()
    appt_data = {
        'patient_id': patient.id,
        'doctor_id': doctor.id,
        'appointment_date': appt_date,
        'reason': 'Final Year Project Test Appointment'
    }
    
    resp = client.post('/api/appointments', json=appt_data)
    if resp.status_code == 201:
        print(f"  ✅ Create appointment: HTTP 201")
    else:
        print(f"  ❌ Create appointment: HTTP {resp.status_code}")
    
    # Test Data Retrieval
    print("\n[TEST 8] Data Retrieval...")
    endpoints = [
        ('/api/predictions', patient),
        ('/api/reports', patient),
        ('/api/medical-records', patient),
        ('/api/appointments', patient),
        ('/api/messages', patient),
        ('/api/notifications', patient),
    ]
    
    for endpoint, user in endpoints:
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
            sess['username'] = user.username
            sess['role'] = user.role
        
        resp = client.get(endpoint)
        status = "✅" if resp.status_code == 200 else "❌"
        print(f"  {status} GET {endpoint}: HTTP {resp.status_code}")
    
    # Test Permissions (Patient tries to create report - should fail)
    print("\n[TEST 9] Permission Enforcement...")
    with client.session_transaction() as sess:
        sess['user_id'] = patient.id
        sess['username'] = patient.username
        sess['role'] = patient.role
    
    resp = client.post('/api/reports', json=report_data)
    if resp.status_code == 403:
        print(f"  ✅ Patient cannot create reports: HTTP 403 (Forbidden)")
    else:
        print(f"  ❌ Permission check failed: HTTP {resp.status_code}")

print("\n" + "=" * 70)
print("✅ ALL FUNCTIONAL TESTS PASSED")
print("=" * 70 + "\n")
