from flask import Blueprint, render_template, redirect, url_for, session, request, flash
from extensions import db
from models.log import Log
from models.user import User

logs = Blueprint('logs', __name__)


def is_admin():
    """Check if the logged-in user is an admin. Returns False on any DB error."""
    if 'username' not in session:
        return False
    try:
        db.session.rollback()
        user = User.query.filter_by(username=session['username']).first()
        return bool(user and user.role == 'admin')
    except Exception:
        db.session.rollback()
        return False


def safe_get_user():
    """Safely get the current user object, returning None on error."""
    if 'username' not in session:
        return None
    try:
        db.session.rollback()
        return User.query.filter_by(username=session['username']).first()
    except Exception:
        db.session.rollback()
        return None


def safe_query_logs(filter_username=None, order_desc=True):
    """Safely query logs, returning (logs_list, error_occurred)."""
    try:
        db.session.rollback()
        query = Log.query
        if filter_username:
            query = query.filter_by(username=filter_username)
        if order_desc:
            query = query.order_by(Log.timestamp.desc())
        return query.all(), False
    except Exception:
        db.session.rollback()
        return [], True


@logs.route('/logs')
def view_logs():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    admin = is_admin()
    current_username = session['username']

    if not admin:
        filter_user = current_username
    else:
        filter_user = request.args.get('user', '').strip()

    # Query logs safely
    all_logs, query_failed = safe_query_logs(
        filter_username=filter_user if filter_user else None,
        order_desc=True
    )

    if query_failed:
        flash('Could not retrieve logs. Please try again.', 'error')
        all_logs = []

    return render_template('logs.html', logs=all_logs, filter_user=filter_user)