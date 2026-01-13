from flask import request, jsonify
from src.app.main import db, app
from src.app.model.profile import Profile
from src.app.model.account import Account
from src.app.model.post import Post
from src.app.model.relation import Relation


# Create a post
@app.route('/posts', methods=['POST'])
def add_post():
    data = request.get_json()
    
    new_post = Post(
        profile_id=data['profile_id'],
        content=data['content']
    )
    db.session.add(new_post)
    db.session.commit()
    return jsonify({"message": "Post created", "id": new_post.id}), 201

# Read a post by ID
@app.route('/posts/<int:id>', methods=['GET'])
def get_post(id):
    post = Post.query.get_or_404(id)
    return jsonify({
        "id": post.id,
        "profile_id": post.profile_id,
        "content": post.content,
        "created_at": post.created_at.isoformat()
    }), 200

# Edit a post
@app.route('/posts/<int:id>', methods=['PUT'])
def edit_post(id):
    post = Post.query.get_or_404(id)
    data = request.get_json()

    post.content = data.get('content', post.content)
    db.session.commit()
    return jsonify({"message": "Post updated"}), 200

# Delete a post
@app.route('/posts/<int:id>', methods=['DELETE'])
def delete_post(id):
    post = Post.query.get_or_404(id)
    db.session.delete(post)
    db.session.commit()
    return jsonify({"message": "Post deleted"}), 200
