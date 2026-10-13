import os
from functools import wraps
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-secret-key-for-development")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "0000"),
    "database": os.getenv("DB_NAME", "movie_planner"),
}

CATEGORIES = ["Comedy", "Action", "Animation", "Other"]
GENRES = ["Comedy", "Action", "Animation", "Drama", "Thriller", "Sci-Fi", "Other"]


def get_db():
    return mysql.connector.connect(**DB_CONFIG)


def query(sql, params=(), one=False, commit=False):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        result = None
        if commit:
            conn.commit()
            result = cur.lastrowid
        elif cur.with_rows:
            result = cur.fetchone() if one else cur.fetchall()
        return result
    finally:
        cur.close()
        conn.close()


def init_db():
    conn = get_db()
    cur = conn.cursor()
    statements = [
        """CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            username VARCHAR(50) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS movie_nights (
            id INT AUTO_INCREMENT PRIMARY KEY,
            creator_id INT NOT NULL,
            title VARCHAR(150) NOT NULL,
            night_date DATE NOT NULL,
            category ENUM('Comedy','Action','Animation','Other') NOT NULL,
            description VARCHAR(500) NOT NULL,
            status ENUM('open','finalized') NOT NULL DEFAULT 'open',
            final_choice_id INT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (creator_id) REFERENCES users(id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS movie_choices (
            id INT AUTO_INCREMENT PRIMARY KEY,
            night_id INT NOT NULL,
            added_by INT NULL,
            title VARCHAR(150) NOT NULL,
            genre VARCHAR(40) NOT NULL,
            reason VARCHAR(300) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (night_id) REFERENCES movie_nights(id) ON DELETE CASCADE,
            FOREIGN KEY (added_by) REFERENCES users(id) ON DELETE SET NULL
        )""",
        """CREATE TABLE IF NOT EXISTS votes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            choice_id INT NOT NULL,
            night_id INT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY unique_user_night (user_id, night_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (choice_id) REFERENCES movie_choices(id) ON DELETE CASCADE,
            FOREIGN KEY (night_id) REFERENCES movie_nights(id) ON DELETE CASCADE
        )"""
    ]
    try:
        for statement in statements:
            cur.execute(statement)
        # Upgrade existing databases without requiring users to delete their data.
        try:
            cur.execute("ALTER TABLE movie_choices ADD COLUMN added_by INT NULL")
        except mysql.connector.Error as exc:
            # MySQL error 1060 means the column already exists.
            if exc.errno != 1060:
                raise
        # For older choices, assign ownership to the movie-night creator.
        cur.execute("""UPDATE movie_choices c
                       JOIN movie_nights n ON n.id = c.night_id
                       SET c.added_by = n.creator_id
                       WHERE c.added_by IS NULL""")
        conn.commit()
    finally:
        cur.close()
        conn.close()


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to do that.", "warning")
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper


def owned_night(night_id):
    return query("SELECT * FROM movie_nights WHERE id=%s", (night_id,), one=True)


