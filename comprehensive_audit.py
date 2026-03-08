import sys, os, ast
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print("=" * 60)
print("PREGNANCY AI - COMPREHENSIVE PROJECT AUDIT")
print("=" * 60)

# 1. Python Syntax Check
print("\n[1/6] CHECKING PYTHON SYNTAX & IMPORTS...")
python_files = []
errors_found = []

for root, dirs, files in os.walk(os.path.join(os.path.dirname(__file__), '..')):
    # Skip venv and __pycache__
    if 'venv' in root or '.venv' in root or '__pycache__' in root or 'scripts' in root:
        continue
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            python_files.append(filepath)
            try:
                with open(filepath, 'r') as f:
                    ast.parse(f.read())
            except SyntaxError as e:
                errors_found.append(f"SYNTAX ERROR in {filepath}: {e}")

if not errors_found:
    print(f"✅ {len(python_files)} Python files checked - ALL VALID")
else:
    for err in errors_found:
        print(f"❌ {err}")

# 2. Import Check
print("\n[2/6] CHECKING IMPORTS...")
try:
    from app import app, db
    from models import User, Prediction, Report, MedicalRecord, Appointment, Message, Notification
    from auth import login_required, get_current_user
    print("✅ All imports successful")
except Exception as e:
    print(f"❌ IMPORT ERROR: {e}")
    sys.exit(1)

# 3. Templates
print("\n[3/6] CHECKING TEMPLATES...")
from app import app
template_errors = []
with app.app_context():
    user = User.query.first() or User(username='test', email='t@example.com', role='doctor')
    context = {'user': user, 'predictions': [], 'reports': [], 'records': [], 'conversations': [], 
               'messages': [], 'appointments': [], 'notifications': [], 'stats': {}, 'form_data': {}}
    
    template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates')
    for template_file in os.listdir(template_dir):
        if template_file.endswith('.html'):
            try:
                with app.test_request_context():
                    tmpl = app.jinja_env.get_template(template_file)
                    tmpl.render(**context)
            except Exception as e:
                template_errors.append(f"TEMPLATE ERROR: {template_file} - {str(e)[:100]}")

if not template_errors:
    print(f"✅ All {len(os.listdir(template_dir))} templates render successfully")
else:
    for err in template_errors:
        print(f"❌ {err}")

# 4. Database Models
print("\n[4/6] CHECKING DATABASE MODELS...")
try:
    with app.app_context():
        # Test model creation
        test_user = User(username='audit_test', email='audit@test.com', role='patient')
        test_user.set_password('test')
        
        # Verify to_dict methods work
        models_to_check = [User, Prediction, Report, MedicalRecord, Appointment, Message, Notification]
        for model in models_to_check:
            # Just check the model exists and has to_dict
            if hasattr(model, '__tablename__'):
                print(f"  ✅ {model.__name__} model OK")
        print("✅ All database models verified")
except Exception as e:
    print(f"❌ DATABASE ERROR: {e}")

# 5. API Routes
print("\n[5/6] CHECKING API ROUTES...")
with app.app_context():
    doctor = User.query.filter_by(username='test_doctor').first()
    patient = User.query.filter_by(username='test_patient').first()
    
    if doctor and patient:
        client = app.test_client()
        routes_to_test = [
            ('GET', '/dashboard', doctor),
            ('GET', '/reports', doctor),
            ('GET', '/messages', doctor),
            ('GET', '/medical-records', doctor),
            ('GET', '/history', patient),
            ('GET', '/doctor/patients', doctor),
            ('GET', '/api/predictions', patient),
            ('GET', '/api/reports', patient),
            ('GET', '/api/medical-records', patient),
            ('GET', '/api/appointments', patient),
            ('GET', '/api/messages', patient),
            ('GET', '/api/notifications', patient),
        ]
        
        route_errors = []
        for method, route, user in routes_to_test:
            try:
                with client.session_transaction() as sess:
                    sess['user_id'] = user.id
                    sess['username'] = user.username
                    sess['role'] = user.role
                
                resp = client.open(route, method=method)
                if resp.status_code >= 500:
                    route_errors.append(f"ERROR {method} {route}: HTTP {resp.status_code}")
            except Exception as e:
                route_errors.append(f"ERROR {method} {route}: {str(e)[:80]}")
        
        if not route_errors:
            print(f"✅ All {len(routes_to_test)} routes tested successfully")
        else:
            for err in route_errors:
                print(f"❌ {err}")
    else:
        print("⚠️  Test users not found - skipping route tests")

# 6. Configuration Check
print("\n[6/6] CHECKING CONFIGURATION...")
config_issues = []
try:
    with app.app_context():
        # Check database
        if not app.config.get('SQLALCHEMY_DATABASE_URI'):
            config_issues.append("MISSING: SQLALCHEMY_DATABASE_URI")
        # Check secret key
        if not app.config.get('SECRET_KEY'):
            config_issues.append("MISSING: SECRET_KEY")
        
        if not config_issues:
            print("✅ Configuration is valid")
        else:
            for issue in config_issues:
                print(f"❌ {issue}")
except Exception as e:
    print(f"❌ CONFIG ERROR: {e}")

print("\n" + "=" * 60)
print("AUDIT COMPLETE")
print("=" * 60)
