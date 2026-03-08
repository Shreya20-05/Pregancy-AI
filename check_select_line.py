import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
from models import User

with app.app_context():
    tmpl = app.jinja_env.get_template('messages.html')
    out = tmpl.render(user=User.query.first(), conversations=[{'id':1,'username':'Alice','email':'a@example.com'}], messages=[])
    for line in out.splitlines():
        if 'selectConversation' in line:
            print(line)
