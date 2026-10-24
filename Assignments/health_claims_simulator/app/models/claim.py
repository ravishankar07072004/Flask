"""Claims, checklist metadata, immutable status history, and simulated payouts."""
from datetime import datetime
from app.extensions import db


class Claim(db.Model):
    """A fictional claim moving through the permitted state machine."""
    __tablename__ = "claims"
    id = db.Column(db.Integer, primary_key=True)
    policy_id = db.Column(db.Integer, db.ForeignKey("policies.id"), nullable=False, index=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=False)
    hospital_id = db.Column(db.Integer, db.ForeignKey("hospitals.id"), nullable=False)
    claim_type = db.Column(db.Enum("cashless", "reimbursement", name="claim_types"), nullable=False)
    treatment_type = db.Column(db.Enum("inpatient", "daycare", name="treatment_types"), nullable=False)
    admission_date = db.Column(db.Date, nullable=False)
    discharge_date = db.Column(db.Date, nullable=False)
    requested_amount_inr = db.Column(db.Numeric(12, 2), nullable=False)
    eligible_amount_inr = db.Column(db.Numeric(12, 2), nullable=True)
    status = db.Column(db.Enum("draft", "submitted", "hospital_check", "policy_check", "in_review", "more_info", "approved", "rejected", "paid", name="claim_statuses"), nullable=False, default="draft", index=True)
    description = db.Column(db.String(500), nullable=False, default="")
    decision_reason = db.Column(db.String(1000), nullable=True)
    officer_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    policy = db.relationship("Policy", back_populates="claims")
    member = db.relationship("Member", back_populates="claims")
    hospital = db.relationship("Hospital", back_populates="claims")
    officer = db.relationship("User", foreign_keys=[officer_user_id])
    creator = db.relationship("User", foreign_keys=[created_by_user_id])
    documents = db.relationship("ClaimDocument", back_populates="claim", cascade="all, delete-orphan")
    history = db.relationship("ClaimHistory", back_populates="claim", cascade="all, delete-orphan", order_by="ClaimHistory.created_at")
    settlement = db.relationship("Settlement", back_populates="claim", uselist=False)


class ClaimDocument(db.Model):
    """Checklist metadata only; the simulator does not store medical files."""
    __tablename__ = "claim_documents"
    id = db.Column(db.Integer, primary_key=True)
    claim_id = db.Column(db.Integer, db.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True)
    document_type = db.Column(db.Enum("hospital_bill", "discharge_summary", name="document_types"), nullable=False)
    checklist_status = db.Column(db.Enum("missing", "received", name="checklist_statuses"), nullable=False, default="missing")
    claim = db.relationship("Claim", back_populates="documents")
    __table_args__ = (db.UniqueConstraint("claim_id", "document_type", name="uq_claim_document_type"),)


class ClaimHistory(db.Model):
    """Auditable status event with actor, previous state, next state and note."""
    __tablename__ = "claim_history"
    id = db.Column(db.Integer, primary_key=True)
    claim_id = db.Column(db.Integer, db.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    from_status = db.Column(db.String(30), nullable=True)
    to_status = db.Column(db.String(30), nullable=False)
    note = db.Column(db.String(1000), nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    actor = db.relationship("User")
    claim = db.relationship("Claim", back_populates="history")


class Settlement(db.Model):
    """A simulated payout record; it never transfers real money."""
    __tablename__ = "settlements"
    id = db.Column(db.Integer, primary_key=True)
    claim_id = db.Column(db.Integer, db.ForeignKey("claims.id"), nullable=False, unique=True)
    payee_type = db.Column(db.Enum("hospital", "policyholder", name="payee_types"), nullable=False)
    amount_inr = db.Column(db.Numeric(12, 2), nullable=False)
    recorded_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    recorded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    recorded_by = db.relationship("User")
    claim = db.relationship("Claim", back_populates="settlement")
