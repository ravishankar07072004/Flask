"""Dashboard, policy views and reports."""
from datetime import date
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash
from sqlalchemy import func
from app.extensions import db
from app.models import Claim, ClaimHistory, Policy, Settlement, User, Hospital, Plan, Member

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Send visitors to login or their dashboard."""
    from flask import redirect, url_for
    return redirect(url_for("main.dashboard" if current_user.is_authenticated else "auth.login"))


@main_bp.route("/dashboard")
@login_required
def dashboard():
    """Show role-scoped counts and claim totals."""
    claims_query = Claim.query
    policies_query = Policy.query
    if current_user.role == "policyholder":
        claims_query = claims_query.join(Policy).filter(Policy.holder_user_id == current_user.id)
        policies_query = policies_query.filter(Policy.holder_user_id == current_user.id)
    elif current_user.role == "hospital":
        claims_query = claims_query.filter(Claim.claim_type == "cashless", Claim.hospital_id == current_user.hospital_id)
        policies_query = policies_query.filter(Policy.id == -1)
    counts = dict(db.session.query(Claim.status, func.count(Claim.id)).filter(Claim.id.in_(claims_query.with_entities(Claim.id))).group_by(Claim.status).all())
    requested_total = db.session.query(func.coalesce(func.sum(Claim.requested_amount_inr), 0)).filter(Claim.id.in_(claims_query.with_entities(Claim.id))).scalar()
    paid_total = db.session.query(func.coalesce(func.sum(Settlement.amount_inr), 0)).join(Claim).filter(Claim.id.in_(claims_query.with_entities(Claim.id))).scalar()
    recent_claims = claims_query.order_by(Claim.created_at.desc()).limit(8).all()
    return render_template("dashboard.html", counts=counts, policies=policies_query.count(),
                           requested_total=requested_total, paid_total=paid_total, recent_claims=recent_claims)


@main_bp.route("/policies")
@login_required
def policies():
    """Show policies within the logged-in user's permitted scope."""
    query = Policy.query
    if current_user.role == "policyholder":
        query = query.filter_by(holder_user_id=current_user.id)
    elif current_user.role == "hospital":
        query = query.filter(Policy.id == -1)
    return render_template("policies.html", policies=query.order_by(Policy.id).all())



def admin_required(view):
    """Restrict reference-data management to administrator accounts."""
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.role != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


