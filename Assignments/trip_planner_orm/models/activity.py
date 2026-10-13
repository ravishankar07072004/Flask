"""Trip activity database model."""
from decimal import Decimal
from extensions import db
from .base import BaseModel


class Activity(BaseModel):
    """Represent an activity associated with a trip."""
    __tablename__ = 'activities'

    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trips.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    activity_date = db.Column(db.Date, nullable=False)
    activity_time = db.Column(db.Time, nullable=True)
    category = db.Column(db.String(60), nullable=False)
    place = db.Column(db.String(180), nullable=False)
    cost = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'), server_default='0.00')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp())

    trip = db.relationship('Trip', back_populates='activities')
    __table_args__ = (db.Index('idx_activity_trip_date', 'trip_id', 'activity_date'),)
