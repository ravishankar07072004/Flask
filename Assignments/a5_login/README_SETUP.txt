COMMUNITY EVENT MANAGER - MYSQL + LOGIN

1. Install Python 3.10+ and make sure MySQL Server is running.
2. Open this folder in Command Prompt / terminal.
3. Create and activate a virtual environment (recommended):
   py -m venv venv
   venv\Scripts\activate       (Windows)
4. Install packages:
   pip install -r requirements.txt
5. Copy .env.example to .env and use your database settings:
   DB_HOST=127.0.0.1
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=your MySQL password
   DB_NAME=event_login
   FLASK_SECRET_KEY=replace-with-a-long-random-secret
6. Ensure the database exists. In MySQL Workbench run:
   CREATE DATABASE IF NOT EXISTS event_login;
   The MySQL user must have permission to create tables in this database.
7. Start the application:
   python run.py
8. Open http://127.0.0.1:5000/register and create an account, then log in.

The app creates app_users, events and event_registrations tables if absent. Event data is now stored in MySQL rather than an in-memory Python list. Passwords are stored as Werkzeug password hashes, not plain text. Posting, editing, deleting and reserving seats require login. Event details and event discovery remain public.

If your existing event_login database already contains a table named `events` with a different schema, back it up and compare its columns before running. CREATE TABLE IF NOT EXISTS will not change an existing table's structure. The app expects the columns defined in app.py.

Security notes: do not commit .env to source control; use a strong FLASK_SECRET_KEY; turn FLASK_DEBUG off outside local development. The supplied DB_PASSWORD is placed in your local .env, not hardcoded into app.py.
