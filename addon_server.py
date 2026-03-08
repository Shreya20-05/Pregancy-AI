"""
Sidecar entrypoint that keeps the original project unchanged.

Run this file to start PregnancyAI with addon modules enabled.
"""

from app import app
from models import db

# Ensure addon models are imported so create_all creates their tables.
from addons import models as addon_models  # noqa: F401
from addons.routes import addon_bp


def register_addons(flask_app):
    if addon_bp.name not in flask_app.blueprints:
        flask_app.register_blueprint(addon_bp)


register_addons(app)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

