import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
from models import User, Prediction, Report, MedicalRecord, Appointment, Message, Notification

errors = []
with app.app_context():
    user = User.query.first()
    sample_pred = Prediction.query.first()
    context = {
        'user': user or User(username='sample', email='s@example.com', role='doctor'),
        'predictions': [sample_pred] if sample_pred else [],
        'reports': Report.query.limit(2).all() if 'Report' in globals() else [],
        'records': MedicalRecord.query.limit(2).all() if 'MedicalRecord' in globals() else [],
        'conversations': [{'id':1,'username':'Alice','email':'a@example.com'}],
        'messages': Message.query.limit(2).all() if 'Message' in globals() else [],
        'appointments': Appointment.query.limit(2).all() if 'Appointment' in globals() else [],
        'notifications': Notification.query.limit(2).all() if 'Notification' in globals() else [],
        'stats': {'total':0},
        'form_data': {}
    }

    template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates')
    templates = [f for f in os.listdir(template_dir) if f.endswith('.html')]
    for t in templates:
        try:
            tmpl = app.jinja_env.get_template(t)
            with app.test_request_context():
                out = tmpl.render(**context)
            print(f"OK: {t} (len={len(out)})")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"ERROR: {t}\n{tb}")
            errors.append((t, tb))

    print('\nSummary:')
    print(f'Templates: {len(templates)} checked, {len(errors)} errors')
    for t, tb in errors:
        print('---', t)
        print(tb[:400])
