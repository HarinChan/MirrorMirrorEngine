"""
Posts API endpoints.
"""
import os
import uuid

from flask import Blueprint, jsonify, request, current_app, send_from_directory, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import desc
from werkzeug.utils import secure_filename

from ..model import db
from ..model.account import Account
from ..model.post import Post
from ..model.post_attachment import PostAttachment

from ..service.chromadb_service import ChromaDBService

from ..config import Config

post_bp = Blueprint('post', __name__)

chroma_service = ChromaDBService(persist_directory="./chroma_db", collection_name="penpals_documents")

ALLOWED_ATTACHMENT_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}
MAX_ATTACHMENT_SIZE_BYTES = 20 * 1024 * 1024


def _attachments_root_dir():
    root = os.path.join(current_app.root_path, 'uploads', 'post_attachments')
    os.makedirs(root, exist_ok=True)
    return root


def _safe_storage_path(storage_key):
    if not storage_key or '..' in storage_key or storage_key.startswith('/'):
        return None

    root = os.path.abspath(_attachments_root_dir())
    abs_path = os.path.abspath(os.path.join(root, storage_key))
    if not abs_path.startswith(root + os.sep):
        return None
    return abs_path


def _uploaded_file_size(file_storage):
    stream = file_storage.stream
    current_pos = stream.tell()
    stream.seek(0, os.SEEK_END)
    size_bytes = stream.tell()
    stream.seek(current_pos, os.SEEK_SET)
    return size_bytes


def _build_attachment_file_url(storage_key):
    relative_url = url_for('post.get_post_attachment_file', storage_key=storage_key, _external=False)

    public_api_base_url = (Config.get_variable('PUBLIC_API_BASE_URL','')).strip().rstrip('/')
    if public_api_base_url:
        return f"{public_api_base_url}{relative_url}"

    # Respect explicit env override; otherwise infer from the current request.
    force_https_env = Config.get_variable('FORCE_HTTPS_ATTACHMENT_URLS','') # will not throw if missing
    if force_https_env == '':
        force_https = bool(request.is_secure)
    else:
        force_https = (force_https_env or '').strip().lower() in {'1', 'true', 'yes', 'on'}

    if force_https:
        return url_for('post.get_post_attachment_file', storage_key=storage_key, _external=True, _scheme='https')

    return url_for('post.get_post_attachment_file', storage_key=storage_key, _external=True)


def _build_attachment_response(attachment):
    return {
        "id": str(attachment.id),
        "filename": attachment.original_filename,
        "mimeType": attachment.mime_type,
        "sizeBytes": attachment.size_bytes,
        "storageKey": attachment.storage_key,
        # Rebuild URL at read time so scheme/base changes apply to old records too.
        "url": _build_attachment_file_url(attachment.storage_key)
    }


def _validate_attachments_payload(attachments):
    if attachments is None:
        return []
    if not isinstance(attachments, list):
        return None

    validated = []
    for attachment in attachments:
        if not isinstance(attachment, dict):
            return None

        filename = str(attachment.get('filename', '')).strip()
        mime_type = str(attachment.get('mimeType', '')).strip()
        storage_key = str(attachment.get('storageKey', '')).strip()
        file_url = attachment.get('url')
        size_bytes = attachment.get('sizeBytes')

        if not filename or not mime_type or not storage_key:
            return None
        if mime_type not in ALLOWED_ATTACHMENT_MIME_TYPES:
            return None

        normalized_url = str(file_url).strip() if file_url else None
        if normalized_url and normalized_url.startswith('blob:'):
            return None

        try:
            size_bytes = int(size_bytes)
        except (TypeError, ValueError):
            return None

        if size_bytes < 0:
            return None

        validated.append({
            'filename': filename,
            'mime_type': mime_type,
            'size_bytes': size_bytes,
            'storage_key': storage_key,
            'file_url': normalized_url
        })

    return validated


