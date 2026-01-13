from src.app.__init__ import db
from datetime import datetime, timezone

class Account(db.Model):
    __tablename__ = 'accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)  # HASHED password
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    metadata = db.Column(db.String(120), nullable=True)
    
    # Relationships
    classrooms = db.relationship('Profile', backref='account', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Account {self.email}>'

