from . import db
from datetime import datetime, timezone

post_likes = db.Table('post_likes',
    db.Column('post_id', db.Integer, db.ForeignKey('posts.id'), primary_key=True),
    db.Column('account_id', db.Integer, db.ForeignKey('accounts.id'), primary_key=True),
    db.Column('timestamp', db.DateTime, default=datetime.now(timezone.utc))
)

class Post(db.Model):
    """Posts/messages between classrooms"""
    __tablename__ = 'posts'
    
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey('profiles.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    
    # Relationships
    profile = db.relationship('Profile', backref='posts')
    liked_by = db.relationship('Account', secondary=post_likes, lazy='subquery',
        backref=db.backref('liked_posts', lazy=True))
    
    # New fields for rich posts
    likes = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)
    image_url = db.Column(db.String(500), nullable=True)
    
    # Self-referential relationship for quoting posts
    quoted_post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=True)
    quoted_post = db.relationship('Post', remote_side=[id], backref='quoted_by')
    
    def __repr__(self):
        return f'<Post {self.id} by {self.profile_id}>'