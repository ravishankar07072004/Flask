"""Import model classes here so SQLAlchemy registers every table."""
from .user import User
from .reference import Hospital, Plan, Policy, Member
from .claim import Claim, ClaimDocument, ClaimHistory, Settlement

__all__ = ["User", "Hospital", "Plan", "Policy", "Member", "Claim", "ClaimDocument", "ClaimHistory", "Settlement"]
