from flask import session, redirect, url_for, render_template
from functools import wraps
from models import User

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

def is_doctor(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user or user.role not in ['doctor', 'admin']:
            return render_template('error.html', message='Access Denied. Doctor access required.'), 403
        return f(*args, **kwargs)
    return decorated_function

def is_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user or user.role != 'admin':
            return render_template('error.html', message='Access Denied. Admin access required.'), 403
        return f(*args, **kwargs)
    return decorated_function
