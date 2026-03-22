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

from ..config import Config

from ..service.webex_service import WebexService
from ..service.meeting_helper import _get_primary_profile, _get_participant_count, _ensure_meeting_created_with_webex, _meeting_has_profile, _normalize_invitee_ids, _serialize_meeting, _sync_meeting_in_chroma

webex_bp = Blueprint('webex', __name__)

webex_service = WebexService()

MEETING_MIN_DURATION_MINUTES = None
MEETING_MAX_DURATION_MINUTES = None
MEETING_MAX_ADVANCE_DAY = None

def _ensure_meeting_schedule_limits_loaded():
    global MEETING_MIN_DURATION_MINUTES, MEETING_MAX_DURATION_MINUTES, MEETING_MAX_ADVANCE_DAY

    if MEETING_MIN_DURATION_MINUTES is None:
        MEETING_MIN_DURATION_MINUTES = Config.get_variable("MEETING_MIN_DURATION_MINUTES", 15)
    if MEETING_MAX_DURATION_MINUTES is None:
        MEETING_MAX_DURATION_MINUTES = Config.get_variable("MEETING_MAX_DURATION_MINUTES", 60)
    if MEETING_MAX_ADVANCE_DAY is None:
        MEETING_MAX_ADVANCE_DAY = Config.get_variable("MEETING_MAX_ADVANCE_DAY", 14)

