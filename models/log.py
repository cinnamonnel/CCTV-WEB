from extensions import db
from datetime import datetime, timezone, timedelta

class Log(db.Model):
    __tablename__ = 'logs'
    id        = db.Column(db.Integer, primary_key=True)
    username  = db.Column(db.String(80), nullable=True)  # Stores username when known, or 'Unknown'
    user_id   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Reference to user if logged in
    action    = db.Column(db.String(255), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4 or IPv6
    status    = db.Column(db.String(20), nullable=False, default='Success')  # Success, Failed, Denied
    reason    = db.Column(db.String(255), nullable=True)  # Reason for failure
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone(timedelta(hours=8))))

    # Relationship to User model
    user = db.relationship('User', backref=db.backref('logs', lazy=True))

    def __repr__(self):
        return f'<Log {self.username} - {self.action} [{self.status}]>'
