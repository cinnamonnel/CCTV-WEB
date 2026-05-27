import os
from dotenv import load_dotenv
from flask import Flask, request, redirect, url_for, session, render_template
from models.log import Log
from extensions import db, limiter
from werkzeug.exceptions import HTTPException
from sqlalchemy import inspect, text
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from datetime import timedelta

load_dotenv()

_secret_key = os.getenv('SECRET_KEY')
if not _secret_key:
    raise RuntimeError("SECRET_KEY environment variable is not set. Cannot start application without it.")

app = Flask(__name__)
app.config['SECRET_KEY'] = _secret_key
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

database_url = os.getenv('DATABASE_URL')
database_public_url = os.getenv('DATABASE_PUBLIC_URL')

# If DATABASE_URL is PostgreSQL (Railway), try it first; fall back to SQLite or DATABASE_PUBLIC_URL
if database_url and database_url.startswith('postgresql://'):
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            pass
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    except OperationalError:
        print("PostgreSQL connection failed. Falling back to SQLite for local development.")
        if database_public_url and database_public_url.startswith('postgresql://'):
            app.config['SQLALCHEMY_DATABASE_URI'] = database_public_url
        else:
            app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'cctv_web.db')
elif database_public_url and database_public_url.startswith('postgresql://'):
    try:
        engine = create_engine(database_public_url)
        with engine.connect() as conn:
            pass
        app.config['SQLALCHEMY_DATABASE_URI'] = database_public_url
    except OperationalError:
        print("DATABASE_PUBLIC_URL connection failed. Falling back to SQLite.")
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'cctv_web.db')
elif database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'cctv_web.db')

limiter.init_app(app)
db.init_app(app)

def get_client_ip():
    """Get client IP address, taking into account proxies and load balancers."""
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
    elif request.headers.getlist("X-Real-IP"):
        ip = request.headers.getlist("X-Real-IP")[0]
    else:
        ip = request.remote_addr
    return ip

def ensure_schema_migrations():
    """Ensure all tables have required columns, adding missing ones."""
    with app.app_context():
        print("Database URI:", app.config['SQLALCHEMY_DATABASE_URI'])
        print("Engine URL:", db.engine.url)
        inspector = inspect(db.engine)

        # Migrate users table (add role column if missing)
        if inspector.has_table("users"):
            existing_user_columns = [col['name'] for col in inspector.get_columns('users')]
            print("Existing columns in users table:", existing_user_columns)
            with db.engine.connect() as conn:
                trans = conn.begin()
                try:
                    if 'role' not in existing_user_columns:
                        conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user'"))
                        print("Added role column to users table")
                    trans.commit()
                    print("Users table schema update completed successfully")
                except Exception as e:
                    trans.rollback()
                    print(f"Error updating users table schema: {e}")

        # Migrate logs table (add missing columns if any)
        if not inspector.has_table("logs"):
            print("Logs table does not exist, will be created by db.create_all()")
            return

        existing_log_columns = [col['name'] for col in inspector.get_columns('logs')]
        print("Existing columns in logs table:", existing_log_columns)

        with db.engine.connect() as conn:
            trans = conn.begin()
            try:
                if 'ip_address' not in existing_log_columns:
                    conn.execute(text("ALTER TABLE logs ADD COLUMN ip_address VARCHAR(45)"))
                    print("Added ip_address column to logs table")

                if 'status' not in existing_log_columns:
                    conn.execute(text("ALTER TABLE logs ADD COLUMN status VARCHAR(20) DEFAULT 'Success'"))
                    print("Added status column to logs table")

                if 'reason' not in existing_log_columns:
                    conn.execute(text("ALTER TABLE logs ADD COLUMN reason VARCHAR(255)"))
                    print("Added reason column to logs table")

                if 'user_id' not in existing_log_columns:
                    conn.execute(text("ALTER TABLE logs ADD COLUMN user_id INTEGER"))
                    print("Added user_id column to logs table")

                trans.commit()
                print("Logs table schema update completed successfully")
            except Exception as e:
                trans.rollback()
                print(f"Error updating logs table schema: {e}")

# Apply schema fixes on startup
ensure_schema_migrations()

# Logging middleware for unauthorized access
@app.before_request
def log_unauthorized_access():
    # Skip logging for static files and auth routes to avoid noise
    if request.endpoint and ('static' in request.endpoint or request.endpoint.startswith('auth.')):
        return

    # Check if user is trying to access protected routes without login
    if 'username' not in session and request.endpoint:
        # Allow access to login and register pages
        if request.endpoint not in ['auth.login', 'auth.register', 'auth.logout']:
            ip_address = get_client_ip()
            try:
                db.session.rollback()
                log = Log(
                    username='Unknown',
                    action=f'Unauthorized access to {request.path}',
                    ip_address=ip_address,
                    status='Denied',
                    reason='Not logged in'
                )
                db.session.add(log)
                db.session.commit()
            except Exception:
                db.session.rollback()

# Specific error handlers for clean logging
@app.errorhandler(404)
def not_found_error(_):
    ip_address = get_client_ip()
    username = session.get('username', 'Unknown')

    try:
        db.session.rollback()
        log = Log(
            username=username,
            action='Page not found',
            ip_address=ip_address,
            status='Failed',
            reason='Page not found'
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()

    return render_template('error.html', message="Page not found"), 404

@app.errorhandler(429)
def rate_limit_error(_):
    ip_address = get_client_ip()
    username = session.get('username', 'Unknown')

    try:
        db.session.rollback()
        log = Log(
            username=username,
            action='Rate limit exceeded',
            ip_address=ip_address,
            status='Failed',
            reason='Too many attempts'
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()

    return render_template('error.html',
        message="Too many attempts. Please wait 15 minutes before trying again."), 429

# Global error handler for other exceptions
@app.errorhandler(Exception)
def log_exception(e):
    ip_address = get_client_ip()
    username = session.get('username', 'Unknown')

    # Determine reason based on error type
    if isinstance(e, HTTPException):
        if e.code == 404:
            reason = 'Page not found'  # Should be caught by 404 handler above
        elif e.code == 429:
            reason = 'Too many attempts'  # Should be caught by 429 handler above
        else:
            reason = f'HTTP {e.code} error'
    else:
        reason = 'Application error'

    try:
        db.session.rollback()
        log = Log(
            username=username,
            action='Application error',
            ip_address=ip_address,
            status='Failed',
            reason=reason
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()

    # Handle rate limit errors specifically (catch any that bypass specific handler)
    if 'RateLimitExceeded' in type(e).__name__:
        return render_template('error.html',
            message="Too many attempts. Please wait 15 minutes before trying again."), 429

    # Handle other HTTP errors
    if isinstance(e, HTTPException):
        return render_template('error.html',
            message=str(e)), e.code

    # Generic server error
    return render_template('error.html',
        message="Something went wrong. Please try again."), 500

from routes.auth import auth
from routes.camera import camera
from routes.logs import logs

app.register_blueprint(auth)
app.register_blueprint(camera)
app.register_blueprint(logs)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('camera.dashboard'))
    return redirect(url_for('auth.login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)