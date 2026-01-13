from . import db
from datetime import datetime, timezone

class Post(db.Model):
    """Posts/messages between classrooms"""
    __tablename__ = 'posts'
    
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey('profiles.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    
    # Relationships
    profile = db.relationship('Profile', backref='posts')
    
    def __repr__(self):
        return f'<Post {self.id} by {self.profile_id}>'