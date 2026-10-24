"""Claim list, creation, detail, review decisions and simulated settlement."""
from datetime import date
from decimal import Decimal, InvalidOperation
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_
from app.extensions import db
from app.models import Claim, ClaimDocument, ClaimHistory, Hospital, Member, Policy, Settlement
from app.services import can_view_claim, change_status, create_default_checklist, remaining_cover, calculate_payout

claims_bp = Blueprint("claims", __name__)


def role_required(*roles):
    """Route decorator that enforces server-side role authorization."""
    from functools import wraps
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


@claims_bp.route("/")
@login_required
def list_claims():
    """List only authorized claims, with combinable search and filters."""
    query = Claim.query
    if current_user.role == "policyholder":
        query = query.join(Policy).filter(Policy.holder_user_id == current_user.id)
    elif current_user.role == "hospital":
        query = query.filter(Claim.claim_type == "cashless", Claim.hospital_id == current_user.hospital_id)
    elif current_user.role == "claims_officer":
        query = query.filter(Claim.status != "draft")
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    claim_type = request.args.get("type", "").strip()
    hospital_id = request.args.get("hospital_id", "").strip()
    if search:
        query = query.join(Member).filter(or_(Member.display_name.ilike(f"%{search}%"), Claim.id.cast(db.String).ilike(f"%{search}%")))
    if status in {"draft", "submitted", "hospital_check", "policy_check", "in_review", "more_info", "approved", "rejected", "paid"}:
        query = query.filter(Claim.status == status)
    if claim_type in {"cashless", "reimbursement"}:
        query = query.filter(Claim.claim_type == claim_type)
    if hospital_id.isdigit():
        query = query.filter(Claim.hospital_id == int(hospital_id))
    claims = query.order_by(Claim.created_at.desc()).all()
    return render_template("claims/list.html", claims=claims, hospitals=Hospital.query.order_by(Hospital.name).all(), q=search, status=status, claim_type=claim_type, hospital_id=hospital_id)


