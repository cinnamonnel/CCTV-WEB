from flask import Blueprint, render_template, redirect, url_for, session, request, flash
from models.log import Log
from models.user import User

logs = Blueprint('logs', __name__)

def is_admin():
    """Check if the logged-in user is an admin."""
    if 'username' not in session:
        return False
    user = User.query.filter_by(username=session['username']).first()
    return user and user.role == 'admin'

@logs.route('/logs')
def view_logs():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    # If user is not admin, they can only view their own logs
    if not is_admin():
        filter_user = session['username']
    else:
        filter_user = request.args.get('user', '')

    if filter_user:
        # Non-admin users can only filter by their own username (ignoring other attempts)
        if not is_admin() and filter_user != session['username']:
            flash('Access denied: You can only view your own logs.')
            return redirect(url_for('logs.view_logs'))
        all_logs = Log.query.filter_by(username=filter_user).order_by(Log.timestamp.desc()).all()
    else:
        # Show all logs only for admin; for non-admin, this case is handled above (filter_user set to username)
        if is_admin():
            all_logs = Log.query.order_by(Log.timestamp.desc()).all()
        else:
            # This should not happen because of the above logic, but as fallback:
            all_logs = Log.query.filter_by(username=session['username']).order_by(Log.timestamp.desc()).all()

    return render_template('logs.html', logs=all_logs, filter_user=filter_user)
