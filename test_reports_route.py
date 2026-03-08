import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app, db
from models import User, Report
from flask import session

with app.app_context():
    # Ensure a test user exists
    user = User.query.filter_by(username='test_doctor').first()
    if not user:
        user = User(username='test_doctor', email='test_doctor@example.com', role='doctor')
        user.set_password('pass')
        db.session.add(user)
        db.session.commit()

    # Ensure a test report exists
    report = Report.query.filter_by(title='Test Report for Debug').first()
    if not report:
        report = Report(user_id=user.id, report_type='clinical_summary', title='Test Report for Debug', content='Debug content')
        db.session.add(report)
        db.session.commit()

    # Use test client to request /reports with session
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = user.id
        sess['username'] = user.username
        sess['role'] = user.role

    resp = client.get('/reports')
    print('Status code:', resp.status_code)
    data = resp.get_data(as_text=True)
    # Print first 1000 chars of response for inspection
    print(data[:1000])