@main_bp.route("/admin/manage", methods=["GET", "POST"])
@admin_required
def admin_manage():
    """Create policyholder/staff accounts and insurance policies."""
    form_type = request.form.get("form_type", "") if request.method == "POST" else ""
    users = User.query.order_by(User.display_name).all()
    holders = User.query.filter_by(role="policyholder").order_by(User.display_name).all()
    hospitals = Hospital.query.order_by(Hospital.name).all()
    plans = Plan.query.order_by(Plan.plan_name).all()

    if request.method == "POST" and form_type == "user":
        username = request.form.get("username", "").strip()
        display_name = request.form.get("display_name", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "").strip()
        hospital_id_raw = request.form.get("hospital_id", "").strip()
        allowed_roles = {"policyholder", "hospital", "claims_officer", "admin"}
        errors = []
        if not username or len(username) > 80:
            errors.append("Username is required and must be at most 80 characters.")
        if User.query.filter_by(username=username).first():
            errors.append("That username already exists.")
        if not display_name or len(display_name) > 120:
            errors.append("Display name is required and must be at most 120 characters.")
        if len(password) < 8:
            errors.append("Password must contain at least 8 characters.")
        if role not in allowed_roles:
            errors.append("Choose a valid user role.")
        linked_hospital = None
        if role == "hospital":
            try:
                linked_hospital = db.session.get(Hospital, int(hospital_id_raw))
            except (TypeError, ValueError):
                linked_hospital = None
            if linked_hospital is None:
                errors.append("Select a valid hospital for a hospital desk account.")
        if role != "hospital":
            linked_hospital = None
        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            user = User(username=username, display_name=display_name, role=role,
                        hospital_id=linked_hospital.id if linked_hospital else None)
            user.set_password(password)
            db.session.add(user)
            try:
                db.session.commit()
                flash(f"User account '{username}' created successfully.", "success")
                return redirect(url_for("main.admin_manage"))
            except IntegrityError:
                db.session.rollback()
                flash("Could not create the account. Check that the username is unique.", "danger")

    elif request.method == "POST" and form_type == "reset_password":
        user_raw = request.form.get("user_id", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        try:
            target_user = db.session.get(User, int(user_raw))
        except (TypeError, ValueError):
            target_user = None
        errors = []
        if target_user is None:
            errors.append("Select a valid user account.")
        if len(new_password) < 8:
            errors.append("New password must contain at least 8 characters.")
        if new_password != confirm_password:
            errors.append("New password and confirmation do not match.")
        if target_user is not None and target_user.id == current_user.id and new_password and current_user.check_password(new_password):
            errors.append("Choose a password different from the current password.")
        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            target_user.set_password(new_password)
            db.session.commit()
            flash(f"Password reset successfully for '{target_user.username}'.", "success")
            return redirect(url_for("main.admin_manage"))

    elif request.method == "POST" and form_type == "delete_user":
        user_raw = request.form.get("user_id", "")
        try:
            target_user = db.session.get(User, int(user_raw))
        except (TypeError, ValueError):
            target_user = None

        if target_user is None:
            flash("Select a valid user account to remove.", "danger")
        elif target_user.id == current_user.id:
            flash("You cannot remove the administrator account you are currently using.", "danger")
        elif target_user.role == "admin" and User.query.filter_by(role="admin").count() <= 1:
            flash("The last administrator account cannot be removed.", "danger")
        else:
            # Keep claims and policy audit records intact. A user referenced by
            # these records must be handled through an explicit archival workflow.
            has_policy = Policy.query.filter_by(holder_user_id=target_user.id).first() is not None
            has_created_claim = Claim.query.filter_by(created_by_user_id=target_user.id).first() is not None
            has_assigned_claim = Claim.query.filter_by(officer_user_id=target_user.id).first() is not None
            has_history = ClaimHistory.query.filter_by(actor_user_id=target_user.id).first() is not None
            has_settlement = Settlement.query.filter_by(recorded_by_user_id=target_user.id).first() is not None
            if any((has_policy, has_created_claim, has_assigned_claim, has_history, has_settlement)):
                flash(
                    f"Cannot remove '{target_user.username}' because the account is linked to policies or claim/audit records. "
                    "Keep the account to preserve the simulator's history.",
                    "danger",
                )
            else:
                username = target_user.username
                db.session.delete(target_user)
                try:
                    db.session.commit()
                    flash(f"User account '{username}' was removed successfully.", "success")
                    return redirect(url_for("main.admin_manage") + "#existing-users")
                except IntegrityError:
                    db.session.rollback()
                    flash("This account is still referenced by other records and cannot be removed.", "danger")

    elif request.method == "POST" and form_type == "plan":
        plan_name = request.form.get("plan_name", "").strip()
        treatments_raw = request.form.get("covered_treatment_types", "").strip()
        annual_raw = request.form.get("annual_limit_inr", "").strip()
        deductible_raw = request.form.get("deductible_inr", "").strip()
        copay_raw = request.form.get("copay_percent", "").strip()
        errors = []
        if not plan_name or len(plan_name) > 100:
            errors.append("Plan name is required and must be at most 100 characters.")
        if Plan.query.filter(func.lower(Plan.plan_name) == plan_name.lower()).first():
            errors.append("An insurance plan with that name already exists.")
        treatments = [item.strip() for item in treatments_raw.split(",") if item.strip()]
        if not treatments:
            errors.append("Enter at least one covered treatment type, separated by commas.")
        elif any(len(item) > 40 for item in treatments):
            errors.append("Each treatment type must be 40 characters or fewer.")
        try:
            annual_limit = float(annual_raw)
            if annual_limit <= 0:
                raise ValueError
        except (TypeError, ValueError):
            annual_limit = None
            errors.append("Annual coverage limit must be a number greater than zero.")
        try:
            deductible = float(deductible_raw)
            if deductible < 0:
                raise ValueError
        except (TypeError, ValueError):
            deductible = None
            errors.append("Deductible must be zero or greater.")
        try:
            copay = float(copay_raw)
            if not 0 <= copay <= 100:
                raise ValueError
        except (TypeError, ValueError):
            copay = None
            errors.append("Copay must be between 0 and 100 percent.")
        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            new_plan = Plan(
                plan_name=plan_name,
                covered_treatment_types="|".join(dict.fromkeys(treatments)),
                annual_limit_inr=annual_limit,
                deductible_inr=deductible,
                copay_percent=copay,
            )
            db.session.add(new_plan)
            try:
                db.session.commit()
                flash(f"Insurance plan '{new_plan.plan_name}' created successfully.", "success")
                return redirect(url_for("main.admin_manage") + "#create-plan")
            except IntegrityError:
                db.session.rollback()
                flash("Could not create the insurance plan. Please check the entered details.", "danger")

    elif request.method == "POST" and form_type == "policy":
        holder_mode = request.form.get("holder_mode", "existing").strip()
        holder_raw = request.form.get("holder_user_id", "")
        new_holder_name = request.form.get("new_holder_name", "").strip()
        new_holder_username = request.form.get("new_holder_username", "").strip()
        new_holder_password = request.form.get("new_holder_password", "")
        plan_raw = request.form.get("plan_id", "")
        start_raw = request.form.get("start_date", "")
        end_raw = request.form.get("end_date", "")
        status = request.form.get("status", "active").strip()
        member_user_ids_raw = request.form.getlist("member_user_id[]")
        member_user_ids = []
        errors = []
        holder = None
        create_holder = holder_mode == "new"
        if holder_mode == "existing":
            try:
                holder = db.session.get(User, int(holder_raw))
            except (TypeError, ValueError):
                holder = None
        elif create_holder:
            if not new_holder_name or len(new_holder_name) > 120:
                errors.append("New policyholder name is required and must be at most 120 characters.")
            if not new_holder_username or len(new_holder_username) > 80:
                errors.append("New username is required and must be at most 80 characters.")
            if new_holder_username and User.query.filter_by(username=new_holder_username).first():
                existing_user = User.query.filter_by(username=new_holder_username).first()
                if existing_user.role == "policyholder":
                    holder = existing_user
                    create_holder = False
                    flash("That username already belongs to a policyholder. The existing account will be used.", "info")
                else:
                    errors.append("That username already exists with a different role. Choose another username or select the existing policyholder.")
            if create_holder and len(new_holder_password) < 8:
                errors.append("New policyholder password must contain at least 8 characters.")
        else:
            errors.append("Choose whether to select an existing policyholder or create a new one.")
        try:
            plan = db.session.get(Plan, int(plan_raw))
        except (TypeError, ValueError):
            plan = None
        try:
            start_date = date.fromisoformat(start_raw)
            end_date = date.fromisoformat(end_raw)
        except (TypeError, ValueError):
            start_date = end_date = None
        if holder_mode == "existing" and (holder is None or holder.role != "policyholder"):
            errors.append("Select an existing policyholder account.")
        if holder is not None and holder.role != "policyholder":
            errors.append("The selected username is not a policyholder account.")
        if plan is None:
            errors.append("Select an existing insurance plan.")
        if start_date is None or end_date is None:
            errors.append("Enter valid start and end dates.")
        elif end_date < start_date:
            errors.append("End date must be on or after the start date.")
        if status not in {"active", "inactive", "expired"}:
            errors.append("Choose a valid policy status.")
        # Members must be existing policyholder accounts, not free-text dependent records.
        for raw_member_id in member_user_ids_raw:
            try:
                member_user_id = int(raw_member_id)
                member_user = db.session.get(User, member_user_id)
            except (TypeError, ValueError):
                member_user = None
            if member_user is None or member_user.role != "policyholder":
                errors.append("Choose valid existing policyholder accounts as policy members.")
                continue
            if holder is not None and member_user.id == holder.id:
                errors.append("The policyholder is already covered as the holder and cannot also be selected as a member.")
                continue
            if member_user_id not in member_user_ids:
                member_user_ids.append(member_user_id)
        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            try:
                if create_holder:
                    holder = User(username=new_holder_username, display_name=new_holder_name, role="policyholder")
                    holder.set_password(new_holder_password)
                    db.session.add(holder)
                    db.session.flush()  # Obtain the user ID before creating the policy.
                policy = Policy(holder_user_id=holder.id, plan_id=plan.id,
                                start_date=start_date, end_date=end_date, status=status)
                for member_user_id in member_user_ids:
                    member_user = db.session.get(User, member_user_id)
                    policy.members.append(Member(user_id=member_user.id, display_name=member_user.display_name, relationship="other"))
                db.session.add(policy)
                db.session.commit()
                flash(f"Policy #{policy.id} created successfully for {holder.display_name}.", "success")
                return redirect(url_for("main.policies"))
            except IntegrityError:
                db.session.rollback()
                flash("Could not create the policy. Check that the username is unique and the policy details are valid.", "danger")
    elif request.method == "POST":
        flash("Choose a valid administrator action.", "danger")

    return render_template("admin_manage.html", users=users, holders=holders,
                           hospitals=hospitals, plans=plans, today=date.today().isoformat())


@main_bp.route("/reports")
@login_required
def reports():
    """Show role-scoped aggregated claim counts and simulated totals."""
    query = Claim.query
    if current_user.role == "policyholder":
        query = query.join(Policy).filter(Policy.holder_user_id == current_user.id)
    elif current_user.role == "hospital":
        query = query.filter(Claim.claim_type == "cashless", Claim.hospital_id == current_user.hospital_id)
    claim_ids = query.with_entities(Claim.id)
    by_status = db.session.query(Claim.status, func.count(Claim.id)).filter(Claim.id.in_(claim_ids)).group_by(Claim.status).all()
    by_type = db.session.query(Claim.claim_type, func.count(Claim.id)).filter(Claim.id.in_(claim_ids)).group_by(Claim.claim_type).all()
    requested = db.session.query(func.coalesce(func.sum(Claim.requested_amount_inr), 0)).filter(Claim.id.in_(claim_ids)).scalar()
    eligible = db.session.query(func.coalesce(func.sum(Claim.eligible_amount_inr), 0)).filter(Claim.id.in_(claim_ids)).scalar()
    paid = db.session.query(func.coalesce(func.sum(Settlement.amount_inr), 0)).join(Claim).filter(Claim.id.in_(claim_ids)).scalar()
    return render_template("reports.html", by_status=by_status, by_type=by_type, requested=requested, eligible=eligible, paid=paid)
