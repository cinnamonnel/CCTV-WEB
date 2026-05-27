from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from extensions import db, limiter
from models.user import User
from models.log import Log
from models.login_attempt import LoginAttempt
import bcrypt
from datetime import datetime, timedelta

auth = Blueprint('auth', __name__)

def safe_db_commit():
    """Attempt to commit the current transaction, rolling back on failure."""
    try:
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False

@auth.route('/register', methods=['GET', 'POST'])
@limiter.limit("3 per hour")
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        confirm  = request.form['confirm_password']
        ip_address = request.remote_addr or '0.0.0.0'

        print(f"[REGISTER] Starting registration for username='{username}'")

        # Step 1: Check password confirmation
        if password != confirm:
            print("[REGISTER] FAIL: passwords do not match")
            _log_registration_failure(username, ip_address, 'Passwords do not match')
            flash('Passwords do not match!')
            return redirect(url_for('auth.register'))

        # Step 2: Check password length
        if len(password) < 8:
            print("[REGISTER] FAIL: password too short")
            _log_registration_failure(username, ip_address, 'Password too short')
            flash('Password must be at least 8 characters!')
            return redirect(url_for('auth.register'))

        # Step 3: Check bcrypt hashing works
        try:
            hashed_password = bcrypt.hashpw(
                password.encode('utf-8'),
                bcrypt.gensalt()
            ).decode('utf-8')
            print(f"[REGISTER] OK: bcrypt hashing succeeded, hash length={len(hashed_password)}")
        except Exception as e:
            print(f"[REGISTER] FAIL: bcrypt hashing raised {type(e).__name__}: {e}")
            db.session.rollback()
            flash('Registration failed (password processing error).')
            return redirect(url_for('auth.register'))

        # Step 4: Check if user already exists
        existing_user = _safe_user_query(username)
        if existing_user:
            print(f"[REGISTER] FAIL: username '{username}' already exists")
            _log_registration_failure(username, ip_address, 'Username already exists')
            flash('Username already exists!')
            return redirect(url_for('auth.register'))
        print(f"[REGISTER] OK: username '{username}' is available")

        # Step 5: Count existing users to determine role
        user_count = _safe_user_count()
        role = 'admin' if user_count == 0 else 'user'
        print(f"[REGISTER] OK: user_count={user_count}, role='{role}'")

        # Step 6: Create User object and print its state
        new_user = User(username=username, password=hashed_password, role=role)
        print(f"[REGISTER] OK: User object created, id={new_user.id}, username='{new_user.username}', role='{new_user.role}'")

        # Step 7: Add to session and commit
        try:
            db.session.rollback()  # Clean slate before adding
            db.session.add(new_user)
            db.session.flush()  # Force ID generation so we can read new_user.id
            print(f"[REGISTER] OK: user flushed to session, new_user.id={new_user.id}")

            log = Log(
                username=username,
                action='Registered an account',
                ip_address=ip_address,
                status='Success',
                user_id=new_user.id  # Now new_user.id is populated
            )
            db.session.add(log)
            print("[REGISTER] OK: log entry created, committing...")
            db.session.commit()
            print(f"[REGISTER] SUCCESS: committed user id={new_user.id}, log created")
        except Exception as e:
            print(f"[REGISTER] FAIL: exception during add/commit: {type(e).__name__}: {e}")
            db.session.rollback()
            flash('Registration failed. Please try again.')
            return redirect(url_for('auth.register'))

        flash('Registration successful! Please login.')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        ip_address = request.remote_addr or '0.0.0.0'

        login_attempt = _get_or_create_login_attempt(ip_address)
        if not login_attempt:
            login_attempt = LoginAttempt(ip_address=ip_address, failed_attempts=0)

        # Check if IP is locked
        is_locked = login_attempt.locked_until and login_attempt.locked_until > datetime.utcnow()

        user = _safe_user_query(username)

        # Determine login success
        login_success = user and bcrypt.checkpw(
            password.encode('utf-8'),
            user.password.encode('utf-8')
        )

        if login_success:
            _reset_failed_attempts(login_attempt)

            session['username'] = username
            session['user_id'] = user.id

            _log_action(
                username=username,
                action='Logged in',
                ip_address=ip_address,
                status='Success',
                user_id=user.id
            )

            return redirect(url_for('camera.dashboard'))
        else:
            # Failed login - increment failed attempts
            _increment_failed_attempts(login_attempt)

            # Log the failed attempt
            reason = (
                'Account locked due to too many failed attempts' if is_locked
                else ('User not found' if not user else 'Wrong password')
            )
            _log_action(
                username=username or 'unknown',
                action='Login attempt',
                ip_address=ip_address,
                status='Failed',
                reason=reason
            )

            # Lock account if 5 or more failed attempts (and not already locked)
            if login_attempt.failed_attempts >= 5 and not is_locked:
                _lock_account(login_attempt)
                flash_message = 'Account locked due to too many failed attempts. Please try again later.'
            elif is_locked:
                flash_message = 'Account locked due to too many failed attempts. Please try again later.'
            else:
                flash_message = 'Login failed'

            flash(flash_message)
            return redirect(url_for('auth.login'))

    return render_template('login.html')


