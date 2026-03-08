import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
from models import User, Report

with app.app_context():
    user = User.query.filter_by(username='test_doctor').first()
    reports = Report.query.all()
    try:
        tmpl = app.jinja_env.get_template('reports.html')
        out = tmpl.render(reports=reports, user=user)
        print('Rendered length:', len(out))
    except Exception as e:
        import traceback
        traceback.print_exc()