def validate_meeting_schedule(start_time: datetime, end_time: datetime):
    _ensure_meeting_schedule_limits_loaded()

    if end_time <= start_time:
        return "end_time must be after start_time"

    duration_minutes = (end_time - start_time).total_seconds() / 60
    if duration_minutes < MEETING_MIN_DURATION_MINUTES or duration_minutes > MEETING_MAX_DURATION_MINUTES:
        return f"Meeting duration must be between {MEETING_MIN_DURATION_MINUTES} and {MEETING_MAX_DURATION_MINUTES} minutes"
    
    max_allowed_start = datetime.utcnow() + timedelta(days=MEETING_MAX_ADVANCE_DAY)
    if start_time > max_allowed_start:
        return f"Meetings can be scheduled up to {MEETING_MAX_ADVANCE_DAY} day in advance"
    
    return None

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
    """Create a pending meeting plan and invitations (public/private)."""
    current_user_id = get_jwt_identity()
    account = Account.query.get(current_user_id)
    
    if not account:
        return jsonify({"msg": "User not found"}), 404
        
    creator_profile = _get_primary_profile(account)
    if not creator_profile:
         return jsonify({"msg": "No profile found for account"}), 400
    
    data = request.json or {}
    title = data.get('title', 'Classroom Meeting')
    description = str(data.get('description') or '').strip()
    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')
    is_public = bool(data.get('is_public', False))
    max_participants = data.get('max_participants')

    legacy_classroom_id = data.get('classroom_id')
    classroom_ids = data.get('classroom_ids') or []
    if legacy_classroom_id is not None:
        classroom_ids.append(legacy_classroom_id)

    normalized_ids, normalize_error = _normalize_invitee_ids(classroom_ids, creator_profile.id)
    if normalize_error:
        return jsonify({"msg": normalize_error}), 400

    if not is_public and len(normalized_ids) == 0:
        return jsonify({"msg": "classroom_id or classroom_ids is required for private meetings"}), 400

    if max_participants is not None:
        try:
            max_participants = int(max_participants)
        except (ValueError, TypeError):
            return jsonify({"msg": "max_participants must be a number"}), 400
        if max_participants < 2:
            return jsonify({"msg": "max_participants must be at least 2"}), 400
    
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
        
    schedule_error = validate_meeting_schedule(start_time, end_time)
    if schedule_error:
        return jsonify({"msg": schedule_error}), 400

    # Create invitation instead of meeting
    new_meeting = Meeting()
    new_meeting.title = title
    new_meeting.description = description
    new_meeting.start_time = start_time
    new_meeting.end_time = end_time
    new_meeting.creator_id = creator_profile.id
    new_meeting.visibility = 'public' if is_public else 'private'
    new_meeting.status = 'pending_setup'
    new_meeting.max_participants=max_participants
    new_meeting.join_count = 0
    
    db.session.add(new_meeting)
    db.session.flush()

    invitations = []
    for receiver_id in normalized_ids:
        receiver_profile = Profile.query.get(receiver_id)
        if not receiver_profile:
            db.session.rollback()
            return jsonify({"msg": f"Receiver classroom not found: {receiver_id}"}), 404

        invitation = MeetingInvitation()
        invitation.sender_profile_id = creator_profile.id
        invitation.receiver_profile_id = receiver_profile.id
        invitation.title = title 
        invitation.start_time = start_time
        invitation.end_time = end_time
        invitation.status = 'pending'
        invitation.meeting_id = new_meeting.id

        db.session.add(invitation)
        invitations.append(invitation)

    db.session.commit()

    _sync_meeting_in_chroma(new_meeting)

    invitations_payload = [{
        "id": inv.id,
        "receiver_id": inv.receiver_profile_id,
        "receiver_name": inv.receiver.name,
        "title": inv.title,
        "start_time": inv.start_time.isoformat(),
        "end_time": inv.end_time.isoformat(),
        "status": inv.status,
        "meeting_id": inv.meeting_id
    } for inv in invitations]

    message = "Public meeting created successfully" if is_public else "Meeting invitation sent successfully"
    
    return jsonify({
        "msg": message,
        "meeting": _serialize_meeting(new_meeting, creator_profile, account),
        "invitation": invitations_payload[0] if len(invitations_payload) == 1 else None,
        "invitations": invitations_payload
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
    profile = _get_primary_profile(account)
    if not profile:
        return jsonify({"msg": "Profile not found"}), 404
        
    is_creator = bool(meeting.creator and meeting.creator.account_id == account.id)
    is_participant = _meeting_has_profile(meeting, profile) and not is_creator

    can_view_public = meeting.visibility == 'public' and meeting.status in ['pending_setup', 'active']
    if request.method == 'GET':
        if not (is_creator or is_participant or can_view_public):
            return jsonify({"msg": "Unauthorized"}), 403
    elif not (is_creator or is_participant):
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
        return jsonify(_serialize_meeting(meeting, profile, account, include_invitees=True)), 200

    if request.method == 'DELETE':
        if not is_creator:
            return jsonify({"msg": "Only default creator can delete meetings"}), 403
              
        try:
            # Delete from WebEx
            if meeting.webex_id:
                if not account.webex_access_token:
                    return jsonify({"msg": "WebEx not connected. Cannot delete active meeting."}), 403
                webex_service.delete_meeting(account.webex_access_token, meeting.webex_id)
            
            # Soft-cancel meeting so invite/history references remain valid
            meeting.status = 'cancelled'
            pending_invitations = MeetingInvitation.query.filter_by(meeting_id=meeting.id, status='pending').all()
            for invitation in pending_invitations:
                invitation.status = 'cancelled'

            db.session.commit()
            _sync_meeting_in_chroma(meeting)
            return jsonify({"msg": "Meeting cancelled successfully"}), 200
        except Exception as e:
            return jsonify({"msg": f"Failed to cancel meeting: {str(e)}"}), 500

    if request.method == 'PUT':
        if not is_creator:
            return jsonify({"msg": "Only creator can update meetings"}), 403
            
        data = request.json or {}
        title = data.get('title')
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')

        visibility = data.get('visibility')
        max_participants = data.get('max_participants')
        description = data.get('description')
        if title is not None:
            title = str(title).strip()
            if not title:
                return jsonify({"msg": "title cannot be empty"}), 400
        if description is not None:
            description = str(description).strip()

        if visibility is not None and visibility not in ['private', 'public']:
            return jsonify({"msg": "visibility must be 'private' or 'public'"}), 400

        parsed_max_participants = meeting.max_participants
        if max_participants is not None:
            if max_participants == '':
                parsed_max_participants = None
            else:
                try:
                    parsed_max_participants = int(max_participants)
                except (ValueError, TypeError):
                    return jsonify({"msg": "max_participants must be a number"}), 400
                if parsed_max_participants < 2:
                    return jsonify({"msg": "max_participants must be at least 2"}), 400
        
        try:
            if title is not None:
                meeting.title = title
            if start_time_str:
                if start_time_str.endswith('Z'): start_time_str = start_time_str[:-1]
                meeting.start_time = datetime.fromisoformat(start_time_str)
            if end_time_str:
                if end_time_str.endswith('Z'): end_time_str = end_time_str[:-1]
                meeting.end_time = datetime.fromisoformat(end_time_str)
                
            if visibility is not None:
                meeting.visibility = visibility
            if max_participants is not None:
                meeting.max_participants = parsed_max_participants
            if description is not None:
                meeting.description = description

            schedule_error = validate_meeting_schedule(meeting.start_time, meeting.end_time)
            if schedule_error:
                return jsonify({"msg": schedule_error}), 400
            
            participant_count = _get_participant_count(meeting)
            if meeting.max_participants and meeting.max_participants < participant_count:
                return jsonify({"msg": f"max_participants cannot be lower than current participant count ({participant_count})"}), 400

            # Update WebEx
            if meeting.webex_id:
                if not account.webex_access_token:
                    return jsonify({"msg": "WebEx not connected. Cannot update active meeting."}), 403
                webex_service.update_meeting(
                    account.webex_access_token, 
                    meeting.webex_id,
                    meeting.start_time,
                    meeting.end_time,
                    meeting.title
                )
            pending_invitations = MeetingInvitation.query.filter_by(meeting_id=meeting.id, status='pending').all()
            for invitation in pending_invitations:
                invitation.title = meeting.title
                invitation.start_time = meeting.start_time
                invitation.end_time = meeting.end_time
            
            db.session.commit()
            _sync_meeting_in_chroma(meeting)
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
    
    receiver_profile = _get_primary_profile(account)
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
            "created_at": inv.created_at.isoformat(),
            "meeting_id": inv.meeting_id,
            "visibility": inv.meeting.visibility if inv.meeting else 'private'
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
    
    sender_profile = _get_primary_profile(account)
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
            "created_at": inv.created_at.isoformat(),
            "meeting_id": inv.meeting_id,
            "visibility": inv.meeting.visibility if inv.meeting else 'private'
        })
    
    return jsonify({"sent_invitations": result}), 200

