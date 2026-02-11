"""
WebEx API Endpoints.
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta

from ..model import db
from ..model.account import Account
from ..model.meeting import Meeting
from ..model.meetinginvitation import MeetingInvitation
from ..model.profile import Profile

from ..service.webex_service import WebexService

webex_bp = Blueprint('webex', __name__)

webex_service = WebexService()

@webex_bp.route('/api/webex/auth-url', methods=['GET'])
@jwt_required()
def get_webex_auth_url():
    """Get the WebEx OAuth authorization URL"""
    url = webex_service.get_auth_url()
    return jsonify({"url": url}), 200

@webex_bp.route('/api/webex/connect', methods=['POST'])
@jwt_required()
def connect_webex():
    """Exchange auth code for tokens and store in account"""
    current_user_id = get_jwt_identity()
    account = Account.query.get(current_user_id)

    if not account:
        return jsonify({"msg": "User not found"}), 404
    
    code = request.json.get('code')
    if not code:
        return jsonify({"msg": "Missing auth code"}), 400
    
    try:
        token_data = webex_service.exchange_code(code)

        account.webex_access_token = token_data.get('access_token')
        account.webex_refresh_token = token_data.get('refresh_token')
        # Expires in comes in seconds, calculate expiry time
        expires_in = token_data.get('expires_in')
        if expires_in:
            account.webex_token_expire_at = datetime.utcnow() + timedelta(seconds=expires_in)

        db.session.commit()
        return jsonify({"msg": "WebEx connected successfully"}), 200
    except Exception as e:
        return jsonify({"msg": str(e)}), 500
    
@webex_bp.route('/api/webex/status', methods=['GET'])
@jwt_required()
def get_webex_status():
    """Check if user has connected WebEx"""
    current_user_id = get_jwt_identity()
    account = Account.query.get(current_user_id)
    
    if not account:
        return jsonify({"msg": "User not found"}), 404
        
    connected = account.webex_access_token is not None
    return jsonify({"connected": connected}), 200

@webex_bp.route('/api/webex/disconnect', methods=['POST'])
@jwt_required()
def webex_disconnect():
    current_user_id = get_jwt_identity()
    account = Account.query.get(current_user_id)
    
    if not account:
        return jsonify({"msg": "User not found"}), 404
        
    account.webex_access_token = None
    account.webex_refresh_token = None
    account.webex_token_expires_at = None
    
    db.session.commit()
    
    return jsonify({"msg": "Disconnected from WebEx successfully"})

@webex_bp.route('/api/webex/meeting', methods=['POST'])
@jwt_required()
def create_webex_meeting():
    """Create a WebEx meeting and save to DB"""
    current_user_id = get_jwt_identity() # Account ID
    account = Account.query.get(current_user_id)
    
    if not account:
        return jsonify({"msg": "User not found"}), 404
        
    # Assuming the account has one profile/classroom for now, or we pick the first one
    # The frontend should ideally send the profile_id, but for now we default to the first one.
    creator_profile = account.profiles.first()
    if not creator_profile:
         return jsonify({"msg": "No profile found for account"}), 400
    
    data = request.json
    title = data.get('title', 'Classroom Meeting')
    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')
    classroom_id = data.get('classroom_id') # The participant classroom ID (the one we are calling)
    
    if not classroom_id:
        return jsonify({"msg": "classroom_id is required"}), 400
    
    # Check if it's a dummy classroom ID (for development/testing)
    if isinstance(classroom_id, str) and classroom_id.startswith('dummy_'):
        return jsonify({"msg": "Cannot invite dummy classrooms. Please use real classrooms from your network."}), 400
    
    # Convert to int if it's a numeric string
    try:
        classroom_id = int(classroom_id)
    except (ValueError, TypeError):
        return jsonify({"msg": "Invalid classroom_id format"}), 400
    
    receiver_profile = Profile.query.get(classroom_id)
    if not receiver_profile:
        return jsonify({"msg": "Receiver classroom not found"}), 404
    
    # Prevent inviting yourself
    if creator_profile.id == receiver_profile.id:
        return jsonify({"msg": "You cannot invite your own classroom"}), 400
    
    if not start_time_str or not end_time_str:
         # Default to instant meeting (now + 1 hour)
         start_time = datetime.utcnow()
         end_time = start_time + timedelta(hours=1)
    else:
        try:
            # Handle potential Z suffix
            if start_time_str.endswith('Z'):
                start_time_str = start_time_str[:-1]
            if end_time_str.endswith('Z'):
                end_time_str = end_time_str[:-1]
                
            start_time = datetime.fromisoformat(start_time_str)
            end_time = datetime.fromisoformat(end_time_str)
        except ValueError:
            return jsonify({"msg": "Invalid date format"}), 400

    # Create invitation instead of meeting
    new_invitation = MeetingInvitation(
        sender_profile_id=creator_profile.id,
        receiver_profile_id=receiver_profile.id,
        title=title,
        start_time=start_time,
        end_time=end_time,
        status='pending'
    )
    
    db.session.add(new_invitation)
    db.session.commit()
    
    return jsonify({
        "msg": "Meeting invitation sent successfully",
        "invitation": {
            "id": new_invitation.id,
            "title": new_invitation.title,
            "start_time": new_invitation.start_time.isoformat(),
            "end_time": new_invitation.end_time.isoformat(),
            "status": new_invitation.status
        }
    }), 201

@webex_bp.route('/api/webex/meeting/<int:meeting_id>', methods=['GET', 'DELETE', 'PUT'])
@jwt_required()
def manage_meeting(meeting_id):
    """Manage a specific meeting (Get Details, Delete, Update)"""
    current_user_id = get_jwt_identity()
    account = Account.query.get(current_user_id)
    
    if not account:
        return jsonify({"msg": "User not found"}), 404
        
    meeting = Meeting.query.get(meeting_id)
    if not meeting:
        return jsonify({"msg": "Meeting not found"}), 404
        
    # Check authorization (creator or participant)
    profile = account.profiles.first()
    if not profile:
        return jsonify({"msg": "Profile not found"}), 404
        
    is_creator = meeting.creator_id == profile.id
    is_participant = profile in meeting.participants
    
    if not (is_creator or is_participant):
        return jsonify({"msg": "Unauthorized"}), 403

    # Relaxed WebEx check: Only strict for modifying/deleting. GET is allowed for participants without WebEx.
    
    # Refresh token logic (only if connected)
    if account.webex_access_token and account.webex_token_expires_at and account.webex_token_expires_at < datetime.utcnow():
        try:
             token_data = webex_service.refresh_access_token(account.webex_refresh_token)
             account.webex_access_token = token_data.get('access_token')
             account.webex_refresh_token = token_data.get('refresh_token', account.webex_refresh_token)
             expires_in = token_data.get('expires_in')
             if expires_in:
                 account.webex_token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
             db.session.commit()
        except Exception as e:
            # If refresh fails, we might still allow GET if it doesn't need fresh WebEx access
            print(f"Failed to refresh WebEx session: {e}")
            # If we were strictly needing it, we'd fail later or in specific methods.


    if request.method == 'GET':
        return jsonify({
            "id": meeting.id,
            "title": meeting.title,
            "start_time": meeting.start_time.isoformat(),
            "end_time": meeting.end_time.isoformat(),
            "web_link": meeting.web_link,
            "password": meeting.password,
            "creator_name": meeting.creator.name,
            "is_creator": is_creator
        }), 200

    if request.method == 'DELETE':
        if not is_creator:
            return jsonify({"msg": "Only default creator can delete meetings"}), 403
            
        if not account.webex_access_token:
             return jsonify({"msg": "WebEx not connected. Cannot delete meeting."}), 403
            
        try:
            # Delete from WebEx
            if meeting.webex_id:
                webex_service.delete_meeting(account.webex_access_token, meeting.webex_id)
            
            # Delete from DB
            db.session.delete(meeting)
            db.session.commit()
            return jsonify({"msg": "Meeting deleted successfully"}), 200
        except Exception as e:
            return jsonify({"msg": f"Failed to delete meeting: {str(e)}"}), 500

    if request.method == 'PUT':
        if not is_creator:
            return jsonify({"msg": "Only creator can update meetings"}), 403
            
        if not account.webex_access_token:
             return jsonify({"msg": "WebEx not connected. Cannot update meeting."}), 403
            
        data = request.json
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')
        
        try:
            if start_time_str:
                if start_time_str.endswith('Z'): start_time_str = start_time_str[:-1]
                meeting.start_time = datetime.fromisoformat(start_time_str)
            if end_time_str:
                if end_time_str.endswith('Z'): end_time_str = end_time_str[:-1]
                meeting.end_time = datetime.fromisoformat(end_time_str)
                
            # Update WebEx
            if meeting.webex_id:
                webex_service.update_meeting(
                    account.webex_access_token, 
                    meeting.webex_id,
                    meeting.start_time,
                    meeting.end_time
                )
            
            db.session.commit()
            return jsonify({"msg": "Meeting updated successfully"}), 200
        except ValueError:
             return jsonify({"msg": "Invalid date format"}), 400
        except Exception as e:
            return jsonify({"msg": f"Failed to update meeting: {str(e)}"}), 500
        
@webex_bp.route('/api/webex/invitations', methods=['GET'])
@jwt_required()
def get_pending_invitations():
    """Get invitations received by the current user's classroom"""
    current_user_id = get_jwt_identity()
    account = Account.query.get(current_user_id)
    
    if not account:
        return jsonify({"msg": "User not found"}), 404
    
    receiver_profile = account.profiles.first()
    if not receiver_profile:
        return jsonify({"msg": "No profile found for account"}), 400
    
    # Get only pending invitations (accepted ones are already shown in meetings)
    invitations = MeetingInvitation.query.filter_by(
        receiver_profile_id=receiver_profile.id,
        status='pending'
    ).order_by(MeetingInvitation.created_at.desc()).all()
    
    result = []
    for inv in invitations:
        result.append({
            "id": inv.id,
            "title": inv.title,
            "start_time": inv.start_time.isoformat(),
            "end_time": inv.end_time.isoformat(),
            "sender_name": inv.sender.name,
            "status": inv.status,
            "created_at": inv.created_at.isoformat()
        })
    
    return jsonify({"invitations": result}), 200

