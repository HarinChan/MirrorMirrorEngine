from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..model import db
from ..model.account import Account
from ..model.friendrequest import FriendRequest
from ..model.notification import Notification
from ..model.profile import Profile
from ..model.relation import Relation

friends_bp = Blueprint('friends', __name__)

@friends_bp.route('/api/friends/request', methods=['POST'])
@jwt_required()
def send_friend_request():
    """Send a friend request to another classroom"""
    current_user_id = get_jwt_identity()
    account = Account.query.get(current_user_id)
    if not account:
        return jsonify({"msg": "User not found"}), 404

    sender_profile = account.profiles.first()
    if not sender_profile:
        return jsonify({"msg": "Profile not found"}), 404

    data = request.json
    if not data:
        return jsonify({"msg": "Request body is required"}), 400
    
    target_classroom_id = data.get('classroomId')
    
    if not target_classroom_id:
        return jsonify({"msg": "Target classroom ID is required"}), 400

    target_profile = Profile.query.get(target_classroom_id)
    if not target_profile:
        return jsonify({"msg": "Target classroom not found"}), 404
        
    if sender_profile.id == target_profile.id:
        return jsonify({"msg": "Cannot add yourself as a friend"}), 400

    # Check if already friends
    existing_relation = Relation.query.filter(
        ((Relation.from_profile_id == sender_profile.id) & (Relation.to_profile_id == target_profile.id)) |
        ((Relation.from_profile_id == target_profile.id) & (Relation.to_profile_id == sender_profile.id))
    ).first()
    
    if existing_relation:
        return jsonify({"msg": "Already friends"}), 400

    # Check if request already exists
    existing_request = FriendRequest.query.filter_by(
        sender_profile_id=sender_profile.id,
        receiver_profile_id=target_profile.id,
        status='pending'
    ).first()
    
    if existing_request:
        return jsonify({"msg": "Friend request already sent"}), 400
        
    # Check if they sent us a request (if so, auto-accept?)
    reverse_request = FriendRequest.query.filter_by(
        sender_profile_id=target_profile.id,
        receiver_profile_id=sender_profile.id,
        status='pending'
    ).first()
    
    if reverse_request:
        # Auto-accept since both want to be friends
        reverse_request.status = 'accepted'
        
        # Create relations (two-way)
        rel1 = Relation()
        rel1.from_profile_id = target_profile.id
        rel1.to_profile_id = sender_profile.id

        rel2 = Relation()
        rel2.from_profile_id = sender_profile.id
        rel2.to_profile_id = target_profile.id
        
        # Notify original sender (who is now becoming a friend)
        notif = Notification()
        notif.account_id = target_profile.account_id
        notif.title = "Friend Request Accepted"
        notif.message = f"{sender_profile.name} accepted your friend request!"
        notif.type = "success"
        notif.related_id = str(sender_profile.id)
        
        db.session.add_all([rel1, rel2, notif])
        db.session.commit()
        
        return jsonify({"msg": "Friend request accepted (mutual)", "status": "accepted"}), 200

    # Create new request
    new_request = FriendRequest()
    new_request.sender_profile_id = sender_profile.id
    new_request.receiver_profile_id = target_profile.id
    new_request.status = 'pending'
    
    # Notify receiver
    notif = Notification()
    notif.account_id = target_profile.account_id
    notif.title = "New Friend Request"
    notif.type = "friend_request_received"
    notif.related_id = str(sender_profile.id)
    
    db.session.add_all([new_request, notif])
    db.session.commit()
    
    return jsonify({"msg": "Friend request sent", "status": "pending"}), 201
