from . import db
from datetime import datetime, timezone


# Many-to-many table for conversation participants
conversation_participants = db.Table('conversation_participants',
    db.Column('conversation_id', db.Integer, db.ForeignKey('conversations.id'), primary_key=True),
    db.Column('profile_id', db.Integer, db.ForeignKey('profiles.id'), primary_key=True),
    db.Column('joined_at', db.DateTime, default=datetime.now(timezone.utc))
)


class Conversation(db.Model):
    """Chat conversations between profiles (classrooms)"""
    __tablename__ = 'conversations'
    
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), default='direct', nullable=False)  # direct, group
    title = db.Column(db.String(255), nullable=True)  # For group chats
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # Relationships
    participants = db.relationship('Profile', secondary=conversation_participants, lazy='subquery',
                                   backref=db.backref('conversations', lazy=True))
    
    def __repr__(self):
        return f'<Conversation {self.id} ({self.type})>'