@claims_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_claim():
    """Create a draft or submitted claim after validating scope and policy/member links."""
    if current_user.role not in {"policyholder", "hospital"}:
        abort(403)
    if request.method == "POST":
        try:
            policy_value = request.form.get("policy_id", "").strip().lstrip("#").strip()
            policy_id = int(policy_value)
            member_id = int(request.form.get("member_id", ""))
            hospital_id = int(request.form.get("hospital_id", ""))
            requested = Decimal(request.form.get("requested_amount_inr", "0"))
            admission = date.fromisoformat(request.form.get("admission_date", ""))
            discharge = date.fromisoformat(request.form.get("discharge_date", ""))
        except (ValueError, InvalidOperation):
            flash("Enter valid policy, member, hospital, dates and amount.", "danger")
            return redirect(url_for("claims.new_claim"))
        policy = db.session.get(Policy, policy_id)
        member = db.session.get(Member, member_id)
        hospital = db.session.get(Hospital, hospital_id)
        claim_type = request.form.get("claim_type", "")
        treatment_type = request.form.get("treatment_type", "")
        submit_now = request.form.get("action") == "submit"
        errors = []
        if not policy or not member or member.policy_id != policy.id:
            errors.append("The selected member must belong to the selected policy.")
        if current_user.role == "policyholder" and (not policy or policy.holder_user_id != current_user.id):
            errors.append("You can create claims only under your own policy.")
        if current_user.role == "hospital":
            claim_type = "cashless"
            if not hospital or hospital.id != current_user.hospital_id:
                errors.append("A hospital desk can submit only for its own hospital.")
        if current_user.role == "policyholder" and claim_type != "reimbursement":
            errors.append("Policyholders can submit reimbursement claims only.")
        if current_user.role == "hospital" and claim_type != "cashless":
            errors.append("Hospital desk accounts can submit cashless claims only.")
        if claim_type not in {"cashless", "reimbursement"}:
            errors.append("Choose a valid claim type.")
        if claim_type == "cashless" and hospital and not hospital.network_status:
            errors.append("Cashless claims require a network hospital.")
        if not hospital:
            errors.append("Choose a listed hospital.")
        if treatment_type not in {"inpatient", "daycare"}:
            errors.append("Choose a valid treatment type.")
        if requested <= 0:
            errors.append("Requested amount must be greater than zero.")
        if discharge < admission or admission > date.today():
            errors.append("Dates are invalid; admission cannot be in the future.")
        if policy and (admission < policy.start_date or admission > policy.end_date or policy.status != "active"):
            errors.append("The policy must be active for the admission date.")
        if policy and not policy.plan.covers(treatment_type):
            errors.append("This plan does not list the selected treatment type.")
        if errors:
            for error in errors:
                flash(error, "danger")
            return redirect(url_for("claims.new_claim"))
        claim = Claim(policy=policy, member=member, hospital=hospital, claim_type=claim_type,
                      treatment_type=treatment_type, admission_date=admission, discharge_date=discharge,
                      requested_amount_inr=requested, description=request.form.get("description", "").strip(),
                      status="draft", created_by_user_id=current_user.id)
        db.session.add(claim)
        db.session.flush()
        create_default_checklist(claim)
        # Initial claim history is written by trg_claim_after_insert in MySQL.
        if submit_now:
            change_status(claim, "submitted", current_user, "Submitted by creator")
        db.session.commit()
        flash(f"Claim #{claim.id} created successfully.", "success")
        return redirect(url_for("claims.detail", claim_id=claim.id))

    policies = Policy.query.filter_by(holder_user_id=current_user.id).all() if current_user.role == "policyholder" else Policy.query.filter(Policy.status == "active").all()
    members = Member.query.join(Policy).filter(Policy.holder_user_id == current_user.id).all() if current_user.role == "policyholder" else Member.query.join(Policy).filter(Policy.status == "active").all()
    hospitals = Hospital.query.filter_by(id=current_user.hospital_id).all() if current_user.role == "hospital" else Hospital.query.order_by(Hospital.name).all()
    return render_template("claims/new.html", policies=policies, members=members, hospitals=hospitals, now_date=date.today().isoformat())


@claims_bp.route("/<int:claim_id>")
@login_required
def detail(claim_id):
    """Show claim details only after a server-side ownership check."""
    claim = db.get_or_404(Claim, claim_id)
    if not can_view_claim(current_user, claim):
        abort(403)
    return render_template("claims/detail.html", claim=claim, remaining=remaining_cover(claim.policy))


@claims_bp.route("/<int:claim_id>/submit", methods=["POST"])
@login_required
def submit(claim_id):
    """Submit a draft or respond to a more-information request."""
    claim = db.get_or_404(Claim, claim_id)
    # Permit the policyholder who owns the policy or the hospital desk for this
    # cashless claim to submit it. This also makes imported demo claims usable
    # when their historical creator ID does not match the seeded history actor.
    is_policyholder_owner = current_user.role == "policyholder" and claim.policy.holder_user_id == current_user.id
    is_claim_hospital = current_user.role == "hospital" and claim.claim_type == "cashless" and current_user.hospital_id == claim.hospital_id
    is_creator = claim.created_by_user_id == current_user.id
    if not can_view_claim(current_user, claim) or not (is_creator or is_policyholder_owner or is_claim_hospital):
        abort(403)
    try:
        if claim.status == "draft":
            if not claim.policy or not claim.member or claim.member.policy_id != claim.policy_id:
                raise ValueError("A valid policy and a member belonging to that policy are required.")
            if not claim.hospital:
                raise ValueError("A valid hospital is required.")
            if claim.requested_amount_inr is None or Decimal(claim.requested_amount_inr) <= 0:
                raise ValueError("Requested amount must be greater than zero.")
            if claim.admission_date is None or claim.admission_date > date.today():
                raise ValueError("Admission date is required and cannot be in the future.")
            if claim.discharge_date is None or claim.discharge_date < claim.admission_date:
                raise ValueError("Discharge date must be on or after the admission date.")
            if claim.policy.status != "active" or claim.admission_date < claim.policy.start_date or claim.admission_date > claim.policy.end_date:
                raise ValueError("The policy must be active and valid on the admission date.")
            if not claim.policy.plan.covers(claim.treatment_type):
                raise ValueError("The selected plan does not cover this treatment type.")
            if claim.claim_type == "cashless" and (not claim.hospital.network_status or not is_claim_hospital):
                raise ValueError("Cashless claims require an eligible network hospital desk.")
        change_status(claim, "submitted", current_user, request.form.get("note", "Submitted / information provided"))
        db.session.commit()
        flash("Claim submitted.", "success")
    except ValueError as exc:
        db.session.rollback(); flash(str(exc), "danger")
    return redirect(url_for("claims.detail", claim_id=claim.id))


