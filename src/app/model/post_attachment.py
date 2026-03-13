from datetime import datetime, timezone

from . import db


class PostAttachment(db.Model):
    """File attachment metadata linked to a post."""
    __tablename__ = 'post_attachments'

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(120), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False)
    storage_key = db.Column(db.String(512), nullable=False, unique=True)
    file_url = db.Column(db.String(1024), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    post = db.relationship('Post', back_populates='attachments')

    def to_dict(self):
        return {
            "id": str(self.id),
            "filename": self.original_filename,
            "mimeType": self.mime_type,
            "sizeBytes": self.size_bytes,
            "storageKey": self.storage_key,
            "url": self.file_url
        }