@post_bp.route('/api/posts/attachments/upload', methods=['POST'])
@jwt_required()
def upload_post_attachment():
    """Upload a post attachment and return metadata for post creation."""
    account_id = get_jwt_identity()
    account = Account.query.get(account_id)
    if not account:
        return jsonify({"msg": "User not found"}), 404

    file_storage = request.files.get('file') or request.files.get('attachment')
    if file_storage is None:
        return jsonify({"msg": "Missing file in form data"}), 400

    original_filename = (file_storage.filename or '').strip()
    if not original_filename:
        return jsonify({"msg": "Filename is required"}), 400

    mime_type = (file_storage.mimetype or '').strip().lower()
    if mime_type not in ALLOWED_ATTACHMENT_MIME_TYPES:
        return jsonify({"msg": f"Unsupported file type: {mime_type}"}), 400

    size_bytes = _uploaded_file_size(file_storage)
    if size_bytes <= 0:
        return jsonify({"msg": "Uploaded file is empty"}), 400
    if size_bytes > MAX_ATTACHMENT_SIZE_BYTES:
        return jsonify({"msg": f"File too large. Max {MAX_ATTACHMENT_SIZE_BYTES} bytes"}), 413

    safe_name = secure_filename(original_filename)
    _, ext = os.path.splitext(safe_name)
    storage_key = f"{account.id}/{uuid.uuid4().hex}{ext.lower()}"

    abs_path = _safe_storage_path(storage_key)
    if abs_path is None:
        return jsonify({"msg": "Invalid storage key"}), 400

    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    file_storage.save(abs_path)

    file_url = _build_attachment_file_url(storage_key)

    return jsonify({
        "msg": "Attachment uploaded",
        "attachment": {
            "filename": original_filename,
            "mimeType": mime_type,
            "sizeBytes": size_bytes,
            "storageKey": storage_key,
            "url": file_url
        }
    }), 201


@post_bp.route('/api/posts/attachments/<path:storage_key>', methods=['GET'])
def get_post_attachment_file(storage_key):
    """Serve uploaded post attachment by storage key."""
    abs_path = _safe_storage_path(storage_key)
    if abs_path is None or not os.path.exists(abs_path):
        return jsonify({"msg": "Attachment not found"}), 404

    return send_from_directory(_attachments_root_dir(), storage_key, as_attachment=False)


@post_bp.route('/api/posts', methods=['GET'])
@jwt_required(optional=True)
def get_posts():
    """Get all posts, ordered by newest"""
    current_user_id = get_jwt_identity()
    current_account = None
    if current_user_id:
        current_account = Account.query.get(current_user_id)
        
    posts = Post.query.order_by(desc(Post.created_at)).all()
    
    result = []
    for post in posts:
        is_liked = False
        if current_account and current_account in post.liked_by:
            is_liked = True
            
        post_data = {
            "id": str(post.id),
            "authorId": str(post.profile_id),
            "authorName": post.profile.name,
            "authorAvatar": post.profile.avatar or "",
            "content": post.content,
            "attachments": [_build_attachment_response(attachment) for attachment in post.attachments],
            "timestamp": post.created_at.isoformat(),
            "likes": post.likes,
            "comments": post.comments_count,
            "isLiked": is_liked
        }
        
        # Include quoted post if it exists
        if post.quoted_post:
            post_data["quotedPost"] = {
                "id": str(post.quoted_post.id),
                "authorName": post.quoted_post.profile.name,
                "content": post.quoted_post.content,
                "attachments": [_build_attachment_response(attachment) for attachment in post.quoted_post.attachments]
            }
            
        result.append(post_data)
        
    return jsonify({"posts": result}), 200