@claims_bp.route("/<int:claim_id>/review", methods=["POST"])
@login_required
@role_required("claims_officer")
def review(claim_id):
    """Assign a submitted claim to the officer or record a review decision."""
    claim = db.get_or_404(Claim, claim_id)
    action = request.form.get("action", "")
    note = request.form.get("reason", "").strip()
    try:
        if action == "assign":
            if claim.status != "submitted":
                raise ValueError("Only submitted claims can be assigned.")
            if claim.officer_user_id not in (None, current_user.id):
                raise ValueError("This claim is already assigned to another officer.")
            claim.officer_user_id = current_user.id
            if claim.claim_type == "cashless":
                # Cashless claims are submitted by an authenticated hospital desk;
                # skip the separate hospital-check state and proceed to policy verification.
                if not claim.hospital or not claim.hospital.name.strip() or not claim.hospital.network_status:
                    raise ValueError("Cashless claims require a valid eligible network hospital.")
                change_status(claim, "policy_check", current_user,
                              "Assigned to officer; hospital desk and network eligibility verified")
            else:
                # Reimbursement claims are submitted by the policyholder; skip policy_check
                # and start substantive review, where policy validity is enforced before approval.
                change_status(claim, "in_review", current_user,
                              "Assigned to officer; reimbursement proceeds directly to claim review")
        elif claim.officer_user_id != current_user.id:
            raise ValueError("This claim must be assigned to you before verification or review.")
        elif action == "hospital_valid":
            if claim.status != "hospital_check":
                raise ValueError("Hospital verification is only available during hospital check.")
            if not claim.hospital or not claim.hospital.name.strip() or not claim.hospital.network_status:
                raise ValueError("Hospital is invalid or ineligible. Reject with a written reason.")
            change_status(claim, "in_review", current_user, note or "Hospital identity, registration and eligibility verified; claim moved to review")
        elif action == "hospital_invalid":
            if claim.status != "hospital_check" or not note:
                raise ValueError("A written reason is required to reject an invalid hospital.")
            claim.decision_reason = note
            claim.eligible_amount_inr = Decimal("0.00")
            change_status(claim, "rejected", current_user, note)
        elif action == "policy_valid":
            if claim.status != "policy_check":
                raise ValueError("Policy verification is only available during policy check.")
            policy = claim.policy
            if not policy or policy.status != "active" or claim.admission_date < policy.start_date or claim.admission_date > policy.end_date or not policy.plan.covers(claim.treatment_type):
                raise ValueError("Policy is invalid or ineligible. Reject with a written reason.")
            change_status(claim, "in_review", current_user, note or "Policyholder identity, policy validity, dates and coverage verified")
        elif action == "policy_invalid":
            if claim.status != "policy_check" or not note:
                raise ValueError("A written reason is required to reject an invalid policy.")
            claim.decision_reason = note
            claim.eligible_amount_inr = Decimal("0.00")
            change_status(claim, "rejected", current_user, note)
        elif claim.status != "in_review":
            raise ValueError("Complete hospital and policy verification before reviewing the claim.")
        elif action == "more_info":
            if not note:
                raise ValueError("Provide a reason or requested information.")
            change_status(claim, "more_info", current_user, note)
        elif action == "reject":
            if not note:
                raise ValueError("A written rejection reason is required.")
            claim.eligible_amount_inr = Decimal("0.00")
            claim.decision_reason = note
            change_status(claim, "rejected", current_user, note)
        elif action == "approve":
            if not note:
                raise ValueError("A written decision reason is required.")
            eligible = Decimal(request.form.get("eligible_amount_inr", "0"))
            available = remaining_cover(claim.policy)
            if eligible <= 0 or eligible > Decimal(claim.requested_amount_inr) or eligible > available:
                raise ValueError(f"Eligible amount must be > 0, no more than requested, and within available cover (₹{available}).")
            if claim.policy.status != "active":
                raise ValueError("The policy is not active.")
            if not claim.policy.plan.covers(claim.treatment_type):
                raise ValueError("The plan does not cover this treatment type.")
            if claim.admission_date < claim.policy.start_date or claim.admission_date > claim.policy.end_date:
                raise ValueError("The admission date is outside the policy dates.")
            claim.eligible_amount_inr = eligible
            claim.decision_reason = note
            change_status(claim, "approved", current_user, note)
        else:
            raise ValueError("Unknown review action.")
        db.session.commit()
        flash("Claim updated.", "success")
    except (ValueError, InvalidOperation) as exc:
        db.session.rollback(); flash(str(exc), "danger")
    return redirect(url_for("claims.detail", claim_id=claim.id))


