import os
from datetime import date
from functools import wraps
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-development-secret")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "0000"),
    "database": os.getenv("DB_NAME", "event_login"),
}


def get_db():
    """Open a new MySQL connection. Each route closes its cursor and connection."""
    return mysql.connector.connect(**DB_CONFIG)


def init_db():
    """Create the application's tables if they do not already exist."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(190) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(200) NOT NULL,
                category VARCHAR(60) NOT NULL,
                event_date DATE NOT NULL,
                event_time TIME NOT NULL,
                venue VARCHAR(255) NOT NULL,
                capacity INT NOT NULL,
                booked_seats INT NOT NULL DEFAULT 0,
                email VARCHAR(190) NOT NULL,
                deadline DATE NOT NULL,
                description TEXT NOT NULL,
                cover_class VARCHAR(30) NOT NULL DEFAULT '',
                created_by INT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_events_creator FOREIGN KEY (created_by) REFERENCES app_users(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_registrations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                event_id INT NOT NULL,
                user_id INT NOT NULL,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(190) NOT NULL,
                phone VARCHAR(30) NOT NULL,
                seats INT NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_user_event (event_id, user_id),
                CONSTRAINT fk_reg_event FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
                CONSTRAINT fk_reg_user FOREIGN KEY (user_id) REFERENCES app_users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login", next=request.url))
        return view(*args, **kwargs)
    return wrapped


def event_from_row(row):
    """Map database column names to the names expected by the existing templates."""
    if not row:
        return None
    row["date"] = row.pop("event_date")
    row["time"] = row.pop("event_time")
    return row


def get_event(event_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM events WHERE id = %s", (event_id,))
        row = cursor.fetchone()
        if not row:
            abort(404)
        return event_from_row(row)
    finally:
        cursor.close()
        conn.close()


@app.route("/")
def index():
    search_query = request.args.get("search", "").strip()
    selected_category = request.args.get("category", "").strip()
    upcoming_only = request.args.get("upcoming") == "1"
    sql = "SELECT * FROM events WHERE 1=1"
    params = []
    if search_query:
        sql += " AND (title LIKE %s OR venue LIKE %s)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])
    if selected_category:
        sql += " AND category = %s"
        params.append(selected_category)
    if upcoming_only:
        sql += " AND event_date >= %s"
        params.append(date.today())
    sql += " ORDER BY event_date ASC, event_time ASC"
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, tuple(params))
        events = [event_from_row(row) for row in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close()
    return render_template("index.html", events=events, search_query=search_query,
                           selected_category=selected_category, upcoming_only=upcoming_only)


@app.route("/register", methods=["GET", "POST"])
def signup():
    if "user_id" in session:
        return redirect(url_for("index"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if not name or not email or not password:
            flash("Please complete all required fields.", "error")
        elif len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        else:
            conn = get_db()
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO app_users (name, email, password_hash) VALUES (%s, %s, %s)",
                               (name, email, generate_password_hash(password)))
                conn.commit()
                flash("Account created. You can now log in.", "success")
                return redirect(url_for("login"))
            except mysql.connector.IntegrityError:
                conn.rollback()
                flash("An account with this email already exists.", "error")
            finally:
                cursor.close()
                conn.close()
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, name, email, password_hash FROM app_users WHERE email = %s", (email,))
            user = cursor.fetchone()
        finally:
            cursor.close()
            conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_email"] = user["email"]
            flash(f"Welcome back, {user['name']}!", "success")
            next_url = request.args.get("next", "")
            # Only allow local relative paths to avoid open redirects.
            if next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect(url_for("index"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/events/new", methods=["GET", "POST"])
@login_required
def create_event():
    if request.method == "POST":
        try:
            capacity = int(request.form.get("capacity", "0"))
            if capacity < 1:
                raise ValueError
        except ValueError:
            flash("Seat capacity must be a positive whole number.", "error")
            return render_template("create_event.html")
        values = (request.form.get("title", "").strip(), request.form.get("category", "").strip(),
                  request.form.get("date"), request.form.get("time"), request.form.get("venue", "").strip(),
                  capacity, request.form.get("email", "").strip(), request.form.get("deadline"),
                  request.form.get("description", "").strip(), session["user_id"])
        if not all(values[:5]) or not values[6] or not values[7] or not values[8]:
            flash("Please complete all required event fields.", "error")
            return render_template("create_event.html")
        conn = get_db(); cursor = conn.cursor()
        try:
            cursor.execute("""INSERT INTO events
                (title, category, event_date, event_time, venue, capacity, email, deadline, description, created_by)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", values)
            conn.commit()
            flash("Event published successfully!", "success")
            return redirect(url_for("event_details", event_id=cursor.lastrowid))
        except mysql.connector.Error:
            conn.rollback()
            flash("The event could not be saved. Check the entered dates and fields.", "error")
        finally:
            cursor.close(); conn.close()
    return render_template("create_event.html")


