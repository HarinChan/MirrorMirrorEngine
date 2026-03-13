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
    try:
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
        
        target_profile_id = data.get('profileId') or data.get('classroomId')
        
        if not target_profile_id:
            return jsonify({"msg": "Target profile ID is required"}), 400
        
        # Validate ID is positive integer
        try:
            target_profile_id = int(target_profile_id)
            if target_profile_id <= 0:
                return jsonify({"msg": "Invalid profile ID"}), 400
        except (ValueError, TypeError):
            return jsonify({"msg": "Invalid profile ID format"}), 400

        target_profile = Profile.query.get(target_profile_id)
        if not target_profile:
            return jsonify({"msg": "Target profile not found"}), 404
            
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
            
            # Check if relations already exist (update status if they do)
            rel1 = Relation.query.filter_by(
                from_profile_id=target_profile.id,
                to_profile_id=sender_profile.id
            ).first()
            rel2 = Relation.query.filter_by(
                from_profile_id=sender_profile.id,
                to_profile_id=target_profile.id
            ).first()
            
            if rel1:
                rel1.status = 'accepted'
            else:
                rel1 = Relation(
                    from_profile_id=target_profile.id,
                    to_profile_id=sender_profile.id,
                    status='accepted'
                )
                db.session.add(rel1)
            
            if rel2:
                rel2.status = 'accepted'
            else:
                rel2 = Relation(
                    from_profile_id=sender_profile.id,
                    to_profile_id=target_profile.id,
                    status='accepted'
                )
                db.session.add(rel2)
            
            # Notify original sender (who is now becoming a friend)
            notif = Notification(
                account_id=target_profile.account_id,
                title="Friend Request Accepted",
                message=f"{sender_profile.name} accepted your friend request!",
                type="success",
                related_id=str(sender_profile.id)
            )
            
            db.session.add(notif)
            db.session.commit()
            
            return jsonify({"msg": "Friend request accepted (mutual)", "status": "accepted"}), 200

        # Create new request
        new_request = FriendRequest(
            sender_profile_id=sender_profile.id,
            receiver_profile_id=target_profile.id,
            status='pending'
        )
        
        # Notify receiver
        notif = Notification(
            account_id=target_profile.account_id,
            title="New Friend Request",
            message=f"{sender_profile.name} sent you a friend request!",
            type="friend_request_received",
            related_id=str(sender_profile.id)
        )
        
        db.session.add_all([new_request, notif])
        db.session.commit()
        
        return jsonify({"msg": "Friend request sent", "status": "pending"}), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Internal server error", "error": str(e)}), 500


