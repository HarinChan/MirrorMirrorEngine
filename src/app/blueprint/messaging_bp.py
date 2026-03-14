"""
Messaging API endpoints for MirrorMirror.
Handles conversations and direct messages between classrooms.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_, and_, desc
from datetime import datetime, timezone

from ..model import db
from ..model.account import Account
from ..model.profile import Profile
from ..model.conversation import Conversation
from ..model.message import Message, MessageRead, MessageReaction
from ..model.relation import Relation

messaging_bp = Blueprint('messaging', __name__)


@messaging_bp.route('/api/conversations', methods=['GET'])
@jwt_required()
def get_conversations():
    """Get all conversations for the current user's classroom"""
    try:
        current_user_id = get_jwt_identity()
        account = Account.query.get(current_user_id)
        if not account:
            return jsonify({"msg": "User not found"}), 404

        profile = account.profiles.first()
        if not profile:
            return jsonify({"msg": "Profile not found"}), 404

        # Get all conversations where this profile is a participant
        conversations = profile.conversations
        
        result = []
        for conv in conversations:
            # Get the other participant(s)
            other_participants = [p for p in conv.participants if p.id != profile.id]
            
            # Get last message
            last_message = Message.query.filter_by(
                conversation_id=conv.id,
                deleted=False
            ).order_by(desc(Message.created_at)).first()
            
            # Count unread messages
            unread_count = 0
            if last_message:
                unread_messages = Message.query.filter(
                    Message.conversation_id == conv.id,
                    Message.sender_profile_id != profile.id,
                    Message.deleted == False,
                    ~Message.read_by.any(MessageRead.profile_id == profile.id)
                ).count()
                unread_count = unread_messages
            
            conv_data = {
                "id": conv.id,
                "type": conv.type,
                "title": conv.title,
                "participants": [{
                    "id": p.id,
                    "name": p.name,
                    "avatar": p.avatar,
                    "location": p.location
                } for p in other_participants],
                "lastMessage": {
                    "id": last_message.id,
                    "content": last_message.content,
                    "senderId": last_message.sender_profile_id,
                    "createdAt": last_message.created_at.isoformat(),
                    "messageType": last_message.message_type
                } if last_message else None,
                "unreadCount": unread_count,
                "updatedAt": conv.updated_at.isoformat()
            }
            result.append(conv_data)
        
        # Sort by most recent activity
        result.sort(key=lambda x: x['updatedAt'], reverse=True)
        
        return jsonify({"conversations": result}), 200
    
    except Exception as e:
        return jsonify({"msg": "Internal server error", "error": str(e)}), 500