@app.route("/")
def home():
    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    sql = """SELECT n.*, u.name AS creator_name,
             (SELECT COUNT(*) FROM movie_choices c WHERE c.night_id=n.id) AS choice_count
             FROM movie_nights n JOIN users u ON u.id=n.creator_id WHERE 1=1"""
    params = []
    if search:
        sql += " AND n.title LIKE %s"
        params.append(f"%{search}%")
    if category in CATEGORIES:
        sql += " AND n.category=%s"
        params.append(category)
    sql += " ORDER BY n.night_date DESC, n.id DESC"
    nights = query(sql, tuple(params))
    return render_template("home.html", nights=nights, q=search, category=category, categories=CATEGORIES)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not name or not username or not password:
            flash("Please complete every field.", "danger")
        elif len(name) > 100 or len(username) > 50 or len(password) < 8:
            flash("Name and username must be within their length limits. Password must be at least 8 characters.", "danger")
        elif query("SELECT id FROM users WHERE username=%s", (username,), one=True):
            flash("That username is already taken. Please choose another.", "danger")
        else:
            query("INSERT INTO users (name, username, password_hash) VALUES (%s,%s,%s)",
                  (name, username, generate_password_hash(password)), commit=True)
            flash("Account created. You can now log in.", "success")
            return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = query("SELECT * FROM users WHERE username=%s", (username,), one=True)
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            flash(f"Welcome back, {user['name']}!", "success")
            next_url = request.args.get("next", "")
            if next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect(url_for("home"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


@app.route("/night/new", methods=["GET", "POST"])
@login_required
def create_night():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        night_date = request.form.get("night_date", "").strip()
        category = request.form.get("category", "")
        description = request.form.get("description", "").strip()
        if not title or not night_date or category not in CATEGORIES or not description:
            flash("Please enter a title, date, valid category, and description.", "danger")
        elif len(title) > 150 or len(description) > 500:
            flash("Title must be 150 characters or fewer and description 500 characters or fewer.", "danger")
        else:
            night_id = query(
                "INSERT INTO movie_nights (creator_id,title,night_date,category,description) VALUES (%s,%s,%s,%s,%s)",
                (session["user_id"], title, night_date, category, description), commit=True)
            flash("Movie night created. Add some movie choices!", "success")
            return redirect(url_for("night_detail", night_id=night_id))
    return render_template("night_form.html", night=None, categories=CATEGORIES, page_title="Create a movie night")


@app.route("/night/<int:night_id>")
def night_detail(night_id):
    night = query("""SELECT n.*, u.name AS creator_name FROM movie_nights n
                     JOIN users u ON u.id=n.creator_id WHERE n.id=%s""", (night_id,), one=True)
    if not night:
        flash("Movie night not found.", "danger")
        return redirect(url_for("home"))
    choices = query("""SELECT c.*, COUNT(v.id) AS vote_count
                       FROM movie_choices c LEFT JOIN votes v ON v.choice_id=c.id
                       WHERE c.night_id=%s GROUP BY c.id ORDER BY c.id""", (night_id,))
    my_vote = query("SELECT choice_id FROM votes WHERE user_id=%s AND night_id=%s",
                    (session.get("user_id", 0), night_id), one=True) if session.get("user_id") else None
    final_choice = None
    if night["final_choice_id"]:
        final_choice = query("SELECT * FROM movie_choices WHERE id=%s AND night_id=%s",
                             (night["final_choice_id"], night_id), one=True)
    is_owner = session.get("user_id") == night["creator_id"]
    return render_template("night_detail.html", night=night, choices=choices, my_vote=my_vote,
                           final_choice=final_choice, is_owner=is_owner, genres=GENRES)


@app.route("/night/<int:night_id>/edit", methods=["GET", "POST"])
@login_required
def edit_night(night_id):
    night = owned_night(night_id)
    if not night:
        flash("Movie night not found.", "danger")
        return redirect(url_for("home"))
    if night["creator_id"] != session["user_id"]:
        flash("You can only edit a movie night you created.", "danger")
        return redirect(url_for("night_detail", night_id=night_id))
    if night["status"] == "finalized":
        flash("A finalized movie night cannot be edited.", "warning")
        return redirect(url_for("night_detail", night_id=night_id))
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        night_date = request.form.get("night_date", "").strip()
        category = request.form.get("category", "")
        description = request.form.get("description", "").strip()
        if not title or not night_date or category not in CATEGORIES or not description:
            flash("Please enter a title, date, valid category, and description.", "danger")
        elif len(title) > 150 or len(description) > 500:
            flash("Title or description is too long.", "danger")
        else:
            query("""UPDATE movie_nights SET title=%s, night_date=%s, category=%s, description=%s
                     WHERE id=%s AND creator_id=%s""",
                  (title, night_date, category, description, night_id, session["user_id"]), commit=True)
            flash("Movie night updated.", "success")
            return redirect(url_for("night_detail", night_id=night_id))
    return render_template("night_form.html", night=night, categories=CATEGORIES, page_title="Edit movie night")


@app.route("/night/<int:night_id>/delete", methods=["POST"])
@login_required
def delete_night(night_id):
    night = owned_night(night_id)
    if not night:
        flash("Movie night not found.", "danger")
    elif night["creator_id"] != session["user_id"]:
        flash("You can only delete a movie night you created.", "danger")
    elif night["status"] == "finalized":
        flash("Finalized movie nights cannot be deleted.", "warning")
    else:
        query("DELETE FROM movie_nights WHERE id=%s AND creator_id=%s",
              (night_id, session["user_id"]), commit=True)
        flash("Movie night deleted.", "success")
        return redirect(url_for("home"))
    return redirect(url_for("night_detail", night_id=night_id))


@app.route("/night/<int:night_id>/choice", methods=["POST"])
@login_required
def add_choice(night_id):
    night = owned_night(night_id)
    title = request.form.get("title", "").strip()
    genre = request.form.get("genre", "")
    reason = request.form.get("reason", "").strip()
    if not night:
        flash("Movie night not found.", "danger")
    elif night["status"] != "open":
        flash("Choices cannot be added after finalization.", "warning")
    elif not title or genre not in GENRES or not reason or len(title) > 150 or len(reason) > 300:
        flash("Enter a movie title, valid genre, and reason (maximum 300 characters).", "danger")
    else:
        query("INSERT INTO movie_choices (night_id,added_by,title,genre,reason) VALUES (%s,%s,%s,%s,%s)",
              (night_id, session["user_id"], title, genre, reason), commit=True)
        flash("Movie suggestion added. You can now vote for your favorite movie.", "success")
    return redirect(url_for("night_detail", night_id=night_id))


@app.route("/choice/<int:choice_id>/delete", methods=["POST"])
@login_required
def delete_choice(choice_id):
    choice = query("SELECT * FROM movie_choices WHERE id=%s", (choice_id,), one=True)
    if not choice:
        flash("Movie choice not found.", "danger")
        return redirect(url_for("home"))
    night = owned_night(choice["night_id"])
    if choice["added_by"] != session["user_id"]:
        flash("You can delete only the movie choices you added.", "danger")
    elif night["status"] != "open":
        flash("Choices cannot be deleted after finalization.", "warning")
    else:
        query("DELETE FROM movie_choices WHERE id=%s", (choice_id,), commit=True)
        flash("Movie choice deleted.", "success")
    return redirect(url_for("night_detail", night_id=choice["night_id"]))


@app.route("/night/<int:night_id>/vote", methods=["POST"])
@login_required
def vote(night_id):
    night = owned_night(night_id)
    choice_id = request.form.get("choice_id", type=int)
    choice = query("SELECT * FROM movie_choices WHERE id=%s AND night_id=%s", (choice_id, night_id), one=True) if choice_id else None
    if not night:
        flash("Movie night not found.", "danger")
    elif night["status"] != "open":
        flash("Voting is closed for this movie night.", "warning")
    elif not choice:
        flash("Select a valid movie choice.", "danger")
    else:
        query("""INSERT INTO votes (user_id,choice_id,night_id) VALUES (%s,%s,%s)
                 ON DUPLICATE KEY UPDATE choice_id=VALUES(choice_id), created_at=CURRENT_TIMESTAMP""",
              (session["user_id"], choice_id, night_id), commit=True)
        flash("Your vote has been saved.", "success")
    return redirect(url_for("night_detail", night_id=night_id))


@app.route("/night/<int:night_id>/finalize", methods=["POST"])
@login_required
def finalize(night_id):
    night = owned_night(night_id)
    choice_id = request.form.get("choice_id", type=int)
    count = query("SELECT COUNT(*) AS total FROM movie_choices WHERE night_id=%s", (night_id,), one=True)["total"] if night else 0
    choice = query("SELECT id FROM movie_choices WHERE id=%s AND night_id=%s", (choice_id, night_id), one=True) if choice_id else None
    if not night:
        flash("Movie night not found.", "danger")
    elif night["creator_id"] != session["user_id"]:
        flash("Only the creator can finalize this movie night.", "danger")
    elif night["status"] != "open":
        flash("This movie night is already finalized.", "warning")
    elif count < 2:
        flash("Add at least two movie choices before finalizing.", "danger")
    elif not choice:
        flash("Select a valid final movie.", "danger")
    else:
        query("UPDATE movie_nights SET final_choice_id=%s, status='finalized' WHERE id=%s AND creator_id=%s",
              (choice_id, night_id, session["user_id"]), commit=True)
        flash("Final movie selected. Voting is now closed.", "success")
    return redirect(url_for("night_detail", night_id=night_id))


@app.errorhandler( mysql.connector.Error )
def database_error(error):
    app.logger.exception("Database error: %s", error)
    return render_template("error.html", message="The database could not complete the request. Check your MySQL service and .env settings."), 500


if __name__ == "__main__":
    try:
        init_db()
        app.run(debug=True)
    except mysql.connector.Error as exc:
        print("Could not connect to MySQL. Check that MySQL is running and .env credentials are correct.")
        print(exc)
