"""Flask application for trip planning, accounts, activities, and public place suggestions."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps
from pathlib import Path
from urllib.parse import quote_plus
import os

from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.engine import URL
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'change-this-local-development-key')

# SQLAlchemy builds the connection URL and manages connections/sessions.
app.config['SQLALCHEMY_DATABASE_URI'] = URL.create(
    drivername='mysql+mysqlconnector',
    username=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD', '0000'),
    host=os.getenv('DB_HOST', '127.0.0.1'),
    port=int(os.getenv('DB_PORT', '3306')),
    database=os.getenv('DB_NAME', 'trip_planner_orm'),
    query={'charset': 'utf8mb4'},
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}

from extensions import db
from models import User, Trip, Activity, PlaceSuggestion

db.init_app(app)


def init_db():
    """Create ORM-managed tables. The configured database must already exist."""
    with app.app_context():
        db.create_all()


def login_required(view):
    """Protect a view so only authenticated users can access it."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        """Redirect unauthenticated visitors to the login page."""
        if 'user_id' not in session:
            flash('Please log in to continue.', 'info')
            return redirect(url_for('login', next=request.path))
        return view(*args, **kwargs)
    return wrapped


def owned_trip(trip_id):
    """Return a trip owned by the current user or raise a 404 error."""
    trip = Trip.query.filter_by(id=trip_id, owner_id=session['user_id']).first()
    if trip is None:
        abort(404)
    return trip


def parse_money(value, label):
    """Validate a non-negative monetary value and normalize it to two decimals."""
    try:
        amount = Decimal((value or '').strip())
        if not amount.is_finite() or amount < 0:
            raise InvalidOperation
        return amount.quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError):
        raise ValueError(f'{label} must be a valid number and cannot be negative.')


def parse_date_input(value):
    """Accept DD/MM/YYYY and ISO dates for compatibility with existing forms."""
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
    """Parse and validate trip start and end dates."""
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
    """Format a monetary value for display in templates."""
    return f'₹{Decimal(str(value or 0)):,.2f}'


@app.template_filter('prettydate')
def prettydate(value):
    """Format a date as day/month/year for display."""
    if value is None:
        return 'Date not set'
    if isinstance(value, timedelta):
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
    """Format a time value for display in templates."""
    if value is None or value == '':
        return 'Any time'
    if isinstance(value, timedelta):
        seconds = int(value.total_seconds()) % 86400
        value = (datetime.min + timedelta(seconds=seconds)).time()
    if isinstance(value, str):
        for fmt in ('%H:%M:%S', '%H:%M'):
            try:
                value = datetime.strptime(value, fmt).time()
                break
            except ValueError:
                pass
        if isinstance(value, str):
            return value
    if hasattr(value, 'strftime'):
        return value.strftime('%I:%M %p')
    return str(value)


@app.route('/')
def home():
    """Render the public home page."""
    samples = [
        {'name': 'Araku Valley', 'description': 'Coffee plantations, green hills and scenic viewpoints.', 'category': 'Nature', 'image': 'https://images.unsplash.com/photo-1472396961693-142e6e269027?auto=format&fit=crop&w=1000&q=85'},
        {'name': 'Hyderabad', 'description': 'Historic landmarks, food streets and city experiences.', 'category': 'City', 'image': 'https://images.unsplash.com/photo-1565552629476-3f7c4f2f2d93?auto=format&fit=crop&w=1000&q=85'},
        {'name': 'Tirupati', 'description': 'Temples, local culture and nearby viewpoints.', 'category': 'Culture', 'image': 'https://images.unsplash.com/photo-1606293926075-69a00db032d4?auto=format&fit=crop&w=1000&q=85'},
    ]
    return render_template('home.html', samples=samples)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new user or display the registration form."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if len(username) < 3 or len(username) > 80 or len(password) < 6:
            flash('Username must be 3–80 characters and password at least 6 characters.', 'error')
            return render_template('register.html')
        user = User(username=username, password_hash=generate_password_hash(password))
        try:
            db.session.add(user)
            db.session.commit()
            flash('Account created. Please log in.', 'success')
            return redirect(url_for('login'))
        except IntegrityError:
            db.session.rollback()
            flash('That username is already taken.', 'error')
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception('Unable to register user')
            flash('Could not create the account. Please try again.', 'error')
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Authenticate a user or display the login form."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session.clear()
            session['user_id'] = user.id
            session['username'] = user.username
            flash(f'Welcome, {user.username}!', 'success')
            return redirect(url_for('my_trips'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')


@app.route('/logout', methods=['POST'])
def logout():
    """End the current user's session."""
    session.clear()
    flash('You have logged out.', 'info')
    return redirect(url_for('home'))


