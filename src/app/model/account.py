from . import db
from datetime import datetime, timezone

class Account(db.Model):
    __tablename__ = 'accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)  # HASHED password
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    account_metadata = db.Column(db.String(120), nullable=True)
    organization = db.Column(db.String(120), nullable=True)

    # WebEx OAuth Tokens
    webex_access_token = db.Column(db.String(512), nullable=True)
    webex_refresh_token = db.Column(db.String(512), nullable=True)
    webex_token_expires_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    profiles = db.relationship('Profile', backref='account', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Account {self.email}>'

