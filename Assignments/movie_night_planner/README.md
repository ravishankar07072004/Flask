# Movie Night Planner

A multipage Flask + MySQL application with a white-and-green UI.

## Features
- Register, log in, and log out; passwords are stored as secure hashes.
- Browse movie nights, search titles, and filter by category at the same time.
- Create, edit, and delete your own open movie nights.
- Add and remove movie choices as the creator.
- One vote per user per movie night; a new vote replaces the previous vote.
- Creator selects the final movie after at least two choices; finalization closes voting.
- Visitors can browse details but must log in to create plans or vote.

## Setup (Windows)
1. Install Python 3.10+ and MySQL Server.
2. Create/activate a virtual environment:
   ```bat
   python -m venv venv
   venv\Scripts\activate
   ```
3. Install dependencies:
   ```bat
   pip install -r requirements.txt
   ```
4. Confirm MySQL is running. The supplied `.env` uses:
   - host `127.0.0.1`
   - port `3306`
   - user `root`
   - database `event_login`
5. Update `.env` if your local MySQL credentials differ. The app creates the database tables automatically, but the database itself must exist. Create it with:
   ```sql
   CREATE DATABASE event_login;
   ```
6. Start the app:
   ```bat
   python app.py
   ```
7. Open `http://127.0.0.1:5000`.

## Notes
- `app.py` uses parameterized SQL queries and checks ownership on the server before modifying a movie night.
- Change `FLASK_SECRET_KEY` to a long random value before using the app beyond local development.
- The app runs with Flask debug mode for local development only. Turn debug mode off before deployment.
- The provided `.env` includes the database password supplied in the project request. Do not share this file publicly.


### Movie-choice ownership
Each movie choice records the user who added it. Only that user sees the delete button and can delete that choice. Other users cannot delete it, even by sending a direct request. Existing choices are assigned to the movie-night creator when the app starts and upgrades the existing database.
