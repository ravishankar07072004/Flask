"""Import the supplied synthetic CSV records in foreign-key-safe order."""
import csv
import io
import zipfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from app.extensions import db
from app.models import User, Hospital, Plan, Policy, Member, Claim, ClaimDocument, ClaimHistory, Settlement

DATA_ZIP = Path(__file__).resolve().parent.parent / "data" / "synthetic_dataset.zip"


def rows(archive, filename):
    """Yield CSV records from the bundled dataset archive."""
    path = next(name for name in archive.namelist() if name.endswith("/" + filename))
    return list(csv.DictReader(io.StringIO(archive.read(path).decode("utf-8-sig"))))


def as_date(value):
    return date.fromisoformat(value) if value else None


def as_decimal(value):
    return Decimal(value) if value else None


def seed_demo():
    """Create schema and load synthetic records without duplicating existing data."""
    db.create_all()
    if User.query.first():
        print("Database already contains users; skipping seed to avoid duplicate records.")
        return
    with zipfile.ZipFile(DATA_ZIP) as archive:
        for r in rows(archive, "hospitals.csv"):
            db.session.add(Hospital(id=int(r["hospital_id"]), name=r["name"], city=r["city"], network_status=bool(int(r["network_status"]))))
        for r in rows(archive, "plans.csv"):
            db.session.add(Plan(id=int(r["plan_id"]), plan_name=r["plan_name"], covered_treatment_types=r["covered_treatment_types"], annual_limit_inr=Decimal(r["annual_limit_inr"]), deductible_inr=Decimal(r["deductible_inr"]), copay_percent=Decimal(r["copay_percent"])))
        db.session.flush()
        for r in rows(archive, "users.csv"):
            user = User(id=int(r["user_id"]), username=r["username"], display_name=r["display_name"], role=r["role"], hospital_id=int(r["hospital_id"]) if r["hospital_id"] else None)
            user.set_password("Demo123!")
            db.session.add(user)
        db.session.flush()
        for r in rows(archive, "policies.csv"):
            db.session.add(Policy(id=int(r["policy_id"]), holder_user_id=int(r["holder_user_id"]), plan_id=int(r["plan_id"]), start_date=as_date(r["start_date"]), end_date=as_date(r["end_date"]), status=r["status"]))
        db.session.flush()
        for r in rows(archive, "members.csv"):
            db.session.add(Member(id=int(r["member_id"]), policy_id=int(r["policy_id"]), display_name=r["display_name"], relationship=r["relationship"]))
        db.session.flush()
        for r in rows(archive, "claims.csv"):
            db.session.add(Claim(id=int(r["claim_id"]), policy_id=int(r["policy_id"]), member_id=int(r["member_id"]), hospital_id=int(r["hospital_id"]), claim_type=r["claim_type"], treatment_type=r["treatment_type"], admission_date=as_date(r["admission_date"]), discharge_date=as_date(r["discharge_date"]), requested_amount_inr=Decimal(r["requested_amount_inr"]), status=r["status"], eligible_amount_inr=as_decimal(r["eligible_amount_inr"]), officer_user_id=int(r["officer_user_id"]) if r["officer_user_id"] else None, created_by_user_id=int(r["officer_user_id"] or (int(r["policy_id"]) - 100)), description="Imported synthetic demo claim"))
        db.session.flush()
        for r in rows(archive, "claim_documents.csv"):
            db.session.add(ClaimDocument(claim_id=int(r["claim_id"]), document_type=r["document_type"], checklist_status=r["checklist_status"]))
        for r in rows(archive, "claim_history.csv"):
            actor_id = int(r["actor_user_id"]) if r["actor_user_id"] else 14
            if not db.session.get(User, actor_id):
                actor_id = 14
            event_date = datetime.combine(as_date(r["event_date"]), datetime.min.time())
            db.session.add(ClaimHistory(claim_id=int(r["claim_id"]), actor_user_id=actor_id, from_status=r["from_status"] or None, to_status=r["to_status"], note=r["note"], created_at=event_date))
        for r in rows(archive, "settlements.csv"):
            actor_id = int(r["recorded_by_user_id"])
            if not db.session.get(User, actor_id):
                actor_id = 14
            db.session.add(Settlement(claim_id=int(r["claim_id"]), payee_type=r["payee_type"], amount_inr=Decimal(r["amount_inr"]), recorded_by_user_id=actor_id, recorded_at=datetime.combine(as_date(r["recorded_date"]), datetime.min.time())))
        db.session.commit()
    print("Seeded synthetic hospitals, plans, users, policies, members, claims, checklists, history and settlements.")
