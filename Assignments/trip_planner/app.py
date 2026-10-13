from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps
import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'change-this-local-development-key')

DB_CONFIG = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'trip_planner'),
}


def get_db():
    return mysql.connector.connect(**DB_CONFIG)


def init_db():
    # The configured database must exist first; tables are created automatically.
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(80) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB''')
    cur.execute('''CREATE TABLE IF NOT EXISTS trips (
        id INT AUTO_INCREMENT PRIMARY KEY,
        owner_id INT NOT NULL,
        destination VARCHAR(150) NOT NULL,
        start_date DATE NOT NULL,
        end_date DATE NOT NULL,
        budget DECIMAL(10,2) NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_trips_owner FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB''')
    cur.execute('''CREATE TABLE IF NOT EXISTS activities (
        id INT AUTO_INCREMENT PRIMARY KEY,
        trip_id INT NOT NULL,
        name VARCHAR(150) NOT NULL,
        activity_date DATE NOT NULL,
        activity_time TIME NULL,
        category VARCHAR(60) NOT NULL,
        place VARCHAR(180) NOT NULL,
        cost DECIMAL(10,2) NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_activities_trip FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE,
        INDEX idx_activity_trip_date (trip_id, activity_date)
    ) ENGINE=InnoDB''')
    cur.execute('''CREATE TABLE IF NOT EXISTS place_suggestions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(150) NOT NULL,
        destination VARCHAR(150) NOT NULL,
        category VARCHAR(60) NOT NULL,
        description TEXT NOT NULL,
        created_by INT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_suggestion_user FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
    ) ENGINE=InnoDB''')
    conn.commit()
    cur.close()
    conn.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'info')
            return redirect(url_for('login', next=request.path))
        return view(*args, **kwargs)
    return wrapped


def owned_trip(trip_id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute('SELECT * FROM trips WHERE id=%s AND owner_id=%s', (trip_id, session['user_id']))
    trip = cur.fetchone()
    cur.close()
    conn.close()
    if not trip:
        abort(404)
    return trip


def parse_money(value, label):
    try:
        amount = Decimal((value or '').strip())
        if not amount.is_finite() or amount < 0:
            raise InvalidOperation
        return amount
    except (InvalidOperation, ValueError):
        raise ValueError(f'{label} must be a valid number and cannot be negative.')


def parse_date_input(value):
    """Accept the requested DD/MM/YYYY format and ISO dates for compatibility."""
    if not value:
        raise ValueError('Please enter a date in DD/MM/YYYY format.')
    value = value.strip()
    for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError('Please enter a valid date in DD/MM/YYYY format, for example 25/12/2026.')


def parse_trip_dates(start_text, end_text):
    try:
        start = parse_date_input(start_text)
        end = parse_date_input(end_text)
    except (TypeError, ValueError):
        raise ValueError('Please enter valid start and end dates in DD/MM/YYYY format.')
    if end < start:
        raise ValueError('Trip end date must be on or after the start date.')
    return start, end


@app.template_filter('money')
def money(value):
    return f'₹{Decimal(str(value or 0)):,.2f}'


@app.template_filter('prettydate')
def prettydate(value):
    """Format a date safely; avoid calling strftime on a timedelta."""
    if value is None:
        return 'Date not set'
    if isinstance(value, timedelta):
        # A timedelta is a duration, not a calendar date. Display it safely
        # rather than raising the original Jinja UndefinedError.
        days = value.days
        return f'Day {days + 1}' if days >= 0 else f'{abs(days)} days before trip'
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value)
        except ValueError:
            return value
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.strftime('%d/%m/%Y')
    return str(value)


@app.template_filter('prettytime')
def prettytime(value):
    if value is None or value == '':
        return 'Any time'
    if isinstance(value, timedelta):
        seconds = int(value.total_seconds()) % 86400
        value = datetime.min + timedelta(seconds=seconds)
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%H:%M:%S').time()
        except ValueError:
            try:
                value = datetime.strptime(value, '%H:%M').time()
            except ValueError:
                return value
    if hasattr(value, 'strftime'):
        return value.strftime('%I:%M %p')
    return str(value)


@app.route('/')
def home():
    samples = [
        {'name': 'Araku Valley', 'description': 'Coffee plantations, green hills and scenic viewpoints.', 'category': 'Nature', 'image': 'https://images.unsplash.com/photo-1472396961693-142e6e269027?auto=format&fit=crop&w=1000&q=85'},
        {'name': 'Hyderabad', 'description': 'Historic landmarks, food streets and city experiences.', 'category': 'City', 'image': 'https://images.unsplash.com/photo-1565552629476-3f7c4f2f2d93?auto=format&fit=crop&w=1000&q=85'},
        {'name': 'Tirupati', 'description': 'Temples, local culture and nearby viewpoints.', 'category': 'Culture', 'image': 'https://images.unsplash.com/photo-1606293926075-69a00db032d4?auto=format&fit=crop&w=1000&q=85'},
    ]
    return render_template('home.html', samples=samples)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if len(username) < 3 or len(username) > 80 or len(password) < 6:
            flash('Username must be 3–80 characters and password at least 6 characters.', 'error')
            return render_template('register.html')
        conn = get_db(); cur = conn.cursor()
        try:
            cur.execute('INSERT INTO users (username, password_hash) VALUES (%s, %s)',
                        (username, generate_password_hash(password)))
            conn.commit()
            flash('Account created. Please log in.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.IntegrityError:
            flash('That username is already taken.', 'error')
        finally:
            cur.close(); conn.close()
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        conn = get_db(); cur = conn.cursor(dictionary=True)
        cur.execute('SELECT id, username, password_hash FROM users WHERE username=%s', (username,))
        user = cur.fetchone(); cur.close(); conn.close()
        if user and check_password_hash(user['password_hash'], password):
            session.clear(); session['user_id'] = user['id']; session['username'] = user['username']
            flash(f'Welcome, {user["username"]}!', 'success')
            return redirect(url_for('my_trips'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('You have logged out.', 'info')
    return redirect(url_for('home'))


@app.route('/trips')
@login_required
def my_trips():
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute('''SELECT t.*, COUNT(a.id) AS activity_count, COALESCE(SUM(a.cost),0) AS total_cost
                   FROM trips t LEFT JOIN activities a ON a.trip_id=t.id
                   WHERE t.owner_id=%s GROUP BY t.id ORDER BY t.start_date DESC''', (session['user_id'],))
    trips = cur.fetchall(); cur.close(); conn.close()
    return render_template('my_trips.html', trips=trips)


@app.route('/trips/new', methods=['GET', 'POST'])
@login_required
def create_trip():
    if request.method == 'POST':
        destination = request.form.get('destination', '').strip()
        try:
            start, end = parse_trip_dates(request.form.get('start_date'), request.form.get('end_date'))
            budget = parse_money(request.form.get('budget'), 'Budget')
            if not destination:
                raise ValueError('Destination is required.')
        except ValueError as exc:
            flash(str(exc), 'error')
            return render_template('trip_form.html', trip=request.form, editing=False)
        conn = get_db(); cur = conn.cursor()
        cur.execute('INSERT INTO trips (owner_id,destination,start_date,end_date,budget) VALUES (%s,%s,%s,%s,%s)',
                    (session['user_id'], destination, start, end, budget))
        trip_id = cur.lastrowid; conn.commit(); cur.close(); conn.close()
        flash('Trip created. Add activities to build your itinerary.', 'success')
        return redirect(url_for('trip_detail', trip_id=trip_id))
    return render_template('trip_form.html', trip={}, editing=False)


@app.route('/trips/<int:trip_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_trip(trip_id):
    trip = owned_trip(trip_id)
    if request.method == 'POST':
        destination = request.form.get('destination', '').strip()
        try:
            start, end = parse_trip_dates(request.form.get('start_date'), request.form.get('end_date'))
            budget = parse_money(request.form.get('budget'), 'Budget')
            if not destination:
                raise ValueError('Destination is required.')
        except ValueError as exc:
            flash(str(exc), 'error')
            return render_template('trip_form.html', trip=request.form, editing=True)
        conn = get_db(); cur = conn.cursor(dictionary=True)
        cur.execute('SELECT COUNT(*) AS total FROM activities WHERE trip_id=%s AND (activity_date < %s OR activity_date > %s)',
                    (trip_id, start, end))
        outside = cur.fetchone()['total']
        if outside:
            cur.close(); conn.close()
            flash(f'Dates not changed: {outside} existing activity/activities would fall outside the new trip dates. Update or remove those activities first.', 'error')
            return render_template('trip_form.html', trip={**trip, **request.form}, editing=True)
        cur2 = conn.cursor()
        cur2.execute('UPDATE trips SET destination=%s,start_date=%s,end_date=%s,budget=%s WHERE id=%s AND owner_id=%s',
                     (destination, start, end, budget, trip_id, session['user_id']))
        conn.commit(); cur2.close(); cur.close(); conn.close()
        flash('Trip updated.', 'success')
        return redirect(url_for('trip_detail', trip_id=trip_id))
    return render_template('trip_form.html', trip=trip, editing=True)


@app.route('/trips/<int:trip_id>/delete', methods=['POST'])
@login_required
def delete_trip(trip_id):
    owned_trip(trip_id)
    conn = get_db(); cur = conn.cursor()
    cur.execute('DELETE FROM trips WHERE id=%s AND owner_id=%s', (trip_id, session['user_id']))
    conn.commit(); cur.close(); conn.close()
    flash('Trip deleted.', 'success')
    return redirect(url_for('my_trips'))


@app.route('/trips/<int:trip_id>')
@login_required
def trip_detail(trip_id):
    trip = owned_trip(trip_id)
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute('SELECT * FROM activities WHERE trip_id=%s ORDER BY activity_date, activity_time, id', (trip_id,))
    activities = cur.fetchall()
    total = sum((Decimal(str(a['cost'])) for a in activities), Decimal('0.00'))
    cur.close(); conn.close()
    grouped = {}
    for activity in activities:
        activity_day = activity.get('activity_date')
        # activity_date should be a MySQL DATE. If an older/misconfigured
        # table returns a timedelta, treat it as an offset from trip start.
        if isinstance(activity_day, timedelta):
            activity_day = trip['start_date'] + activity_day
            activity['activity_date'] = activity_day
        elif isinstance(activity_day, datetime):
            activity_day = activity_day.date()
            activity['activity_date'] = activity_day
        elif isinstance(activity_day, str):
            activity_day = date.fromisoformat(activity_day)
            activity['activity_date'] = activity_day
        grouped.setdefault(activity_day, []).append(activity)
    grouped = dict(sorted(grouped.items(), key=lambda item: str(item[0])))
    difference = Decimal(str(trip['budget'])) - total
    return render_template('trip_detail.html', trip=trip, grouped=grouped, total=total, difference=difference,
                           activity_count=len(activities))


@app.route('/trips/<int:trip_id>/activities/new', methods=['GET', 'POST'])
@login_required
def add_activity(trip_id):
    trip = owned_trip(trip_id)
    if request.method == 'POST':
        form = request.form
        try:
            name = form.get('name', '').strip(); place = form.get('place', '').strip()
            category = form.get('category', '').strip()
            try: activity_date = parse_date_input(form.get('activity_date', ''))
            except ValueError as exc: raise ValueError(str(exc))
            activity_time = form.get('activity_time') or None
            cost = parse_money(form.get('cost'), 'Activity cost')
            if not name or not place or not category: raise ValueError('Name, category and place are required.')
            if not (trip['start_date'] <= activity_date <= trip['end_date']):
                raise ValueError('Activity date must fall within the trip start and end dates.')
        except ValueError as exc:
            flash(str(exc), 'error')
            return render_template('activity_form.html', trip=trip, activity=form, editing=False)
        conn = get_db(); cur = conn.cursor()
        cur.execute('INSERT INTO activities (trip_id,name,activity_date,activity_time,category,place,cost) VALUES (%s,%s,%s,%s,%s,%s,%s)',
                    (trip_id, name, activity_date, activity_time, category, place, cost))
        conn.commit(); cur.close(); conn.close()
        flash('Activity added to your itinerary.', 'success')
        return redirect(url_for('trip_detail', trip_id=trip_id))
    return render_template('activity_form.html', trip=trip, activity={}, editing=False)


@app.route('/trips/<int:trip_id>/activities/<int:activity_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_activity(trip_id, activity_id):
    trip = owned_trip(trip_id)
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute('SELECT a.* FROM activities a JOIN trips t ON a.trip_id=t.id WHERE a.id=%s AND a.trip_id=%s AND t.owner_id=%s',
                (activity_id, trip_id, session['user_id']))
    activity = cur.fetchone(); cur.close(); conn.close()
    if not activity: abort(404)
    if request.method == 'POST':
        form = request.form
        try:
            name = form.get('name', '').strip(); place = form.get('place', '').strip(); category = form.get('category', '').strip()
            try: activity_date = parse_date_input(form.get('activity_date', ''))
            except ValueError as exc: raise ValueError(str(exc))
            activity_time = form.get('activity_time') or None
            cost = parse_money(form.get('cost'), 'Activity cost')
            if not name or not place or not category: raise ValueError('Name, category and place are required.')
            if not (trip['start_date'] <= activity_date <= trip['end_date']):
                raise ValueError('Activity date must fall within the trip start and end dates.')
        except ValueError as exc:
            flash(str(exc), 'error')
            return render_template('activity_form.html', trip=trip, activity=form, editing=True)
        conn = get_db(); cur = conn.cursor()
        cur.execute('UPDATE activities SET name=%s,activity_date=%s,activity_time=%s,category=%s,place=%s,cost=%s WHERE id=%s AND trip_id=%s',
                    (name, activity_date, activity_time, category, place, cost, activity_id, trip_id))
        conn.commit(); cur.close(); conn.close()
        flash('Activity updated; trip total has been recalculated.', 'success')
        return redirect(url_for('trip_detail', trip_id=trip_id))
    return render_template('activity_form.html', trip=trip, activity=activity, editing=True)


@app.route('/trips/<int:trip_id>/activities/<int:activity_id>/delete', methods=['POST'])
@login_required
def delete_activity(trip_id, activity_id):
    owned_trip(trip_id)
    conn = get_db(); cur = conn.cursor()
    cur.execute('DELETE a FROM activities a JOIN trips t ON a.trip_id=t.id WHERE a.id=%s AND a.trip_id=%s AND t.owner_id=%s',
                (activity_id, trip_id, session['user_id']))
    conn.commit(); deleted = cur.rowcount; cur.close(); conn.close()
    if not deleted: abort(404)
    flash('Activity removed and total recalculated.', 'success')
    return redirect(url_for('trip_detail', trip_id=trip_id))


@app.route('/explore')
def explore():
    search = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    query = 'SELECT * FROM place_suggestions WHERE 1=1'
    params = []
    if search:
        query += ' AND (name LIKE %s OR destination LIKE %s)'
        params.extend([f'%{search}%', f'%{search}%'])
    if category:
        query += ' AND category=%s'; params.append(category)
    query += ' ORDER BY destination, name'
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute(query, tuple(params)); places = cur.fetchall()
    cur.execute('SELECT DISTINCT category FROM place_suggestions ORDER BY category')
    categories = [row['category'] for row in cur.fetchall()]
    cur.close(); conn.close()
    return render_template('explore.html', places=places, categories=categories, q=search, selected_category=category)


@app.route('/explore/suggest', methods=['GET', 'POST'])
@login_required
def suggest_place():
    if request.method == 'POST':
        name = request.form.get('name', '').strip(); destination = request.form.get('destination', '').strip()
        category = request.form.get('category', '').strip(); description = request.form.get('description', '').strip()
        if not all([name, destination, category, description]):
            flash('Please complete every field.', 'error')
        else:
            conn = get_db(); cur = conn.cursor()
            cur.execute('INSERT INTO place_suggestions (name,destination,category,description,created_by) VALUES (%s,%s,%s,%s,%s)',
                        (name, destination, category, description, session['user_id']))
            conn.commit(); cur.close(); conn.close()
            flash('Place suggestion published to Explore.', 'success')
            return redirect(url_for('explore'))
    return render_template('suggest_place.html')


@app.errorhandler(404)
def not_found(_error):
    return render_template('error.html', title='Page not found', message='This trip or page is unavailable. Private trips can only be opened by their owner.'), 404


if __name__ == '__main__':
    try:
        init_db()
    except mysql.connector.Error as exc:
        raise SystemExit(f'Could not connect to MySQL. Check .env and create the database first. Details: {exc}')
    app.run(debug=True)