@webex_bp.route('/api/webex/invitations/<int:invitation_id>/accept', methods=['POST'])
@jwt_required()
def accept_invitation(invitation_id):
    """Accept a meeting invitation and join/create the planned meeting."""
    current_user_id = get_jwt_identity()
    account = Account.query.get(current_user_id)
    
    if not account:
        return jsonify({"msg": "User not found"}), 404
    
    receiver_profile = _get_primary_profile(account)
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
    
    meeting = invitation.meeting
    if not meeting:
        meeting = Meeting()
        meeting.title=invitation.title
        meeting.start_time=invitation.start_time
        meeting.end_time=invitation.end_time
        meeting.creator_id=invitation.sender_profile_id
        meeting.visibility='private'
        meeting.status='pending_setup'

        db.session.add(meeting)
        db.session.flush()
        invitation.meeting_id = meeting.id

    participant_count = _get_participant_count(meeting)
    if meeting.max_participants and participant_count >= meeting.max_participants and not _meeting_has_profile(meeting, receiver_profile):
        return jsonify({"msg": "Meeting is full"}), 409

    create_error = _ensure_meeting_created_with_webex(meeting)
    if create_error:
        return jsonify({"msg": create_error}), 403

    if not any(p.id == receiver_profile.id for p in meeting.participants):
        meeting.participants.append(receiver_profile)

    meeting.join_count = len(meeting.participants)
    
    # Update invitation status
    invitation.status = 'accepted'
    invitation.meeting_id = meeting.id
    
    db.session.commit()
    
    return jsonify({
        "msg": "Invitation accepted. Meeting joined successfully!",
        "meeting": _serialize_meeting(meeting, receiver_profile, account)
    }), 201