@app.route('/trips')
@login_required
def my_trips():
    """Display trips belonging to the authenticated user."""
    trips = Trip.query.filter_by(owner_id=session['user_id']).order_by(Trip.start_date.desc()).all()
    for trip in trips:
        trip.activity_count = len(trip.activities)
        trip.total_cost = sum((Decimal(str(a.cost or 0)) for a in trip.activities), Decimal('0.00'))
    return render_template('my_trips.html', trips=trips)


@app.route('/trips/new', methods=['GET', 'POST'])
@login_required
def create_trip():
    """Create a trip for the authenticated user."""
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
        trip = Trip(owner_id=session['user_id'], destination=destination, start_date=start, end_date=end, budget=budget)
        db.session.add(trip)
        db.session.commit()
        flash('Trip created. Add activities to build your itinerary.', 'success')
        return redirect(url_for('trip_detail', trip_id=trip.id))
    return render_template('trip_form.html', trip={}, editing=False)


@app.route('/trips/<int:trip_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_trip(trip_id):
    """Update an existing trip owned by the authenticated user."""
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
        outside = Activity.query.filter(
            Activity.trip_id == trip_id,
            or_(Activity.activity_date < start, Activity.activity_date > end)
        ).count()
        if outside:
            flash(f'Dates not changed: {outside} existing activity/activities would fall outside the new trip dates. Update or remove those activities first.', 'error')
            return render_template('trip_form.html', trip={**trip.__dict__, **request.form}, editing=True)
        trip.destination = destination
        trip.start_date = start
        trip.end_date = end
        trip.budget = budget
        db.session.commit()
        flash('Trip updated.', 'success')
        return redirect(url_for('trip_detail', trip_id=trip_id))
    return render_template('trip_form.html', trip=trip, editing=True)


@app.route('/trips/<int:trip_id>/delete', methods=['POST'])
@login_required
def delete_trip(trip_id):
    """Delete a trip owned by the authenticated user."""
    trip = owned_trip(trip_id)
    db.session.delete(trip)
    db.session.commit()
    flash('Trip deleted.', 'success')
    return redirect(url_for('my_trips'))


@app.route('/trips/<int:trip_id>')
@login_required
def trip_detail(trip_id):
    """Display a trip and its scheduled activities."""
    trip = owned_trip(trip_id)
    activities = Activity.query.filter_by(trip_id=trip_id).order_by(
        Activity.activity_date, Activity.activity_time, Activity.id
    ).all()
    total = sum((Decimal(str(a.cost or 0)) for a in activities), Decimal('0.00'))
    grouped = {}
    for activity in activities:
        grouped.setdefault(activity.activity_date, []).append(activity)
    grouped = dict(sorted(grouped.items(), key=lambda item: str(item[0])))
    difference = Decimal(str(trip.budget)) - total
    return render_template('trip_detail.html', trip=trip, grouped=grouped, total=total,
                           difference=difference, activity_count=len(activities))


@app.route('/trips/<int:trip_id>/activities/new', methods=['GET', 'POST'])
@login_required
def add_activity(trip_id):
    """Add an activity to a trip owned by the authenticated user."""
    trip = owned_trip(trip_id)
    if request.method == 'POST':
        form = request.form
        try:
            name = form.get('name', '').strip()
            place = form.get('place', '').strip()
            category = form.get('category', '').strip()
            activity_date = parse_date_input(form.get('activity_date', ''))
            raw_time = form.get('activity_time') or None
            activity_time = datetime.strptime(raw_time, '%H:%M').time() if raw_time else None
            cost = parse_money(form.get('cost'), 'Activity cost')
            if not name or not place or not category:
                raise ValueError('Name, category and place are required.')
            if not (trip.start_date <= activity_date <= trip.end_date):
                raise ValueError('Activity date must fall within the trip start and end dates.')
        except ValueError as exc:
            flash(str(exc), 'error')
            return render_template('activity_form.html', trip=trip, activity=form, editing=False)
        activity = Activity(trip_id=trip_id, name=name, activity_date=activity_date,
                            activity_time=activity_time, category=category, place=place, cost=cost)
        db.session.add(activity)
        db.session.commit()
        flash('Activity added to your itinerary.', 'success')
        return redirect(url_for('trip_detail', trip_id=trip_id))
    return render_template('activity_form.html', trip=trip, activity={}, editing=False)


@app.route('/trips/<int:trip_id>/activities/<int:activity_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_activity(trip_id, activity_id):
    """Update an activity belonging to the selected trip."""
    trip = owned_trip(trip_id)
    activity = Activity.query.filter_by(id=activity_id, trip_id=trip_id).first()
    if activity is None:
        abort(404)
    if request.method == 'POST':
        form = request.form
        try:
            name = form.get('name', '').strip()
            place = form.get('place', '').strip()
            category = form.get('category', '').strip()
            activity_date = parse_date_input(form.get('activity_date', ''))
            raw_time = form.get('activity_time') or None
            activity_time = datetime.strptime(raw_time, '%H:%M').time() if raw_time else None
            cost = parse_money(form.get('cost'), 'Activity cost')
            if not name or not place or not category:
                raise ValueError('Name, category and place are required.')
            if not (trip.start_date <= activity_date <= trip.end_date):
                raise ValueError('Activity date must fall within the trip start and end dates.')
        except ValueError as exc:
            flash(str(exc), 'error')
            return render_template('activity_form.html', trip=trip, activity=form, editing=True)
        activity.name = name
        activity.place = place
        activity.category = category
        activity.activity_date = activity_date
        activity.activity_time = activity_time
        activity.cost = cost
        db.session.commit()
        flash('Activity updated; trip total has been recalculated.', 'success')
        return redirect(url_for('trip_detail', trip_id=trip_id))
    return render_template('activity_form.html', trip=trip, activity=activity, editing=True)


@app.route('/trips/<int:trip_id>/activities/<int:activity_id>/delete', methods=['POST'])
@login_required
def delete_activity(trip_id, activity_id):
    """Delete an activity belonging to the selected trip."""
    owned_trip(trip_id)
    activity = Activity.query.filter_by(id=activity_id, trip_id=trip_id).first()
    if activity is None:
        abort(404)
    db.session.delete(activity)
    db.session.commit()
    flash('Activity removed and total recalculated.', 'success')
    return redirect(url_for('trip_detail', trip_id=trip_id))


@app.route('/explore')
def explore():
    """Display public place suggestions submitted by users."""
    search = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    query = PlaceSuggestion.query
    if search:
        pattern = f'%{search}%'
        query = query.filter(or_(PlaceSuggestion.name.ilike(pattern), PlaceSuggestion.destination.ilike(pattern)))
    if category:
        query = query.filter(PlaceSuggestion.category == category)
    places = query.order_by(PlaceSuggestion.destination, PlaceSuggestion.name).all()
    categories = [row[0] for row in db.session.query(PlaceSuggestion.category).distinct().order_by(PlaceSuggestion.category).all()]
    return render_template('explore.html', places=places, categories=categories, q=search, selected_category=category)


@app.route('/explore/suggest', methods=['GET', 'POST'])
@login_required
def suggest_place():
    """Submit a place suggestion or display the suggestion form."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        destination = request.form.get('destination', '').strip()
        category = request.form.get('category', '').strip()
        description = request.form.get('description', '').strip()
        if not all([name, destination, category, description]):
            flash('Please complete every field.', 'error')
        else:
            suggestion = PlaceSuggestion(name=name, destination=destination, category=category,
                                         description=description, created_by=session['user_id'])
            db.session.add(suggestion)
            db.session.commit()
            flash('Place suggestion published to Explore.', 'success')
            return redirect(url_for('explore'))
    return render_template('suggest_place.html')


@app.errorhandler(404)
def not_found(_error):
    """Render the custom page for resources that cannot be found."""
    return render_template('error.html', title='Page not found', message='This trip or page is unavailable. Private trips can only be opened by their owner.'), 404


if __name__ == '__main__':
    try:
        init_db()
    except SQLAlchemyError as exc:
        raise SystemExit(f'Could not connect to MySQL or create tables. Check .env and create the database first. Details: {exc}')
    app.run(debug=True)
