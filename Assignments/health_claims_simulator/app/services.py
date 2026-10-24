"""Business rules shared by routes; never trust browser-supplied role or status."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from app.extensions import db
from app.models import Claim, ClaimHistory, ClaimDocument, Settlement

ALLOWED_TRANSITIONS = {
    "draft": {"submitted"},
    "submitted": {"hospital_check", "policy_check", "in_review"},
    "hospital_check": {"policy_check", "in_review", "rejected"},
    "policy_check": {"in_review", "rejected"},
    "in_review": {"more_info", "approved", "rejected"},
    "more_info": {"submitted"},
    "approved": {"paid"},
    "rejected": set(),
    "paid": set(),
}


def can_view_claim(user, claim):
    """Enforce record-level scope for each role."""
    if user.role == "admin":
        return True
    if user.role == "claims_officer":
        return claim.status != "draft"
    if user.role == "policyholder":
        return claim.policy.holder_user_id == user.id
    if user.role == "hospital":
        return claim.claim_type == "cashless" and user.hospital_id == claim.hospital_id
    return False


def change_status(claim, new_status, actor, note=""):
    """Validate a state transition and persist its audit event in the same transaction."""
    if new_status not in ALLOWED_TRANSITIONS.get(claim.status, set()):
        raise ValueError(f"Invalid transition: {claim.status} → {new_status}.")
    old_status = claim.status
    claim.status = new_status
    db.session.add(ClaimHistory(claim=claim, actor_user_id=actor.id,
                                from_status=old_status, to_status=new_status, note=note.strip()))


def remaining_cover(policy):
    """Return annual limit less simulated payouts in the policy's current coverage year."""
    start_year = policy.start_date.year
    year_end = date(start_year, 12, 31)
    paid_total = db.session.query(db.func.coalesce(db.func.sum(Settlement.amount_inr), 0)) \
        .join(Claim, Settlement.claim_id == Claim.id) \
        .filter(Claim.policy_id == policy.id,
                Claim.admission_date >= policy.start_date,
                Claim.admission_date <= min(policy.end_date, year_end)).scalar()
    return max(Decimal("0.00"), Decimal(policy.plan.annual_limit_inr) - Decimal(str(paid_total)))


def calculate_payout(eligible_amount, plan):
    """Apply the BRD's fictional deductible/co-pay formula using Decimal arithmetic."""
    eligible = Decimal(str(eligible_amount))
    deductible = Decimal(plan.deductible_inr)
    copay = Decimal(plan.copay_percent) / Decimal("100")
    payout = (eligible - min(eligible, deductible)) * (Decimal("1") - copay)
    return payout.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def create_default_checklist(claim):
    """Create checklist metadata rows for both required document categories."""
    for kind in ("hospital_bill", "discharge_summary"):
        if not any(doc.document_type == kind for doc in claim.documents):
            db.session.add(ClaimDocument(claim=claim, document_type=kind, checklist_status="missing"))
