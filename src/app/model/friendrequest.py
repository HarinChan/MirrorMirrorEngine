from . import db
from datetime import datetime, timezone

class FriendRequest(db.Model):
    """Pending friend requests between profiles (classrooms)"""
    __tablename__ = 'friend_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_profile_id = db.Column(db.Integer, db.ForeignKey('profiles.id'), nullable=False)
    receiver_profile_id = db.Column(db.Integer, db.ForeignKey('profiles.id'), nullable=False)
    status = db.Column(db.String(20), default='pending') # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    
    # Relationships
    sender = db.relationship('Profile', foreign_keys=[sender_profile_id], backref='sent_requests')
    receiver = db.relationship('Profile', foreign_keys=[receiver_profile_id], backref='received_requests')

    def __repr__(self):
        return f'<FriendRequest {self.sender_profile_id} -> {self.receiver_profile_id}>'