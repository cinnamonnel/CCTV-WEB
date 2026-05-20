from flask import Blueprint, render_template, redirect, url_for, session, request
from models.log import Log

logs = Blueprint('logs', __name__)

@logs.route('/logs')
def view_logs():
    if 'username' not in session:
        return redirect(url_for('auth.login'))

    filter_user = request.args.get('user', '')

    if filter_user:
        all_logs = Log.query.filter_by(username=filter_user).order_by(Log.timestamp.desc()).all()
    else:
        all_logs = Log.query.order_by(Log.timestamp.desc()).all()

    return render_template('logs.html', logs=all_logs, filter_user=filter_user)