@friends_bp.route('/api/friends/accept', methods=['POST'])
@jwt_required()
def accept_friend_request():
    """Accept a pending friend request"""
    try:
        current_user_id = get_jwt_identity()
        account = Account.query.get(current_user_id)
        if not account:
            return jsonify({"msg": "User not found"}), 404

        receiver_profile = account.profiles.first()
        if not receiver_profile:
            return jsonify({"msg": "Profile not found"}), 404

        data = request.json
        if not data:
            return jsonify({"msg": "Request body is required"}), 400
            
        request_id = data.get('requestId')
        sender_profile_id = data.get('senderId')  # Optional, if request_id not provided
        
        # Validate IDs if provided
        if request_id is not None:
            try:
                request_id = int(request_id)
                if request_id <= 0:
                    return jsonify({"msg": "Invalid request ID"}), 400
            except (ValueError, TypeError):
                return jsonify({"msg": "Invalid request ID format"}), 400
        
        if sender_profile_id is not None:
            try:
                sender_profile_id = int(sender_profile_id)
                if sender_profile_id <= 0:
                    return jsonify({"msg": "Invalid sender ID"}), 400
            except (ValueError, TypeError):
                return jsonify({"msg": "Invalid sender ID format"}), 400

        friend_request = None
        if request_id:
            friend_request = FriendRequest.query.get(request_id)
        elif sender_profile_id:
            friend_request = FriendRequest.query.filter_by(
                sender_profile_id=sender_profile_id,
                receiver_profile_id=receiver_profile.id,
                status='pending'
            ).first()

        if not friend_request:
            return jsonify({"msg": "Friend request not found"}), 404

        if friend_request.receiver_profile_id != receiver_profile.id:
            return jsonify({"msg": "Unauthorized"}), 403

        friend_request.status = 'accepted'

        # Check if relations already exist (update status if they do)
        rel1 = Relation.query.filter_by(
            from_profile_id=friend_request.sender_profile_id,
            to_profile_id=friend_request.receiver_profile_id
        ).first()
        rel2 = Relation.query.filter_by(
            from_profile_id=friend_request.receiver_profile_id,
            to_profile_id=friend_request.sender_profile_id
        ).first()

        if rel1:
            rel1.status = 'accepted'
        else:
            rel1 = Relation(
                from_profile_id=friend_request.sender_profile_id,
                to_profile_id=friend_request.receiver_profile_id,
                status='accepted'
            )
            db.session.add(rel1)

        if rel2:
            rel2.status = 'accepted'
        else:
            rel2 = Relation(
                from_profile_id=friend_request.receiver_profile_id,
                to_profile_id=friend_request.sender_profile_id,
                status='accepted'
            )
            db.session.add(rel2)

        # Notify sender
        notif = Notification(
            account_id=friend_request.sender.account_id,
            title="Friend Request Accepted",
            message=f"{receiver_profile.name} accepted your friend request!",
            type="friend_request_accepted",
            related_id=str(receiver_profile.id)
        )

        db.session.add(notif)
        db.session.commit()

        return jsonify({"msg": "Friend request accepted"}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Internal server error", "error": str(e)}), 500


@friends_bp.route('/api/friends/reject', methods=['POST'])
@jwt_required()
def reject_friend_request():
    """Reject a pending friend request"""
    try:
        current_user_id = get_jwt_identity()
        account = Account.query.get(current_user_id)
        if not account:
            return jsonify({"msg": "User not found"}), 404

        receiver_profile = account.profiles.first()
        if not receiver_profile:
            return jsonify({"msg": "Profile not found"}), 404

        data = request.json
        if not data:
            return jsonify({"msg": "Request body is required"}), 400
            
        request_id = data.get('requestId')
        sender_profile_id = data.get('senderId')
        
        # Validate IDs if provided
        if request_id is not None:
            try:
                request_id = int(request_id)
                if request_id <= 0:
                    return jsonify({"msg": "Invalid request ID"}), 400
            except (ValueError, TypeError):
                return jsonify({"msg": "Invalid request ID format"}), 400
        
        if sender_profile_id is not None:
            try:
                sender_profile_id = int(sender_profile_id)
                if sender_profile_id <= 0:
                    return jsonify({"msg": "Invalid sender ID"}), 400
            except (ValueError, TypeError):
                return jsonify({"msg": "Invalid sender ID format"}), 400

        friend_request = None
        if request_id:
            friend_request = FriendRequest.query.get(request_id)
        elif sender_profile_id:
            friend_request = FriendRequest.query.filter_by(
                sender_profile_id=sender_profile_id,
                receiver_profile_id=receiver_profile.id,
                status='pending'
            ).first()

        if not friend_request:
            return jsonify({"msg": "Friend request not found"}), 404

        if friend_request.receiver_profile_id != receiver_profile.id:
            return jsonify({"msg": "Unauthorized"}), 403

        friend_request.status = 'rejected'
        db.session.commit()

        return jsonify({"msg": "Friend request rejected"}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Internal server error", "error": str(e)}), 500


@friends_bp.route('/api/friends/<int:friend_id>', methods=['DELETE'])
@jwt_required()
def remove_friend(friend_id):
    """Remove a friend connection"""
    try:
        current_user_id = get_jwt_identity()
        account = Account.query.get(current_user_id)
        if not account:
            return jsonify({"msg": "User not found"}), 404

        my_profile = account.profiles.first()
        if not my_profile:
            return jsonify({"msg": "Profile not found"}), 404

        # Validate friend_id
        if friend_id <= 0:
            return jsonify({"msg": "Invalid friend ID"}), 400

        # Check both directions
        relations_to_delete = Relation.query.filter(
            ((Relation.from_profile_id == my_profile.id) & (Relation.to_profile_id == friend_id)) |
            ((Relation.from_profile_id == friend_id) & (Relation.to_profile_id == my_profile.id))
        ).all()

        if not relations_to_delete:
            return jsonify({"msg": "Friendship not found"}), 404

        for rel in relations_to_delete:
            db.session.delete(rel)

        db.session.commit()

        return jsonify({"msg": "Friend removed"}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Internal server error", "error": str(e)}), 500
