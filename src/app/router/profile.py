from flask import request, jsonify
from src.app.__init__ import db
from src.app.model.profile import Profile
from src.app.model.account import Account
from src.app.model.post import Post
from src.app.model.relation import Relation


# Create a profile
@app.route('/profiles', methods=['POST'])
def add_profile():
    data = request.get_json()
    new_profile = Profile(name=data['name'])
    db.session.add(new_profile)
    db.session.commit()
    return jsonify({"message": "Profile created", "id": new_profile.id}), 201

# Edit a profile
@app.route('/profiles/<int:id>', methods=['PUT'])
def edit_profile(id):
    data = request.get_json()
    profile = Profile.query.get_or_404(id)
    profile.name = data['name']
    db.session.commit()
    return jsonify({"message": "Profile updated"}), 200

# Delete a profile
@app.route('/profiles/<int:id>', methods=['DELETE'])
def delete_profile(id):
    profile = Profile.query.get_or_404(id)
    db.session.delete(profile)
    db.session.commit()
    return jsonify({"message": "Profile deleted"}), 200