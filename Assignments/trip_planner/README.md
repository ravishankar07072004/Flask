# Trip Planner — Flask + MySQL

A multipage trip planning app with private user trips, day-wise activities, cost totals, budget difference, and a public Explore page for community place suggestions. Uses MySQL, not SQLite.

## Features
- Register, login, logout; passwords stored as secure hashes.
- My trips: a user sees and manages only trips they own.
- Create, edit and delete trips.
- Add, edit and delete activities within a trip.
- Trip detail groups activities by date and calculates saved activity costs and budget remaining/overage.
- Validates trip dates, activity dates and non-negative budget/cost values.
- Rejects trip date edits if any existing activity would fall outside the new dates.
- Explore places with combined name/destination search and category filter.
- Logged-in users can publish public place suggestions.
- Print itinerary button on trip detail page.

## Setup (Windows / VS Code)

1. Extract the ZIP and open the `trip_planner` folder in VS Code.
2. Start your MySQL server.
3. Open MySQL Workbench and run:
   ```sql
   CREATE DATABASE IF NOT EXISTS trip_planner;
   ```
   Or run `schema.sql`.
4. Check `.env`. Defaults are `127.0.0.1`, port `3306`, user `root`, password `0000`, database `trip_planner`. Update these to match your local MySQL.
5. Open the terminal in the project folder and run:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   python app.py
   ```
6. Visit http://127.0.0.1:5000

The app creates the required tables automatically when it starts. The database itself must exist first. If you prefer to use your existing `event_login` database, change `DB_NAME=trip_planner` to `DB_NAME=event_login` in `.env` before starting; tables will be created there, but this app uses its own `trips` and `activities` table names.

## Acceptance test checklist
1. Register user A, create a two-day trip, add activities on both dates. Detail page should group activities by date.
2. Edit an activity cost and save; total and remaining/over-budget figure update on reload.
3. Try adding an activity before the trip start or after the end; the form should show a validation message.
4. Try a negative budget or activity cost; validation should reject it.
5. Edit trip dates so a saved activity would be outside the new dates; the change should be rejected with an explanation.
6. Register user B and log in. User B cannot see user A's private trip by visiting its URL.
7. Open Explore and combine a name/destination search with a category filter.

## Security / deployment notes
- Change `FLASK_SECRET_KEY` to a long random secret before deployment.
- `.env` contains local development credentials; do not commit it or publish it.
- This project is intended for local learning/demo use. For production, turn off Flask debug mode and add CSRF protection, rate limiting, and deployment-specific hardening.


## Date format
All trip and activity date entry fields use **DD/MM/YYYY** (for example, `25/12/2026`). Dates are stored in MySQL as DATE values and displayed in DD/MM/YYYY format.
