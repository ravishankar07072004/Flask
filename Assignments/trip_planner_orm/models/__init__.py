"""Import all model classes so SQLAlchemy registers every table."""
from .user import User
from .trip import Trip
from .activity import Activity
from .place_suggestion import PlaceSuggestion

__all__ = ['User', 'Trip', 'Activity', 'PlaceSuggestion']

