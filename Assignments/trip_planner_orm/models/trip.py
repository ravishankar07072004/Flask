"""Trip database model."""
from decimal import Decimal
from extensions import db
from .base import BaseModel


class Trip(BaseModel):
    """Represent a trip owned by a registered user."""
    __tablename__ = 'trips'

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    destination = db.Column(db.String(150), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    budget = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'), server_default='0.00')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp())

    owner = db.relationship('User', back_populates='trips')
    activities = db.relationship(
        'Activity', back_populates='trip', cascade='all, delete-orphan', passive_deletes=True,
        order_by='(Activity.activity_date, Activity.activity_time, Activity.id)'
    )

    # Values populated per request for the My Trips summary template.
    activity_count = 0
    total_cost = Decimal('0.00')
