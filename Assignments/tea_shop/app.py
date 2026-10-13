
# Import datetime to get the current date and time.
# Import timedelta to calculate the tea preparation deadline.
from datetime import datetime, timedelta

# Path helps locate files and folders.
from pathlib import Path

# os is used to read environment variables.
import os

# Import MySQL connector to connect Python with MySQL.
import mysql.connector

# Load database configuration from the .env file.
from dotenv import load_dotenv

# Import Flask tools:
# Flask       -> creates the web application
# jsonify     -> returns JSON responses
# render_template -> displays HTML templates
# request     -> reads data sent by the client
from flask import Flask, jsonify, render_template, request


# Get the directory where this Python file is located.
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from the .env file in the project folder.
load_dotenv(BASE_DIR / ".env")


# Read MySQL connection details from environment variables.
# Default values are used if a variable is not configured.
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "0000")
DB_NAME = os.getenv("DB_NAME", "f_ass_4")


# Create the Flask application.
app = Flask(__name__)


# Create a connection to the MySQL server without selecting a database.
# This connection is used when creating the database.
def get_server_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
    )


# Connect to the specific MySQL database used by the application.
def get_db():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
    )


# Create the database and orders table if they do not already exist.
def initialize_db():

    # Connect to the MySQL server.
    server_conn = get_server_connection()

    try:
        # Create a cursor to execute SQL statements.
        cursor = server_conn.cursor()

        # Create the database if it does not exist.
        # utf8mb4 supports a wide range of characters.
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )

        # Close the cursor after executing the query.
        cursor.close()

    finally:
        # Always close the server connection.
        server_conn.close()

    # Connect to the newly created or existing database.
    conn = get_db()

    try:
        # Create a cursor for executing table queries.
        cursor = conn.cursor()

        # Create the orders table if it does not exist.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tea_shop_orders (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                customer_name VARCHAR(50) NOT NULL,
                tea_type ENUM('Regular', 'Ginger', 'Green') NOT NULL,
                preparation_seconds TINYINT UNSIGNED NOT NULL,
                simulate_failure BOOLEAN NOT NULL DEFAULT FALSE,
                status ENUM('Preparing', 'Ready', 'Failed')
                    NOT NULL DEFAULT 'Preparing',
                explanation VARCHAR(255),
                created_at DATETIME NOT NULL,
                ready_at DATETIME NOT NULL,
                INDEX idx_status_ready_at (status, ready_at)
            ) ENGINE=InnoDB
        """)

        # Save database changes.
        conn.commit()

        # Close the cursor.
        cursor.close()

    finally:
        # Close the database connection.
        conn.close()


# Check whether any order has reached its preparation deadline.
# Update expired orders to Ready or Failed.
def update_order_states():

    # Get the current date and time.
    now = datetime.now()

    # Connect to the application database.
    conn = get_db()

    try:
        # dictionary=True returns each row as a dictionary.
        cursor = conn.cursor(dictionary=True)

        # Find orders that are still Preparing but whose deadlines have passed.
        cursor.execute("""
            SELECT id, simulate_failure
            FROM tea_shop_orders
            WHERE status = 'Preparing' AND ready_at <= %s
        """, (now,))

        # Retrieve all matching orders.
        rows = cursor.fetchall()

        # Process each expired order independently.
        for row in rows:

            # If failure simulation was enabled, mark this order as Failed.
            if row["simulate_failure"]:

                cursor.execute("""
                    UPDATE tea_shop_orders
                    SET status = 'Failed',
                        explanation = %s
                    WHERE id = %s AND status = 'Preparing'
                """, (
                    "Simulated preparation failure. Please prepare this order again.",
                    row["id"],
                ))

            # Otherwise, mark the order as Ready.
            else:

                cursor.execute("""
                    UPDATE tea_shop_orders
                    SET status = 'Ready',
                        explanation = %s
                    WHERE id = %s AND status = 'Preparing'
                """, (
                    "Preparation completed successfully.",
                    row["id"],
                ))

        # Save all status updates.
        conn.commit()

    finally:
        # Close the database connection even if an error occurs.
        conn.close()


# Convert a database row into a dictionary that can be returned as JSON.
def serialize_order(row):

    # Read the creation time and preparation deadline from the database.
    created_at = row["created_at"]
    ready_at = row["ready_at"]

    # Return the order details in a JSON-friendly format.
    return {
        # Unique numeric database ID.
        "id": row["id"],

        # Generate a readable order number from the database ID.
        "order_number": f"TS-{row['id']:04d}",

        # Customer and tea details.
        "customer_name": row["customer_name"],
        "tea_type": row["tea_type"],
        "preparation_seconds": row["preparation_seconds"],

        # Convert the database boolean value to a Python boolean.
        "simulate_failure": bool(row["simulate_failure"]),

        # Current order status and explanation.
        "status": row["status"],
        "explanation": row["explanation"],

        # Convert date and time values to strings for JSON.
        "created_at": (
            created_at.isoformat(sep=" ", timespec="seconds")
            if isinstance(created_at, datetime)
            else str(created_at)
        ),
        "ready_at": (
            ready_at.isoformat(sep=" ", timespec="seconds")
            if isinstance(ready_at, datetime)
            else str(ready_at)
        ),
    }


# Display the main HTML page when the user visits the website.
@app.get("/")
def index():
    return render_template("index.html")


# Receive a new tea order from the frontend.
# A successful order returns HTTP 201 Created.
@app.post("/api/orders")
def create_order():

    # Read the incoming JSON data.
    # If the request contains no valid JSON, use an empty dictionary.
    data = request.get_json(silent=True) or {}

    # Extract the values submitted by the customer.
    name = data.get("customer_name")
    tea_type = data.get("tea_type")
    seconds = data.get("preparation_seconds")
    simulate_failure = data.get("simulate_failure", False)

    # Store validation errors in a dictionary.
    errors = {}

    # Validate the customer name.
    # The name must contain between 2 and 50 characters.
    if not isinstance(name, str) or not 2 <= len(name.strip()) <= 50:
        errors["customer_name"] = (
            "Customer name must contain 2–50 characters."
        )

    # Validate the selected tea type.
    if tea_type not in ("Regular", "Ginger", "Green"):
        errors["tea_type"] = (
            "Choose Regular, Ginger, or Green tea."
        )

    # Accept only 2, 4, or 6 seconds.
    # Reject booleans because bool is a subclass of int in Python.
    if isinstance(seconds, bool) or seconds not in (2, 4, 6):
        errors["preparation_seconds"] = (
            "Preparation time must be 2, 4, or 6 seconds."
        )

    # Check that the failure flag is a boolean.
    if not isinstance(simulate_failure, bool):
        errors["simulate_failure"] = (
            "Simulate failure must be true or false."
        )

    # If any validation fails, return HTTP 400 and the error details.
    if errors:
        return jsonify({
            "error": "Please correct the form inputs.",
            "fields": errors
        }), 400

    # Record the order creation time.
    now = datetime.now()

    # Calculate when preparation should finish.
    ready_at = now + timedelta(seconds=seconds)

    # Connect to MySQL to save the new order.
    conn = get_db()

    try:
        # Create a cursor to execute the INSERT statement.
        cursor = conn.cursor()

        # Insert the order with an initial status of Preparing.
        # %s placeholders safely pass the supplied values to MySQL.
        cursor.execute("""
            INSERT INTO tea_shop_orders (
                customer_name,
                tea_type,
                preparation_seconds,
                simulate_failure,
                status,
                explanation,
                created_at,
                ready_at
            ) VALUES (%s, %s, %s, %s, 'Preparing', %s, %s, %s)
        """, (
            name.strip(),
            tea_type,
            seconds,
            simulate_failure,
            "Order accepted; preparation is in progress.",
            now,
            ready_at,
        ))

        # Save the new order.
        conn.commit()

        # Retrieve the unique ID generated by MySQL.
        order_id = cursor.lastrowid

        # Close the cursor.
        cursor.close()

    finally:
        # Release the database connection.
        conn.close()

    # Retrieve the saved order so the API can return its full details.
    conn = get_db()

    try:
        # Use a dictionary cursor for convenient field access.
        cursor = conn.cursor(dictionary=True)

        # Retrieve the order using its unique ID.
        cursor.execute(
            "SELECT * FROM tea_shop_orders WHERE id = %s",
            (order_id,)
        )

        # Fetch the saved order.
        row = cursor.fetchone()

        # Close the cursor.
        cursor.close()

    finally:
        # Close the connection.
        conn.close()

    # Return the created order and HTTP 201 status.
    return jsonify({
        "message": "Order created.",
        "order": serialize_order(row)
    }), 201


# Retrieve all saved orders and their current states.
@app.get("/api/orders")
def list_orders():

    # Update orders whose preparation deadlines have passed.
    update_order_states()

    # Connect to MySQL to retrieve the orders.
    conn = get_db()

    try:
        # Return database rows as dictionaries.
        cursor = conn.cursor(dictionary=True)

        # Retrieve the newest orders first.
        cursor.execute(
            "SELECT * FROM tea_shop_orders ORDER BY id DESC"
        )

        # Fetch every saved order.
        rows = cursor.fetchall()

        # Close the cursor.
        cursor.close()

    finally:
        # Close the database connection.
        conn.close()

    # Convert the database rows into JSON-compatible dictionaries.
    return jsonify({
        "orders": [serialize_order(row) for row in rows]
    })


# Retrieve the current state of one specific order.
@app.get("/api/orders/<int:order_id>")
def get_order(order_id):

    # Update expired orders before returning the requested status.
    update_order_states()

    # Connect to MySQL.
    conn = get_db()

    try:
        # Create a dictionary cursor.
        cursor = conn.cursor(dictionary=True)

        # Search for the requested order by its database ID.
        cursor.execute(
            "SELECT * FROM tea_shop_orders WHERE id = %s",
            (order_id,)
        )

        # Fetch the matching order, if it exists.
        row = cursor.fetchone()

        # Close the cursor.
        cursor.close()

    finally:
        # Close the connection.
        conn.close()

    # Return HTTP 404 if the order does not exist.
    if row is None:
        return jsonify({"error": "Order not found."}), 404

    # Return the requested order and its current state.
    return jsonify({"order": serialize_order(row)})


# Initialize the database and table when this module is imported.
initialize_db()


# Start the Flask development server when this file is run directly.
if __name__ == "__main__":
    app.run(debug=True)
