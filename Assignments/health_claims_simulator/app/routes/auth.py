"""Login and logout routes."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate a seeded local demo account."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("main.dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """End the current authenticated session."""
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    """Allow each authenticated user to change only their own password."""
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        errors = []
        if not current_user.check_password(current_password):
            errors.append("Current password is incorrect.")
        if len(new_password) < 8:
            errors.append("New password must contain at least 8 characters.")
        if new_password != confirm_password:
            errors.append("New password and confirmation do not match.")
        if current_password and new_password == current_password:
            errors.append("Choose a password different from your current password.")
        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            current_user.set_password(new_password)
            from app.extensions import db
            db.session.commit()
            flash("Your password has been changed successfully.", "success")
            return redirect(url_for("main.dashboard"))
    return render_template("change_password.html")
