"""Public Explore place suggestion model."""
from extensions import db
from .base import BaseModel


class PlaceSuggestion(BaseModel):
    """Represent a public place suggestion submitted to Explore."""
    __tablename__ = 'place_suggestions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    destination = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(60), nullable=False)
    description = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp())

    creator = db.relationship('User', back_populates='suggestions')
