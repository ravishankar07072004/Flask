from flask import Flask, request, jsonify, render_template, url_for

app = Flask(__name__)

# Store registered users in a list (in-memory storage)
registered_users = []


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
    # Get JSON data sent from JavaScript fetch()
    data = request.get_json()

    # Read each field from the JSON data
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    phone = data.get("phone", "").strip()
    course = data.get("course", "").strip()
    gender = data.get("gender", "").strip()

    # Validate — make sure required fields are not empty
    if not name or not email or not phone or not course:
        return jsonify({
            "status": "error",
            "message": "Please fill in all required fields."
        }), 400

    # Create a user dictionary
    user = {
        "id": len(registered_users) + 1,
        "name": name,
        "email": email,
        "phone": phone,
        "course": course,
        "gender": gender,
    }

    # Add user to the list
    registered_users.append(user)

    return jsonify({
        "status": "success",
        "message": f"{name} registered successfully!",
        "user": user,
    })


# Route 4: Display all registered users on another page
@app.route("/users")
def users_page():
    return render_template("users.html", users=registered_users)


# Route 5: API Endpoint — Get all users as JSON
@app.route("/api/users", methods=["GET"])
def api_get_users():
    return jsonify({
        "status": "success",
        "count": len(registered_users),
        "users": registered_users,
    })


# Run Flask application in debug mode
if __name__ == "__main__":
    app.run(debug=True)
