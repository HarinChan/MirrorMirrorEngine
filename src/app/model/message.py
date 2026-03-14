from . import db
from datetime import datetime, timezone


class Message(db.Model):
    """Messages within conversations"""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False)
    sender_profile_id = db.Column(db.Integer, db.ForeignKey('profiles.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='text', nullable=False)  # text, image, file, system
    attachment_url = db.Column(db.String(500), nullable=True)  # For images/files
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    edited_at = db.Column(db.DateTime, nullable=True)
    deleted = db.Column(db.Boolean, default=False)
    
    # Relationships
    conversation = db.relationship('Conversation', backref=db.backref('messages', cascade='all, delete-orphan', order_by='Message.created_at'))
    sender = db.relationship('Profile', backref=db.backref('sent_messages', cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f'<Message {self.id} in Conversation {self.conversation_id}>'


class MessageRead(db.Model):
    """Track which messages have been read by which profiles"""
    __tablename__ = 'message_reads'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=False)
    profile_id = db.Column(db.Integer, db.ForeignKey('profiles.id'), nullable=False)
    read_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    
    __table_args__ = (
        db.UniqueConstraint('message_id', 'profile_id', name='unique_message_read'),
    )
    
    # Relationships
    message = db.relationship('Message', backref=db.backref('read_by', cascade='all, delete-orphan'))
    profile = db.relationship('Profile', backref=db.backref('read_messages', cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f'<MessageRead message={self.message_id} profile={self.profile_id}>'


class MessageReaction(db.Model):
    """Reactions to messages (emoji reactions)"""
    __tablename__ = 'message_reactions'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=False)
    profile_id = db.Column(db.Integer, db.ForeignKey('profiles.id'), nullable=False)
    emoji = db.Column(db.String(10), nullable=False)  # Store emoji character
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    
    __table_args__ = (
        db.UniqueConstraint('message_id', 'profile_id', 'emoji', name='unique_message_reaction'),
    )
    
    # Relationships
    message = db.relationship('Message', backref=db.backref('reactions', cascade='all, delete-orphan'))
    profile = db.relationship('Profile', backref=db.backref('message_reactions', cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f'<MessageReaction message={self.message_id} profile={self.profile_id} emoji={self.emoji}>'
