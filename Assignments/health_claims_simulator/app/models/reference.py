"""Reference data models: hospitals, plans, policies and covered members."""
from app.extensions import db


class Hospital(db.Model):
    """A fictional hospital, optionally eligible for cashless claims."""
    __tablename__ = "hospitals"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    network_status = db.Column(db.Boolean, nullable=False, default=False)
    users = db.relationship("User", back_populates="hospital")
    claims = db.relationship("Claim", back_populates="hospital")


class Plan(db.Model):
    """A fictional plan and its simplified classroom coverage rules."""
    __tablename__ = "plans"
    id = db.Column(db.Integer, primary_key=True)
    plan_name = db.Column(db.String(100), nullable=False)
    covered_treatment_types = db.Column(db.String(100), nullable=False)
    annual_limit_inr = db.Column(db.Numeric(12, 2), nullable=False)
    deductible_inr = db.Column(db.Numeric(12, 2), nullable=False)
    copay_percent = db.Column(db.Numeric(5, 2), nullable=False)
    policies = db.relationship("Policy", back_populates="plan")

    def covers(self, treatment_type: str) -> bool:
        """Check whether this plan lists the requested treatment type."""
        return treatment_type in self.covered_treatment_types.split("|")


class Policy(db.Model):
    """A policy held by a user and connected to one fictional plan."""
    __tablename__ = "policies"
    id = db.Column(db.Integer, primary_key=True)
    holder_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("plans.id"), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    holder = db.relationship("User", back_populates="policies", foreign_keys=[holder_user_id])
    plan = db.relationship("Plan", back_populates="policies")
    members = db.relationship("Member", back_populates="policy", cascade="all, delete-orphan")
    claims = db.relationship("Claim", back_populates="policy")


class Member(db.Model):
    """A person covered under one policy; names in this project are synthetic."""
    __tablename__ = "members"
    id = db.Column(db.Integer, primary_key=True)
    policy_id = db.Column(db.Integer, db.ForeignKey("policies.id"), nullable=False, index=True)
    display_name = db.Column(db.String(120), nullable=False)
    relationship = db.Column(db.String(40), nullable=False, default="other")
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    user = db.relationship("User", foreign_keys=[user_id])
    policy = db.relationship("Policy", back_populates="members")
    claims = db.relationship("Claim", back_populates="member")
