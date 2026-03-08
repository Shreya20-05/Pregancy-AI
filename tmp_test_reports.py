from app import app, db
from models import User, Report

with app.app_context():
    # Create test doctor if not exists
    u = User.query.filter_by(username='testdoc').first()
    if not u:
        u = User(username='testdoc', email='testdoc@example.com', role='doctor')
        u.set_password('pass123')
        db.session.add(u)
        db.session.commit()

    # Ensure at least one report exists
    r = Report.query.first()
    if not r:
        rep = Report(user_id=u.id, report_type='clinical_summary', title='Test Report', content='Sample content', generated_by_id=u.id)
        db.session.add(rep)
        db.session.commit()

    client = app.test_client()
    # Log in
    rv = client.post('/login', data={'username':'testdoc','password':'pass123'}, follow_redirects=True)
    print('\n--- LOGIN STATUS:', rv.status_code)
    # Request reports
    resp = client.get('/reports')
    print('\n--- REPORTS STATUS:', resp.status_code)
    data = resp.get_data(as_text=True)
    print('\n--- BEGIN HTML PREVIEW ---')
    print(data[:4000])
    print('\n--- END HTML PREVIEW ---')
