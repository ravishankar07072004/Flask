# Trip Planner — Flask + MySQL + SQLAlchemy ORM

A multipage trip-planning app with private user trips, day-wise activities, cost totals, budget difference, and a public Explore page for community place suggestions. The database layer uses **SQLAlchemy ORM** instead of manually written CRUD SQL and `mysql.connector` cursors.

## Features
- Register, log in and log out; passwords are stored as secure hashes.
- Users can view and manage only their own trips.
- Create, edit and delete trips.
- Add, edit and delete activities within a trip.
- Day-wise itinerary with activity costs and budget remaining/overage.
- Validates dates, activity dates and non-negative budget/cost values.
- Prevents changing trip dates if saved activities would fall outside the new range.
- Explore public place suggestions with name/destination search and category filter.
- Logged-in users can publish place suggestions.
- Print itinerary.
- Date entry and display format: **DD/MM/YYYY**.

## Setup on Windows / VS Code

1. Extract the ZIP and open the `trip_planner` folder.
2. Start MySQL Server.
3. Open MySQL Workbench and run `schema.sql`, or run:
   ```sql
   CREATE DATABASE IF NOT EXISTS trip_planner CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
4. Check `.env` and set your local MySQL credentials (`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`). The database must exist before the app starts. The app creates the four tables through `db.create_all()`.
5. Open a terminal in the `trip_planner` folder and run:
   ```powershell
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   python app.py
   ```
6. Visit http://127.0.0.1:5000.

## Project structure
```text
trip_planner/
├── app.py
├── extensions.py
├── models/
│   ├── __init__.py
│   ├── base.py
│   ├── user.py
│   ├── trip.py
│   ├── activity.py
│   └── place_suggestion.py
├── templates/
├── static/
├── schema.sql
├── requirements.txt
└── .env.example
```

## ORM implementation overview
- All SQLAlchemy model classes are maintained in the `models/` package: `user.py`, `trip.py`, `activity.py`, and `place_suggestion.py`.
- `models/base.py` contains the shared abstract `BaseModel` and dictionary-style field access compatibility used by templates.
- `extensions.py` defines the shared SQLAlchemy extension; `app.py` initializes it and imports all models.
- `Model.query.filter_by(...)` and `.filter(...)` read records.
- `db.session.add(model)` stages inserts.
- Assigning values to model attributes updates records when committed.
- `db.session.delete(model)` stages deletion.
- `db.session.commit()` saves changes; `db.session.rollback()` cancels a failed transaction.
- SQLAlchemy manages connection pooling and generates SQL from ORM operations.

The model definitions create missing tables but do not migrate existing table definitions. Back up important data before changing schema/model definitions.

## Acceptance checklist
1. Register a user, create a two-day trip and add activities on both days.
2. Edit an activity cost; totals should update when the itinerary reloads.
3. Try adding an activity outside the trip dates; it should be rejected.
4. Try a negative budget or cost; it should be rejected.
5. Try changing trip dates so existing activities are outside the range; the edit should be rejected.
6. Register a second user and verify they cannot open the first user's private trip.
7. Use Explore search and category filters; submit a place suggestion while logged in.

## Security notes
- Replace `FLASK_SECRET_KEY` with a long random value.
- Do not commit or publish `.env` credentials.
- This project is for local learning/demo use. Before production, disable Flask debug mode and add CSRF protection, rate limiting and deployment hardening.
