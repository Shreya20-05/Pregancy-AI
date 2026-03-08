import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app, db
from models import User
with app.app_context():
    u = User.query.filter_by(username='test_doctor').first()
    if not u:
        u = User(username='test_doctor', email='test_doctor@example.com', role='doctor')
        u.set_password('pass')
        db.session.add(u); db.session.commit()
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = u.id; sess['username'] = u.username; sess['role'] = u.role
    resp = client.get('/messages')
    print('status', resp.status_code)
    body = resp.get_data(as_text=True)
    idx = body.find('selectConversation')
    print(body[idx-80:idx+80])
