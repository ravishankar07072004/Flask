"""Application factory for the Health Insurance Claims Processing Simulator."""
import os
from dotenv import load_dotenv
from flask import Flask, redirect, url_for
from flask_login import current_user

# Load environment variables before Config reads them.
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_BASE_DIR, ".env"))

from app.config import Config
from app.extensions import db, login_manager, csrf


def create_app(test_config=None):
    """Build and configure the Flask app, extensions, routes and CLI commands."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(base_dir, ".env"))
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.claims import claims_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(claims_bp, url_prefix="/claims")

    @app.cli.command("init-db")
    def init_db_command():
        """Create all tables defined by the SQLAlchemy models."""
        with app.app_context():
            db.create_all()
        print("Database tables created. Run `flask --app run.py seed-demo` next.")

    @app.cli.command("seed-demo")
    def seed_demo_command():
        """Seed demo logins and import synthetic reference data from the bundled CSVs."""
        from app.seed import seed_demo
        with app.app_context():
            seed_demo()
        print("Demo data seeded. Demo passwords are documented in README.md; change them locally.")

    return app
