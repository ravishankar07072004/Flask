"""User database model."""
from extensions import db
from .base import BaseModel


class User(BaseModel):
    """Represent a registered user account."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp())

    trips = db.relationship('Trip', back_populates='owner', cascade='all, delete-orphan', passive_deletes=True)
    suggestions = db.relationship('PlaceSuggestion', back_populates='creator')