@post_bp.route('/api/posts', methods=['POST'])
@jwt_required()
def create_post():
    """Create a new post"""
    current_user_id = get_jwt_identity()
    account = Account.query.get(current_user_id)
    
    if not account:
        return jsonify({"msg": "User not found"}), 404
        
    # Use the classroom specified by the frontend, fall back to first if not provided
    data = request.json
    classroom_id = data.get('classroomId')
    
    if classroom_id:
        profile = account.profiles.filter_by(id=classroom_id).first()
        if not profile:
            # classroomId provided but doesn't belong to this account — reject
            return jsonify({"msg": "Classroom not found for this account"}), 404
    else:
        profile = account.profiles.first()
    if not profile:
        return jsonify({"msg": "Profile not found. Create a profile first."}), 400
        
    data = request.json
    if not data:
        return jsonify({"msg": "Request body is required"}), 400
    
    content = data.get('content')
    quoted_post_id = data.get('quotedPostId')
    attachments_payload = _validate_attachments_payload(data.get('attachments'))
    
    if not content:
        return jsonify({"msg": "Content is required"}), 400
    if attachments_payload is None:
        return jsonify({"msg": "attachments must be an array of valid attachment objects"}), 400
        
    post = Post()
    post.profile_id = profile.id
    post.content = content
    post.quoted_post_id = quoted_post_id

    for attachment_data in attachments_payload:
        attachment = PostAttachment(
            original_filename=attachment_data['filename'],
            mime_type=attachment_data['mime_type'],
            size_bytes=attachment_data['size_bytes'],
            storage_key=attachment_data['storage_key'],
            file_url=attachment_data['file_url']
        )
        post.attachments.append(attachment)
    
    db.session.add(post)
    db.session.commit()

    # Index post content in ChromaDB for RAG retrieval
    try:
        chroma_service.add_documents(
            [post.content],
            metadatas=[{
                "source": "post",
                "post_id": str(post.id),
                "author": profile.name,
                "profile_id": str(profile.id),
                "timestamp": post.created_at.isoformat()
            }],
            ids=[f"post-{post.id}"]
        )
    except Exception as e:
        # Don't fail post creation if indexing fails
        current_app.logger.warning("Failed to index post in ChromaDB: %s", e)
    
    # Return the created post in the format frontend expects
    response_data = {
        "id": str(post.id),
        "authorId": str(profile.id),
        "authorName": profile.name,
        "authorAvatar": profile.avatar or "",
        "content": post.content,
        "attachments": [_build_attachment_response(attachment) for attachment in post.attachments],
        "timestamp": post.created_at.isoformat(),
        "likes": post.likes,
        "comments": post.comments_count
    }
    
    if post.quoted_post:
        response_data["quotedPost"] = {
            "id": str(post.quoted_post.id),
            "authorName": post.quoted_post.profile.name,
            "content": post.quoted_post.content,
            "attachments": [_build_attachment_response(attachment) for attachment in post.quoted_post.attachments]
        }
    
    return jsonify({
        "msg": "Post created successfully",
        "post": response_data
    }), 201

@post_bp.route('/api/posts/<int:post_id>/like', methods=['POST'])
@jwt_required()
def like_post(post_id):
    """Like a post"""
    current_user_id = get_jwt_identity()
    account = Account.query.get(current_user_id)
    if not account:
        return jsonify({"msg": "User not found"}), 404

    post = Post.query.get(post_id)
    if not post:
        return jsonify({"msg": "Post not found"}), 404
        
    # Check if already liked
    if account in post.liked_by:
        return jsonify({"msg": "Already liked", "likes": post.likes}), 200
        
    post.liked_by.append(account)
    post.likes += 1
    db.session.commit()
    
    return jsonify({"msg": "Post liked", "likes": post.likes}), 200

@post_bp.route('/api/posts/<int:post_id>/unlike', methods=['POST'])
@jwt_required()
def unlike_post(post_id):
    """Unlike a post"""
    current_user_id = get_jwt_identity()
    account = Account.query.get(current_user_id)
    if not account:
        return jsonify({"msg": "User not found"}), 404

    post = Post.query.get(post_id)
    if not post:
        return jsonify({"msg": "Post not found"}), 404
        
    # Check if liked
    if account not in post.liked_by:
        return jsonify({"msg": "Not liked yet", "likes": post.likes}), 200
        
    post.liked_by.remove(account)
    if post.likes > 0:
        post.likes -= 1
    db.session.commit()
    
    return jsonify({"msg": "Post unliked", "likes": post.likes}), 200

@post_bp.route('/api/posts/<int:post_id>', methods=['DELETE'])
@jwt_required()
def delete_post(post_id):
    """Delete a post — only the author's classroom can delete it"""
    current_user_id = get_jwt_identity()
    account = Account.query.get(current_user_id)
    if not account:
        return jsonify({"msg": "User not found"}), 404

    post = Post.query.get(post_id)
    if not post:
        return jsonify({"msg": "Post not found"}), 404

    # Verify the post belongs to a classroom owned by this account
    if post.profile.account_id != account.id:
        return jsonify({"msg": "You can only delete your own posts"}), 403

    # Remove from ChromaDB index (best-effort)
    try:
        chroma_service.delete_documents([f"post-{post.id}"])
    except Exception as e:
        current_app.logger.warning("Failed to remove post from ChromaDB: %s", e)

    # Collect attachment file paths before deleting DB rows.
    attachment_file_paths = []
    for attachment in post.attachments:
        abs_path = _safe_storage_path(attachment.storage_key)
        if abs_path:
            attachment_file_paths.append(abs_path)

    db.session.delete(post)
    db.session.commit()

    for abs_path in attachment_file_paths:
        try:
            if os.path.exists(abs_path):
                os.remove(abs_path)
        except OSError as e:
            current_app.logger.warning("Failed to delete attachment file %s: %s", abs_path, e)

    return jsonify({"msg": "Post deleted"}), 200