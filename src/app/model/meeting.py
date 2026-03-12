from . import db
from datetime import datetime, timezone

meeting_participants = db.Table('meeting_participants',
    db.Column('meeting_id', db.Integer, db.ForeignKey('meetings.id'), primary_key=True),
    db.Column('profile_id', db.Integer, db.ForeignKey('profiles.id'), primary_key=True)
)

class Meeting(db.Model):
    """Video meetings scheduled via WebEx"""
    __tablename__ = 'meetings'
    
    id = db.Column(db.Integer, primary_key=True)
    webex_id = db.Column(db.String(255), nullable=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    web_link = db.Column(db.String(1000), nullable=True)  # Nullable until invitation accepted
    password = db.Column(db.String(255), nullable=True)
    visibility = db.Column(db.String(20), default='private', nullable=False)  # private, public
    status = db.Column(db.String(30), default='pending_setup', nullable=False)  # pending_setup, active, cancelled
    max_participants = db.Column(db.Integer, nullable=True)
    join_count = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    
    creator_id = db.Column(db.Integer, db.ForeignKey('profiles.id'), nullable=False)
    
    # Relationships
    creator = db.relationship('Profile', foreign_keys=[creator_id], backref='created_meetings')
    participants = db.relationship('Profile', secondary=meeting_participants, lazy='subquery',
        backref=db.backref('meetings', lazy=True))
    
    @property
    def friends(self):
        """Return list of profiles that are friends (accepted relation)"""
        # This is a helper, but actual query logic is often in the route for customization
        pass

    def __repr__(self):
        return f'<Meeting {self.title}>'