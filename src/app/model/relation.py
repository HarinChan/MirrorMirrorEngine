from . import db
from datetime import datetime, timezone

class Relation(db.Model):
    """Profile-to-Profile connections (friendships/connections)"""
    __tablename__ = 'relations'
    
    id = db.Column(db.Integer, primary_key=True)
    from_profile_id = db.Column(db.Integer, db.ForeignKey('profiles.id'), nullable=False)
    to_profile_id = db.Column(db.Integer, db.ForeignKey('profiles.id'), nullable=False)
    status = db.Column(db.Integer, default='pending')  # pending, accepted, blocked
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    
    __table_args__ = (
        db.UniqueConstraint('from_profile_id', 'to_profile_id', name='unique_relation'),
    )
    
    def __repr__(self):
        return f'<Relation {self.from_profile_id} -> {self.to_profile_id}>'

