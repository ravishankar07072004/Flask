from flask import Flask, request, jsonify, render_template, url_for
import mysql.connector
import os
import json
from dotenv import load_dotenv

# Load .env from the same folder as app.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

load_dotenv(dotenv_path=ENV_PATH, override=True)

print("ENV file exists:", os.path.isfile(ENV_PATH))
print("DB_HOST:", os.getenv("DB_HOST"))
print("DB_NAME:", os.getenv("DB_NAME"))

app = Flask(__name__)

# Store registered users in a list (in-memory storage)
# registered_users = []




def get_db():
    # Each database operation opens its own connection.
    return mysql.connector.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
    )






# Route 1: Home Page
@app.route("/")
def home():
    return render_template("register.html")


# Route 2: Registration Page
@app.route("/register")
def register_page():
    return render_template("register.html")


# Route 3: API Endpoint — Receive form data from JavaScript

@app.route("/api/register", methods=["POST"])
def api_register():

    # Step 1: Get JSON data from JavaScript
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "Invalid JSON data."
        }), 400

    # Step 2: Read form fields
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    phone = data.get("phone", "").strip()
    dob = data.get("dob", "").strip()
    gender = data.get("gender", "").strip()
    course = data.get("course", "").strip()
    qualification = data.get("qualification", "").strip()
    training_mode = data.get("training_mode", "").strip()
    address = data.get("address", "").strip()
    website = data.get("website", "").strip()

    # Skills is a list
    skills = data.get("skills", [])

    # Experience is numeric
    experience = data.get("experience", 0)

    # Password fields
    password = data.get("password", "")
    confirm_password = data.get("confirm_password", "")
    agree = data.get("agree", False)

    # Step 3: Validate field types
    if not all(isinstance(data.get(field), str) for field in [
        "name", "email", "phone", "dob", "gender",
        "course", "qualification", "training_mode",
        "address", "website", "password", "confirm_password"
    ]):
        return jsonify({
            "status": "error",
            "message": "Invalid field values."
        }), 400

    # Step 4: Validate required fields
    if not all([
        name, email, phone, dob, gender, course,
        qualification, training_mode, address, password
    ]):
        return jsonify({
            "status": "error",
            "message": "Please fill in all required fields."
        }), 400

    # Step 5: Validate skills
    if not isinstance(skills, list) or not skills:
        return jsonify({
            "status": "error",
            "message": "Please select at least one skill."
        }), 400

    if not all(isinstance(skill, str) for skill in skills):
        return jsonify({
            "status": "error",
            "message": "Invalid skills data."
        }), 400

    # Step 6: Validate experience
    try:
        experience = int(experience)
        if experience < 0 or experience > 50:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({
            "status": "error",
            "message": "Experience must be between 0 and 50."
        }), 400

    # Step 7: Validate password and agreement
    if password != confirm_password:
        return jsonify({
            "status": "error",
            "message": "Passwords do not match."
        }), 400

    if len(password) < 8:
        return jsonify({
            "status": "error",
            "message": "Password must contain at least 8 characters."
        }), 400

    if agree is not True:
        return jsonify({
            "status": "error",
            "message": "Please agree to register."
        }), 400

    # Step 9: Insert data into MySQL
    connection = None
    cursor = None

    try:
        connection = get_db()
        cursor = connection.cursor()

        sql = """
            INSERT INTO student_data (
                name, email, phone, dob, gender, course,
                qualification, training_mode, skills,
                experience, address, website, password, agree
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s
            )
        """

        values = (
            name,
            email,
            phone,
            dob,
            gender,
            course,
            qualification,
            training_mode,
            json.dumps(skills),
            experience,
            address,
            website or None,
            password,
            agree
        )

        cursor.execute(sql, values)
        connection.commit()

        return jsonify({
            "status": "success",
            "message": f"{name} registered successfully!"
        }), 201

    except mysql.connector.Error as e:
        if connection is not None and connection.is_connected():
            connection.rollback()

        app.logger.exception("Database error")

        # Avoid exposing database details to the browser
        return jsonify({
            "status": "error",
            "message": (
                "This email is already registered."
                if e.errno == 1062
                else "Unable to register the student. Please try again."
            )
        }), 409 if e.errno == 1062 else 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()






# Route 5: API Endpoint — Get all users as JSON
   
@app.route("/api/users", methods=["GET"])
def api_get_users():
    connection = None
    cursor = None
    try:
        connection = get_db()
        print("MySQL connected successfully!")
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
    SELECT name, email, phone, dob, gender, course,
           qualification, training_mode, skills, experience,
           address, website, created_at
    FROM student_data
""")
        data = cursor.fetchall()
        return jsonify({
            "status": "success",
            "count": len(data),
            "users": data
        })
    except mysql.connector.Error as e:
        app.logger.exception("Database error")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()



@app.route("/users")
def users_page():
    connection = None
    cursor = None
    try:
        connection = get_db()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
    SELECT name, email, phone, dob, gender, course,
           qualification, training_mode, skills, experience,
           address, website, created_at
    FROM student_data
""")
        data = cursor.fetchall()
        return render_template("users.html", users=data)
    except mysql.connector.Error:
        app.logger.exception("Failed to retrieve students")
        return "Unable to retrieve student records. Check the Flask terminal.", 500
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    app.run(debug=True)