@auth.route('/logout')
def logout():
    username = session.get('username')
    user_id = session.get('user_id')
    ip_address = request.remote_addr or '0.0.0.0'

    if username:
        _log_action(
            username=username,
            action='Logged out',
            ip_address=ip_address,
            status='Success',
            user_id=user_id
        )

    session.pop('username', None)
    session.pop('user_id', None)
    return redirect(url_for('auth.login'))


# ---- Helper functions ----

def _safe_user_query(username):
    """Safely query a user, returning None on any database error."""
    try:
        db.session.rollback()
        return User.query.filter_by(username=username).first()
    except Exception:
        db.session.rollback()
        return None


def _safe_user_count():
    """Safely count users, returning 0 on any database error."""
    try:
        db.session.rollback()
        return User.query.count()
    except Exception:
        db.session.rollback()
        return 0


def _get_or_create_login_attempt(ip_address):
    """Get or create a login attempt record."""
    try:
        db.session.rollback()
        record = LoginAttempt.query.filter_by(ip_address=ip_address).first()
        if not record:
            record = LoginAttempt(ip_address=ip_address, failed_attempts=0)
            db.session.add(record)
            db.session.commit()
        return record
    except Exception:
        db.session.rollback()
        return None


def _reset_failed_attempts(login_attempt):
    """Reset failed attempts counter."""
    try:
        db.session.rollback()
        login_attempt.failed_attempts = 0
        login_attempt.locked_until = None
        db.session.commit()
    except Exception:
        db.session.rollback()


def _increment_failed_attempts(login_attempt):
    """Increment failed attempts counter."""
    try:
        db.session.rollback()
        login_attempt.failed_attempts += 1
        db.session.commit()
    except Exception:
        db.session.rollback()
        login_attempt.failed_attempts += 1


def _lock_account(login_attempt):
    """Lock an account for 15 minutes."""
    try:
        db.session.rollback()
        login_attempt.locked_until = datetime.utcnow() + timedelta(minutes=15)
        db.session.commit()
    except Exception:
        db.session.rollback()


def _log_action(username, action, ip_address, status, reason=None, user_id=None):
    """Safely log an action to the database."""
    try:
        db.session.rollback()
        log = Log(
            username=username,
            action=action,
            ip_address=ip_address,
            status=status,
            reason=reason,
            user_id=user_id
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()


def _log_registration_failure(username, ip_address, reason):
    """Safely log a registration failure."""
    _log_action(
        username=username or 'unknown',
        action='Registration attempt',
        ip_address=ip_address or '0.0.0.0',
        status='Failed',
        reason=reason
    )