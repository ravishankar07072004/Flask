"""User accounts and role-based access helpers."""
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from app.extensions import db


class User(UserMixin, db.Model):
    """A seeded simulator account with one of the permitted application roles."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.Enum("policyholder", "hospital", "claims_officer", "admin", name="user_roles"), nullable=False)
    hospital_id = db.Column(db.Integer, db.ForeignKey("hospitals.id", ondelete="SET NULL"), nullable=True)

    hospital = db.relationship("Hospital", back_populates="users")
    policies = db.relationship("Policy", back_populates="holder", foreign_keys="Policy.holder_user_id")

    def set_password(self, password: str) -> None:
        """Hash a password before storing it."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Return whether the supplied password matches the stored hash."""
        return check_password_hash(self.password_hash, password)