@messaging_bp.route('/api/conversations/<int:conversation_id>/messages', methods=['GET'])
@jwt_required()
def get_messages(conversation_id):
    """Get messages in a conversation with pagination"""
    try:
        # Validate conversation_id
        if conversation_id <= 0:
            return jsonify({"msg": "Invalid conversation ID"}), 400
            
        current_user_id = get_jwt_identity()
        account = Account.query.get(current_user_id)
        if not account:
            return jsonify({"msg": "User not found"}), 404

        profile = account.profiles.first()
        if not profile:
            return jsonify({"msg": "Profile not found"}), 404

        # Verify user is participant in this conversation
        conversation = Conversation.query.get(conversation_id)
        if not conversation:
            return jsonify({"msg": "Conversation not found"}), 404
        
        if profile not in conversation.participants:
            return jsonify({"msg": "Unauthorized"}), 403

        # Pagination - get latest messages (newest first for pagination)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 30, type=int)
        
        # Validate pagination parameters
        if page < 1:
            page = 1
        if per_page < 1:
            per_page = 30
        if per_page > 100:  # Cap at 100 to prevent DoS
            per_page = 100
        
        # Get messages ordered newest first for proper pagination
        messages_query = Message.query.filter_by(
            conversation_id=conversation_id,
            deleted=False
        ).order_by(desc(Message.created_at))
        
        paginated = messages_query.paginate(page=page, per_page=per_page, error_out=False)
        
        messages = []
        for msg in paginated.items:
            # Check if current user has read this message
            is_read = MessageRead.query.filter_by(
                message_id=msg.id,
                profile_id=profile.id
            ).first() is not None
            
            # Get reactions grouped by emoji
            reactions_data = {}
            for reaction in msg.reactions:
                if reaction.emoji not in reactions_data:
                    reactions_data[reaction.emoji] = {
                        "emoji": reaction.emoji,
                        "count": 0,
                        "profiles": [],
                        "hasReacted": False
                    }
                reactions_data[reaction.emoji]["count"] += 1
                reactions_data[reaction.emoji]["profiles"].append({
                    "id": reaction.profile_id,
                    "name": reaction.profile.name
                })
                if reaction.profile_id == profile.id:
                    reactions_data[reaction.emoji]["hasReacted"] = True
            
            messages.append({
                "id": msg.id,
                "conversationId": msg.conversation_id,
                "senderId": msg.sender_profile_id,
                "senderName": msg.sender.name,
                "senderAvatar": msg.sender.avatar,
                "content": msg.content,
                "messageType": msg.message_type,
                "attachmentUrl": msg.attachment_url,
                "createdAt": msg.created_at.isoformat(),
                "editedAt": msg.edited_at.isoformat() if msg.edited_at else None,
                "isRead": is_read,
                "deleted": msg.deleted,
                "reactions": list(reactions_data.values())
            })
        
        # Reverse to show oldest first in UI
        messages.reverse()
        
        return jsonify({
            "messages": messages,
            "pagination": {
                "page": page,
                "perPage": per_page,
                "total": paginated.total,
                "pages": paginated.pages,
                "hasNext": paginated.has_next,
                "hasPrev": paginated.has_prev
            }
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Internal server error", "error": str(e)}), 500


@messaging_bp.route('/api/conversations/<int:conversation_id>/messages', methods=['POST'])
@jwt_required()
def send_message(conversation_id):
    """Send a message in a conversation"""
    try:
        # Validate conversation_id
        if conversation_id <= 0:
            return jsonify({"msg": "Invalid conversation ID"}), 400
            
        current_user_id = get_jwt_identity()
        account = Account.query.get(current_user_id)
        if not account:
            return jsonify({"msg": "User not found"}), 404

        profile = account.profiles.first()
        if not profile:
            return jsonify({"msg": "Profile not found"}), 404

        # Verify user is participant
        conversation = Conversation.query.get(conversation_id)
        if not conversation:
            return jsonify({"msg": "Conversation not found"}), 404
        
        if profile not in conversation.participants:
            return jsonify({"msg": "Unauthorized"}), 403

        data = request.json
        if not data:
            return jsonify({"msg": "Request body is required"}), 400
            
        content = data.get('content', '').strip()
        message_type = data.get('messageType', 'text')
        attachment_url = data.get('attachmentUrl')
        
        if not content and not attachment_url:
            return jsonify({"msg": "Message content or attachment required"}), 400
        
        # Validate content length (max 10,000 characters)
        if content and len(content) > 10000:
            return jsonify({"msg": "Message content too long (max 10,000 characters)"}), 400
        
        # Validate message_type
        valid_types = ['text', 'image', 'file', 'system']
        if message_type not in valid_types:
            return jsonify({"msg": f"Invalid message type. Must be one of: {', '.join(valid_types)}"}), 400
        
        # Validate attachment_url length
        if attachment_url and len(attachment_url) > 500:
            return jsonify({"msg": "Attachment URL too long (max 500 characters)"}), 400

        # Create message
        message = Message(
            conversation_id=conversation_id,
            sender_profile_id=profile.id,
            content=content,
            message_type=message_type,
            attachment_url=attachment_url
        )
        
        # Update conversation timestamp
        conversation.updated_at = datetime.now(timezone.utc)
        
        db.session.add(message)
        db.session.commit()
        
        return jsonify({
            "msg": "Message sent",
            "message": {
                "id": message.id,
                "conversationId": message.conversation_id,
                "senderId": message.sender_profile_id,
                "senderName": profile.name,
                "senderAvatar": profile.avatar,
                "content": message.content,
                "messageType": message.message_type,
                "attachmentUrl": message.attachment_url,
                "createdAt": message.created_at.isoformat()
            }
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Internal server error", "error": str(e)}), 500


@messaging_bp.route('/api/messages/<int:message_id>/read', methods=['POST'])
@jwt_required()
def mark_message_read(message_id):
    """Mark a message as read"""
    try:
        # Validate message_id
        if message_id <= 0:
            return jsonify({"msg": "Invalid message ID"}), 400

        current_user_id = get_jwt_identity()
        account = Account.query.get(current_user_id)
        if not account:
            return jsonify({"msg": "User not found"}), 404

        profile = account.profiles.first()
        if not profile:
            return jsonify({"msg": "Profile not found"}), 404

        message = Message.query.get(message_id)
        if not message:
            return jsonify({"msg": "Message not found"}), 404

        # Verify user is in the conversation
        if profile not in message.conversation.participants:
            return jsonify({"msg": "Unauthorized"}), 403

        # Don't mark own messages as read
        if message.sender_profile_id == profile.id:
            return jsonify({"msg": "Cannot mark own message as read"}), 400

        # Check if already marked as read
        existing = MessageRead.query.filter_by(
            message_id=message_id,
            profile_id=profile.id
        ).first()

        if existing:
            return jsonify({"msg": "Already marked as read"}), 200

        # Create read receipt
        read_receipt = MessageRead(
            message_id=message_id,
            profile_id=profile.id
        )

        db.session.add(read_receipt)
        db.session.commit()

        return jsonify({"msg": "Message marked as read"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Internal server error", "error": str(e)}), 500


@messaging_bp.route('/api/conversations/<int:conversation_id>/mark-all-read', methods=['POST'])
@jwt_required()
def mark_all_read(conversation_id):
    """Mark all messages in a conversation as read"""
    try:
        # Validate conversation_id
        if conversation_id <= 0:
            return jsonify({"msg": "Invalid conversation ID"}), 400

        current_user_id = get_jwt_identity()
        account = Account.query.get(current_user_id)
        if not account:
            return jsonify({"msg": "User not found"}), 404

        profile = account.profiles.first()
        if not profile:
            return jsonify({"msg": "Profile not found"}), 404

        conversation = Conversation.query.get(conversation_id)
        if not conversation:
            return jsonify({"msg": "Conversation not found"}), 404

        if profile not in conversation.participants:
            return jsonify({"msg": "Unauthorized"}), 403

        # Get all unread messages from others
        unread_messages = Message.query.filter(
            Message.conversation_id == conversation_id,
            Message.sender_profile_id != profile.id,
            Message.deleted == False,
            ~Message.read_by.any(MessageRead.profile_id == profile.id)
        ).all()

        # Mark all as read
        for msg in unread_messages:
            read_receipt = MessageRead(
                message_id=msg.id,
                profile_id=profile.id
            )
            db.session.add(read_receipt)

        db.session.commit()

        return jsonify({"msg": f"Marked {len(unread_messages)} messages as read"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Internal server error", "error": str(e)}), 500


@messaging_bp.route('/api/conversations/start', methods=['POST'])
@jwt_required()
def start_conversation():
    """Start a new conversation with a friend"""
    try:
        current_user_id = get_jwt_identity()
        account = Account.query.get(current_user_id)
        if not account:
            return jsonify({"msg": "User not found"}), 404

        profile = account.profiles.first()
        if not profile:
            return jsonify({"msg": "Profile not found"}), 404

        data = request.json
        if not data:
            return jsonify({"msg": "Request body is required"}), 400

        friend_id = data.get('friendId')

        if not friend_id:
            return jsonify({"msg": "Friend ID required"}), 400

        # Validate friend_id
        if not isinstance(friend_id, int) or friend_id <= 0:
            return jsonify({"msg": "Invalid friend ID"}), 400

        friend = Profile.query.get(friend_id)
        if not friend:
            return jsonify({"msg": "Friend not found"}), 404

        # Verify they are friends
        friendship = Relation.query.filter(
            or_(
                and_(Relation.from_profile_id == profile.id, Relation.to_profile_id == friend_id),
                and_(Relation.from_profile_id == friend_id, Relation.to_profile_id == profile.id)
            ),
            Relation.status == 'accepted'
        ).first()

        if not friendship:
            return jsonify({"msg": "Can only message friends"}), 403

        # Check if conversation already exists
        existing_conv = None
        for conv in profile.conversations:
            if conv.type == 'direct' and friend in conv.participants and len(conv.participants) == 2:
                existing_conv = conv
                break

        if existing_conv:
            return jsonify({
                "msg": "Conversation already exists",
                "conversation": {
                    "id": existing_conv.id,
                    "type": existing_conv.type,
                    "participants": [{
                        "id": friend.id,
                        "name": friend.name,
                        "avatar": friend.avatar,
                        "location": friend.location
                    }]
                }
            }), 200

        # Create new conversation
        conversation = Conversation(type='direct')
        conversation.participants.append(profile)
        conversation.participants.append(friend)

        db.session.add(conversation)
        db.session.commit()

        return jsonify({
            "msg": "Conversation created",
            "conversation": {
                "id": conversation.id,
                "type": conversation.type,
                "participants": [{
                    "id": friend.id,
                    "name": friend.name,
                    "avatar": friend.avatar,
                    "location": friend.location
                }],
                "createdAt": conversation.created_at.isoformat()
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Internal server error", "error": str(e)}), 500


@messaging_bp.route('/api/messages/<int:message_id>', methods=['PUT'])
@jwt_required()
def edit_message(message_id):
    """Edit a message (only by sender)"""
    try:
        # Validate message_id
        if message_id <= 0:
            return jsonify({"msg": "Invalid message ID"}), 400

        current_user_id = get_jwt_identity()
        account = Account.query.get(current_user_id)
        if not account:
            return jsonify({"msg": "User not found"}), 404

        profile = account.profiles.first()
        if not profile:
            return jsonify({"msg": "Profile not found"}), 404

        message = Message.query.get(message_id)
        if not message:
            return jsonify({"msg": "Message not found"}), 404

        # Security: Only sender can edit their own message
        if message.sender_profile_id != profile.id:
            return jsonify({"msg": "Unauthorized - can only edit your own messages"}), 403

        # Can't edit deleted messages
        if message.deleted:
            return jsonify({"msg": "Cannot edit deleted message"}), 400

        data = request.json
        if not data:
            return jsonify({"msg": "Request body is required"}), 400

        new_content = data.get('content', '').strip()

        if not new_content:
            return jsonify({"msg": "Message content required"}), 400

        # Validate content length (max 10,000 characters)
        if len(new_content) > 10000:
            return jsonify({"msg": "Message content too long (max 10,000 characters)"}), 400

        # Update message
        message.content = new_content
        message.edited_at = datetime.now(timezone.utc)

        db.session.commit()

        return jsonify({
            "msg": "Message updated",
            "message": {
                "id": message.id,
                "content": message.content,
                "editedAt": message.edited_at.isoformat()
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Internal server error", "error": str(e)}), 500


@messaging_bp.route('/api/messages/<int:message_id>', methods=['DELETE'])
@jwt_required()
def delete_message(message_id):
    """Delete a message (only by sender)"""
    try:
        # Validate message_id
        if message_id <= 0:
            return jsonify({"msg": "Invalid message ID"}), 400

        current_user_id = get_jwt_identity()
        account = Account.query.get(current_user_id)
        if not account:
            return jsonify({"msg": "User not found"}), 404

        profile = account.profiles.first()
        if not profile:
            return jsonify({"msg": "Profile not found"}), 404

        message = Message.query.get(message_id)
        if not message:
            return jsonify({"msg": "Message not found"}), 404

        # Security: Only sender can delete their own message
        if message.sender_profile_id != profile.id:
            return jsonify({"msg": "Unauthorized - can only delete your own messages"}), 403

        # Soft delete
        message.deleted = True
        message.content = "[Message deleted]"

        db.session.commit()

        return jsonify({"msg": "Message deleted"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Internal server error", "error": str(e)}), 500


@messaging_bp.route('/api/messages/<int:message_id>/reactions', methods=['POST'])
@jwt_required()
def add_reaction(message_id):
    """Add a reaction to a message"""
    try:
        # Validate message_id
        if message_id <= 0:
            return jsonify({"msg": "Invalid message ID"}), 400

        current_user_id = get_jwt_identity()
        account = Account.query.get(current_user_id)
        if not account:
            return jsonify({"msg": "User not found"}), 404

        profile = account.profiles.first()
        if not profile:
            return jsonify({"msg": "Profile not found"}), 404

        message = Message.query.get(message_id)
        if not message:
            return jsonify({"msg": "Message not found"}), 404

        # Verify user is in the conversation
        if profile not in message.conversation.participants:
            return jsonify({"msg": "Unauthorized"}), 403

        data = request.json
        if not data:
            return jsonify({"msg": "Request body is required"}), 400

        emoji = data.get('emoji', '').strip()

        if not emoji:
            return jsonify({"msg": "Emoji required"}), 400

        # Validate emoji length (max 10 characters to prevent abuse)
        if len(emoji) > 10:
            return jsonify({"msg": "Emoji too long (max 10 characters)"}), 400

        # Check if reaction already exists
        existing = MessageReaction.query.filter_by(
            message_id=message_id,
            profile_id=profile.id,
            emoji=emoji
        ).first()

        if existing:
            # Remove reaction (toggle)
            db.session.delete(existing)
            db.session.commit()
            return jsonify({"msg": "Reaction removed", "action": "removed"}), 200

        # Add new reaction
        reaction = MessageReaction(
            message_id=message_id,
            profile_id=profile.id,
            emoji=emoji
        )

        db.session.add(reaction)
        db.session.commit()

        return jsonify({
            "msg": "Reaction added",
            "action": "added",
            "reaction": {
                "id": reaction.id,
                "messageId": reaction.message_id,
                "profileId": reaction.profile_id,
                "emoji": reaction.emoji,
                "createdAt": reaction.created_at.isoformat()
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Internal server error", "error": str(e)}), 500


@messaging_bp.route('/api/messages/<int:message_id>/reactions', methods=['GET'])
@jwt_required()
def get_reactions(message_id):
    """Get all reactions for a message"""
    try:
        # Validate message_id
        if message_id <= 0:
            return jsonify({"msg": "Invalid message ID"}), 400

        current_user_id = get_jwt_identity()
        account = Account.query.get(current_user_id)
        if not account:
            return jsonify({"msg": "User not found"}), 404

        profile = account.profiles.first()
        if not profile:
            return jsonify({"msg": "Profile not found"}), 404

        message = Message.query.get(message_id)
        if not message:
            return jsonify({"msg": "Message not found"}), 404

        # Verify user is in the conversation
        if profile not in message.conversation.participants:
            return jsonify({"msg": "Unauthorized"}), 403

        reactions = MessageReaction.query.filter_by(message_id=message_id).all()

        # Group reactions by emoji
        reaction_groups = {}
        for reaction in reactions:
            if reaction.emoji not in reaction_groups:
                reaction_groups[reaction.emoji] = {
                    "emoji": reaction.emoji,
                    "count": 0,
                    "profiles": []
                }
            reaction_groups[reaction.emoji]["count"] += 1
            reaction_groups[reaction.emoji]["profiles"].append({
                "id": reaction.profile_id,
                "name": reaction.profile.name
            })

        return jsonify({
            "reactions": list(reaction_groups.values())
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Internal server error", "error": str(e)}), 500