@app.route("/events/<int:event_id>")
def event_details(event_id):
    return render_template("event_details.html", event=get_event(event_id))


@app.route("/events/<int:event_id>/register", methods=["GET", "POST"])
@login_required
def register_event(event_id):
    event = get_event(event_id)
    if request.method == "POST":
        try:
            seats = int(request.form.get("seats", "1"))
            if seats < 1:
                raise ValueError
        except ValueError:
            flash("Please choose a valid number of seats.", "error")
            return render_template("register.html", event=event)
        conn = get_db(); cursor = conn.cursor(dictionary=True)
        try:
            conn.start_transaction()
            cursor.execute("SELECT capacity, booked_seats FROM events WHERE id = %s FOR UPDATE", (event_id,))
            current = cursor.fetchone()
            if not current:
                abort(404)
            if seats > current["capacity"] - current["booked_seats"]:
                conn.rollback()
                flash("Sorry, not enough seats are available.", "error")
            else:
                cursor.execute("SELECT id FROM event_registrations WHERE event_id=%s AND user_id=%s", (event_id, session["user_id"]))
                if cursor.fetchone():
                    conn.rollback()
                    flash("You have already registered for this event.", "error")
                else:
                    cursor.execute("INSERT INTO event_registrations (event_id,user_id,name,email,phone,seats) VALUES (%s,%s,%s,%s,%s,%s)",
                                   (event_id, session["user_id"], request.form.get("name", "").strip() or session.get("user_name", ""),
                                    request.form.get("email", "").strip() or session.get("user_email", ""),
                                    request.form.get("phone", "").strip(), seats))
                    cursor.execute("UPDATE events SET booked_seats = booked_seats + %s WHERE id = %s", (seats, event_id))
                    conn.commit()
                    flash(f"Successfully registered {seats} seat(s)!", "success")
                    return redirect(url_for("event_details", event_id=event_id))
        except mysql.connector.IntegrityError:
            conn.rollback()
            flash("You have already registered for this event.", "error")
        except mysql.connector.Error:
            conn.rollback()
            flash("Registration could not be completed. Please try again.", "error")
        finally:
            cursor.close(); conn.close()
        event = get_event(event_id)
    return render_template("register.html", event=event)


@app.route("/events/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
def edit_event(event_id):
    event = get_event(event_id)
    if event.get("created_by") not in (None, session["user_id"]):
        abort(403)
    if request.method == "POST":
        try:
            capacity = int(request.form.get("capacity", event["capacity"]))
            if capacity < event["booked_seats"]:
                raise ValueError
        except ValueError:
            flash("Capacity cannot be lower than the number of seats already booked.", "error")
            return render_template("edit_event.html", event=event)
        values = (request.form.get("title", "").strip(), request.form.get("category", "").strip(),
                  request.form.get("date"), request.form.get("time"), request.form.get("venue", "").strip(),
                  capacity, request.form.get("email", "").strip(), request.form.get("deadline"),
                  request.form.get("description", "").strip(), event_id)
        conn = get_db(); cursor = conn.cursor()
        try:
            cursor.execute("""UPDATE events SET title=%s, category=%s, event_date=%s, event_time=%s,
                venue=%s, capacity=%s, email=%s, deadline=%s, description=%s WHERE id=%s""", values)
            conn.commit()
            flash("Event updated successfully!", "success")
            return redirect(url_for("event_details", event_id=event_id))
        except mysql.connector.Error:
            conn.rollback()
            flash("Event could not be updated. Check the entered values.", "error")
        finally:
            cursor.close(); conn.close()
    return render_template("edit_event.html", event=event)


@app.route("/events/<int:event_id>/delete", methods=["POST"])
@login_required
def delete_event(event_id):
    event = get_event(event_id)
    if event.get("created_by") not in (None, session["user_id"]):
        abort(403)
    conn = get_db(); cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM events WHERE id=%s", (event_id,))
        conn.commit()
        flash(f"Event '{event['title']}' deleted successfully!", "success")
    finally:
        cursor.close(); conn.close()
    return redirect(url_for("index"))


@app.context_processor
def inject_user():
    return {"logged_in": "user_id" in session, "current_user_name": session.get("user_name")}


if __name__ == "__main__":
    try:
        init_db()
        print("MySQL connected; application tables are ready.")
    except mysql.connector.Error as exc:
        raise SystemExit(f"Could not connect to MySQL database '{DB_CONFIG['database']}': {exc}\nCheck the .env settings and ensure MySQL is running.")
    app.run(debug=os.getenv("FLASK_DEBUG", "1") == "1")
