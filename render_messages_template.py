import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
from models import User, Message

with app.app_context():
    user = User.query.filter_by(username='test_doctor').first()
    try:
        tmpl = app.jinja_env.get_template('messages.html')
        out = tmpl.render(user=user, conversations=[{'id':1,'username':'Alice','email':'a@example.com'}], messages=[])
        print('Rendered length:', len(out))
        print(out[:400])
    except Exception as e:
        import traceback
        traceback.print_exc()
