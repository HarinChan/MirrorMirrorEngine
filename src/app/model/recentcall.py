from . import db
from datetime import datetime, timezone

class RecentCall(db.Model):
    """Log of recent calls"""
    __tablename__ = 'recent_calls'
    
    id = db.Column(db.Integer, primary_key=True)
    caller_profile_id = db.Column(db.Integer, db.ForeignKey('profiles.id'), nullable=False)
    # The other party could be null if it was a group call or external, but for now assuming 1:1 or 1:Group
    # Storing the classroom name/ID for display even if the actual call object is complex
    target_classroom_name = db.Column(db.String(255), nullable=True)
    target_classroom_id = db.Column(db.String(50), nullable=True) # ID as string for flexibility
    
    duration_seconds = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    call_type = db.Column(db.String(20)) # outgoing, incoming
    
    # Relationships
    caller_profile = db.relationship('Profile', foreign_keys=[caller_profile_id], backref='call_history')

    def __repr__(self):
        return f'<RecentCall {self.caller_profile_id} -> {self.target_classroom_name}>'