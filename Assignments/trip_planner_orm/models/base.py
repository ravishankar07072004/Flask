"""Base class and common behavior for ORM models."""
from extensions import db


class DictAccessMixin:
    """Allow templates to access model fields using row['field'] syntax."""
    def __getitem__(self, key):
        """Provide dictionary-style access to a model attribute."""
        return getattr(self, key)

    def get(self, key, default=None):
        """Return a model attribute or a default value when it is missing."""
        return getattr(self, key, default)


class BaseModel(DictAccessMixin, db.Model):
    """Abstract base class shared by all application models."""
    __abstract__ = True