@webex_bp.route('/api/webex/invitations/sent', methods=['GET'])
@jwt_required()
def get_sent_invitations():
    """Get invitations sent by the current user's classroom"""
    current_user_id = get_jwt_identity()
    account = Account.query.get(current_user_id)
    
    if not account:
        return jsonify({"msg": "User not found"}), 404
    
    sender_profile = account.profiles.first()
    if not sender_profile:
        return jsonify({"msg": "No profile found for account"}), 400
    
    # Get only pending invitations (accepted ones are already shown in meetings)
    invitations = MeetingInvitation.query.filter_by(
        sender_profile_id=sender_profile.id,
        status='pending'
    ).order_by(MeetingInvitation.created_at.desc()).all()
    
    result = []
    for inv in invitations:
        result.append({
            "id": inv.id,
            "title": inv.title,
            "start_time": inv.start_time.isoformat(),
            "end_time": inv.end_time.isoformat(),
            "receiver_name": inv.receiver.name,
            "status": inv.status,
            "created_at": inv.created_at.isoformat()
        })
    
    return jsonify({"sent_invitations": result}), 200

@webex_bp.route('/api/webex/invitations/<int:invitation_id>/accept', methods=['POST'])
@jwt_required()
def accept_invitation(invitation_id):
    """Accept a meeting invitation and create the WebEx meeting"""
    current_user_id = get_jwt_identity()
    account = Account.query.get(current_user_id)
    
    if not account:
        return jsonify({"msg": "User not found"}), 404
    
    receiver_profile = account.profiles.first()
    if not receiver_profile:
        return jsonify({"msg": "No profile found for account"}), 400
    
    invitation = MeetingInvitation.query.get(invitation_id)
    if not invitation:
        return jsonify({"msg": "Invitation not found"}), 404
    
    # Verify the invitation is for this user
    if invitation.receiver_profile_id != receiver_profile.id:
        return jsonify({"msg": "This invitation is not for you"}), 403
    
    if invitation.status != 'pending':
        return jsonify({"msg": f"Invitation is already {invitation.status}"}), 400
    
    # Check if the sender has WebEx connected
    sender_account = invitation.sender.account
    if not sender_account.webex_access_token:
        return jsonify({"msg": "The meeting organizer's WebEx account is not connected"}), 403
    
    # Refresh WebEx token if expired
    if sender_account.webex_token_expires_at and sender_account.webex_token_expires_at < datetime.utcnow():
        try:
            token_data = webex_service.refresh_access_token(sender_account.webex_refresh_token)
            sender_account.webex_access_token = token_data.get('access_token')
            sender_account.webex_refresh_token = token_data.get('refresh_token', sender_account.webex_refresh_token)
            expires_in = token_data.get('expires_in')
            if expires_in:
                sender_account.webex_token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            db.session.commit()
        except Exception as e:
            return jsonify({"msg": "Failed to refresh organizer's WebEx session. Please try again later."}), 403
    
    # Create meeting via WebEx using the sender's token
    try:
        webex_meeting = webex_service.create_meeting(
            sender_account.webex_access_token,
            invitation.title,
            invitation.start_time,
            invitation.end_time
        )
    except Exception as e:
        return jsonify({"msg": f"Failed to create WebEx meeting: {str(e)}"}), 500
    
    # Create meeting in database with sender as creator
    new_meeting = Meeting(
        webex_id=webex_meeting.get('id'),
        title=webex_meeting.get('title', invitation.title),
        start_time=invitation.start_time,
        end_time=invitation.end_time,
        web_link=webex_meeting.get('webLink'),
        password=webex_meeting.get('password'),
        creator_id=invitation.sender_profile_id
    )
    
    # Add the accepting classroom as a participant
    new_meeting.participants.append(receiver_profile)
    
    db.session.add(new_meeting)
    
    # Update invitation status
    invitation.status = 'accepted'
    invitation.meeting_id = new_meeting.id
    
    db.session.commit()
    
    return jsonify({
        "msg": "Invitation accepted. Meeting created successfully!",
        "meeting": {
            "id": new_meeting.id,
            "title": new_meeting.title,
            "web_link": new_meeting.web_link,
            "start_time": new_meeting.start_time.isoformat(),
            "end_time": new_meeting.end_time.isoformat(),
            "password": new_meeting.password
        }
    }), 201