@claims_bp.route("/<int:claim_id>/documents", methods=["POST"])
@login_required
def update_documents(claim_id):
    """Update checklist metadata for the claim creator on a draft or more-info claim."""
    claim = db.get_or_404(Claim, claim_id)
    if not can_view_claim(current_user, claim) or claim.created_by_user_id != current_user.id or claim.status not in {"draft", "more_info"}:
        abort(403)
    for doc in claim.documents:
        value = request.form.get(doc.document_type, "missing")
        if value in {"missing", "received"}:
            doc.checklist_status = value
    db.session.add(ClaimHistory(claim=claim, actor_user_id=current_user.id, from_status=claim.status, to_status=claim.status, note="Document checklist updated"))
    db.session.commit()
    flash("Checklist updated.", "success")
    return redirect(url_for("claims.detail", claim_id=claim.id))


@claims_bp.route("/<int:claim_id>/settle", methods=["POST"])
@login_required
@role_required("admin")
def settle(claim_id):
    """Record one simulated payout for an approved claim."""
    claim = db.get_or_404(Claim, claim_id)
    try:
        if claim.status != "approved" or claim.settlement:
            raise ValueError("Only an approved claim without a settlement can be paid.")
        if claim.eligible_amount_inr is None:
            raise ValueError("An eligible amount is required before settlement.")
        payout = calculate_payout(claim.eligible_amount_inr, claim.policy.plan)
        if payout <= 0:
            raise ValueError("Calculated simulated payout must be greater than zero.")
        payee_type = "hospital" if claim.claim_type == "cashless" else "policyholder"
        db.session.add(Settlement(claim=claim, payee_type=payee_type, amount_inr=payout, recorded_by_user_id=current_user.id))
        change_status(claim, "paid", current_user, f"Simulated payout ₹{payout} recorded for {payee_type}")
        db.session.commit()
        flash(f"Simulated settlement recorded: ₹{payout}. No real money was transferred.", "success")
    except ValueError as exc:
        db.session.rollback(); flash(str(exc), "danger")
    return redirect(url_for("claims.detail", claim_id=claim.id))