@webex_bp.route('/api/webex/invitations/<int:invitation_id>/decline', methods=['POST'])
@jwt_required()
def decline_invitation(invitation_id):
    """Decline a meeting invitation"""
    current_user_id = get_jwt_identity()
    account = Account.query.get(current_user_id)
    
    if not account:
        return jsonify({"msg": "User not found"}), 404
    
    receiver_profile = _get_primary_profile(account)
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
    
    sender_profile = _get_primary_profile(account)
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

@webex_bp.route('/api/webex/meeting/<int:meeting_id>/invitees', methods=['POST'])
@jwt_required()
def invite_meeting_invitees(meeting_id):
    current_user_id = get_jwt_identity()
    account = Account.query.get(current_user_id)

    if not account:
        return jsonify({"msg": "User not found"}), 404

    meeting = Meeting.query.get(meeting_id)
    if not meeting:
        return jsonify({"msg": "Meeting not found"}), 404

    if not meeting.creator or meeting.creator.account_id != account.id:
        return jsonify({"msg": "Only creator can invite classrooms"}), 403

    sender_profile = meeting.creator

    if meeting.status == 'cancelled':
        return jsonify({"msg": "Cannot invite to a cancelled meeting"}), 409

    data = request.json or {}
    classroom_ids = data.get('classroom_ids')
    normalized_ids, normalize_error = _normalize_invitee_ids(classroom_ids, sender_profile.id)
    if normalize_error:
        return jsonify({"msg": normalize_error}), 400

    if len(normalized_ids) == 0:
        return jsonify({"msg": "classroom_ids is required"}), 400

    created = []
    skipped = []

    for receiver_id in normalized_ids:
        receiver_profile = Profile.query.get(receiver_id)
        if not receiver_profile:
            skipped.append({"receiver_id": receiver_id, "reason": "not_found"})
            continue

        if _meeting_has_profile(meeting, receiver_profile):
            skipped.append({"receiver_id": receiver_id, "receiver_name": receiver_profile.name, "reason": "already_participant"})
            continue

        existing_pending = MeetingInvitation.query.filter_by(
            meeting_id=meeting.id,
            receiver_profile_id=receiver_profile.id,
            status='pending'
        ).first()
        if existing_pending:
            skipped.append({"receiver_id": receiver_id, "receiver_name": receiver_profile.name, "reason": "already_pending"})
            continue

        invitation = MeetingInvitation()
        invitation.sender_profile_id = sender_profile.id
        invitation.receiver_profile_id = receiver_profile.id
        invitation.title = meeting.title
        invitation.start_time = meeting.start_time
        invitation.end_time = meeting.end_time
        invitation.status = 'pending'
        invitation.meeting_id = meeting.id
        
        db.session.add(invitation)
        db.session.flush()

        created.append({
            "id": invitation.id,
            "receiver_id": invitation.receiver_profile_id,
            "receiver_name": receiver_profile.name,
            "title": invitation.title,
            "start_time": invitation.start_time.isoformat(),
            "end_time": invitation.end_time.isoformat(),
            "status": invitation.status,
            "meeting_id": invitation.meeting_id
        })

    db.session.commit()

    if len(created) == 0:
        return jsonify({
            "msg": "No new invitations were created",
            "invitations": created,
            "skipped": skipped
        }), 200

    return jsonify({
        "msg": "Invitations sent successfully",
        "invitations": created,
        "skipped": skipped
    }), 201
