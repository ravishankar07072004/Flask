"""Shared Flask extensions initialized by the application factory."""
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

# Models inherit from SQLAlchemy's declarative base through this extension.
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
