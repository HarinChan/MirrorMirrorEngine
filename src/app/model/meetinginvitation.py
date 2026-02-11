from . import db
from datetime import datetime, timezone

class MeetingInvitation(db.Model):
    """Invitations for scheduled meetings between classrooms"""
    __tablename__ = 'meeting_invitations'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_profile_id = db.Column(db.Integer, db.ForeignKey('profiles.id'), nullable=False)
    receiver_profile_id = db.Column(db.Integer, db.ForeignKey('profiles.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, accepted, declined
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    
    # Foreign key to the meeting created when invitation is accepted
    meeting_id = db.Column(db.Integer, db.ForeignKey('meetings.id'), nullable=True)
    
    # Relationships
    sender = db.relationship('Profile', foreign_keys=[sender_profile_id], backref='sent_invitations')
    receiver = db.relationship('Profile', foreign_keys=[receiver_profile_id], backref='received_invitations')
    meeting = db.relationship('Meeting', backref='invitation')
    
    def __repr__(self):
        return f'<MeetingInvitation {self.id} from {self.sender_profile_id} to {self.receiver_profile_id}>'