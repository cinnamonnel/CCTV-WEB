from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from extensions import db, limiter
from models.user import User
from models.log import Log
from models.login_attempt import LoginAttempt
import bcrypt
from datetime import datetime, timedelta

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
@limiter.limit("3 per hour")
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        confirm  = request.form['confirm_password']

        if password != confirm:
            log = Log(
                username=username or 'unknown',
                action='Registration attempt',
                ip_address=request.remote_addr,
                status='Failed',
                reason='Passwords do not match'
            )
            db.session.add(log)
            db.session.commit()
            flash('Passwords do not match!')
            return redirect(url_for('auth.register'))

        if len(password) < 8:
            log = Log(
                username=username or 'unknown',
                action='Registration attempt',
                ip_address=request.remote_addr,
                status='Failed',
                reason='Password too short'
            )
            db.session.add(log)
            db.session.commit()
            flash('Password must be at least 8 characters!')
            return redirect(url_for('auth.register'))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            log = Log(
                username=username,
                action='Registration attempt',
                ip_address=request.remote_addr,
                status='Failed',
                reason='Username already exists'
            )
            db.session.add(log)
            db.session.commit()
            flash('Username already exists!')
            return redirect(url_for('auth.register'))

        hashed_password = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        # Determine role: if no users exist, make this user an admin
        user_count = User.query.count()
        role = 'admin' if user_count == 0 else 'user'

        new_user = User(username=username, password=hashed_password, role=role)
        db.session.add(new_user)

        log = Log(
            username=username,
            action='Registered an account',
            ip_address=request.remote_addr,
            status='Success',
            user_id=new_user.id
        )
        db.session.add(log)
        db.session.commit()

        flash('Registration successful! Please login.')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        ip_address = request.remote_addr

        # Get or create login attempt record for this IP
        login_attempt = LoginAttempt.query.filter_by(ip_address=ip_address).first()
        if not login_attempt:
            login_attempt = LoginAttempt(ip_address=ip_address, failed_attempts=0)
            db.session.add(login_attempt)

        # Check if IP is locked
        is_locked = login_attempt.locked_until and login_attempt.locked_until > datetime.utcnow()

        user = User.query.filter_by(username=username).first()

        # Determine login success
        login_success = user and bcrypt.checkpw(
            password.encode('utf-8'),
            user.password.encode('utf-8')
        )

        if login_success:
            # Successful login - reset failed attempts and lock time
            login_attempt.failed_attempts = 0
            login_attempt.locked_until = None
            db.session.commit()

            session['username'] = username
            session['user_id'] = user.id

            log = Log(
                username=username,
                action='Logged in',
                ip_address=ip_address,
                status='Success',
                user_id=user.id
            )
            db.session.add(log)
            db.session.commit()

            return redirect(url_for('camera.dashboard'))
        else:
            # Failed login - increment failed attempts
            login_attempt.failed_attempts += 1

            # Log the failed attempt
            log = Log(
                username=username or 'unknown',
                action='Login attempt',
                ip_address=ip_address,
                status='Failed',
                reason='Account locked due to too many failed attempts' if is_locked else ('User not found' if not user else 'Wrong password')
            )
            db.session.add(log)

            # Lock account if 5 or more failed attempts (and not already locked)
            if login_attempt.failed_attempts >= 5 and not is_locked:
                login_attempt.locked_until = datetime.utcnow() + timedelta(minutes=15)
                flash_message = 'Account locked due to too many failed attempts. Please try again later.'
            elif is_locked:
                flash_message = 'Account locked due to too many failed attempts. Please try again later.'
            else:
                flash_message = 'Login failed'

            db.session.commit()
            flash(flash_message)
            return redirect(url_for('auth.login'))

    return render_template('login.html')


@auth.route('/logout')
def logout():
    username = session.get('username')

    if username:
        user = User.query.filter_by(username=username).first()
        log = Log(
            username=username,
            action='Logged out',
            ip_address=request.remote_addr,
            status='Success',
            user_id=user.id if user else None
        )
        db.session.add(log)
        db.session.commit()

    session.pop('username', None)
    return redirect(url_for('auth.login'))