@webex_bp.route('/api/webex/invitations/<int:invitation_id>/decline', methods=['POST'])
@jwt_required()
def decline_invitation(invitation_id):
    """Decline a meeting invitation"""
    current_user_id = get_jwt_identity()
    account = Account.query.get(current_user_id)
    
    if not account:
        return jsonify({"msg": "User not found"}), 404
    
    receiver_profile = account.profiles.first()
    if not receiver_profile:
        return jsonify({"msg": "No profile found for account"}), 400
    
    invitation = MeetingInvitation.query.get(invitation_id)
    if not invitation:
        return jsonify({"msg": "Invitation not found"}), 404
    
    # Verify the invitation is for this user
    if invitation.receiver_profile_id != receiver_profile.id:
        return jsonify({"msg": "This invitation is not for you"}), 403
    
    if invitation.status != 'pending':
        return jsonify({"msg": f"Invitation is already {invitation.status}"}), 400
    
    # Update invitation status to declined
    invitation.status = 'declined'
    db.session.commit()
    
    return jsonify({
        "msg": "Invitation declined successfully"
    }), 200

@webex_bp.route('/api/webex/invitations/<int:invitation_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_invitation(invitation_id):
    """Cancel a sent meeting invitation (only sender can cancel)"""
    current_user_id = get_jwt_identity()
    account = Account.query.get(current_user_id)
    
    if not account:
        return jsonify({"msg": "User not found"}), 404
    
    sender_profile = account.profiles.first()
    if not sender_profile:
        return jsonify({"msg": "No profile found for account"}), 400
    
    invitation = MeetingInvitation.query.get(invitation_id)
    if not invitation:
        return jsonify({"msg": "Invitation not found"}), 404
    
    # Verify the invitation was sent by this user
    if invitation.sender_profile_id != sender_profile.id:
        return jsonify({"msg": "You can only cancel invitations you sent"}), 403
    
    if invitation.status != 'pending':
        return jsonify({"msg": f"Cannot cancel {invitation.status} invitation"}), 400
    
    # Update invitation status to cancelled
    invitation.status = 'cancelled'
    db.session.commit()
    
    return jsonify({
        "msg": "Invitation cancelled successfully"
    }), 200