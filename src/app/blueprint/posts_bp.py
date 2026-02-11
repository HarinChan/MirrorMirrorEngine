"""
Posts API endpoints.
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import desc

from ..model import db
from ..model.account import Account
from ..model.post import Post

post_bp = Blueprint('post', __name__)

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
            "content": post.content,
            "imageUrl": post.image_url,
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
                "imageUrl": post.quoted_post.image_url
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
        
    # Use the first profile for posting (simplification)
    profile = account.profiles.first()
    if not profile:
        return jsonify({"msg": "Profile not found. Create a profile first."}), 400
        
    data = request.json
    if not data:
        return jsonify({"msg": "Request body is required"}), 400
    
    content = data.get('content')
    image_url = data.get('imageUrl')
    quoted_post_id = data.get('quotedPostId')
    
    if not content:
        return jsonify({"msg": "Content is required"}), 400
        
    post = Post()
    post.profile_id = profile.id
    post.content = content
    post.image_url = image_url
    post.quoted_post_id = quoted_post_id
    
    db.session.add(post)
    db.session.commit()
    
    # Return the created post in the format frontend expects
    response_data = {
        "id": str(post.id),
        "authorId": str(profile.id),
        "authorName": profile.name,
        "content": post.content,
        "imageUrl": post.image_url,
        "timestamp": post.created_at.isoformat(),
        "likes": post.likes,
        "comments": post.comments_count
    }
    
    if post.quoted_post:
        response_data["quotedPost"] = {
            "id": str(post.quoted_post.id),
            "authorName": post.quoted_post.profile.name,
            "content": post.quoted_post.content,
            "imageUrl": post.quoted_post.image_url
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