"""
Meeting API endpoints.
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta

from ..model import db
from ..model.account import Account
from ..model.meeting import Meeting
from ..model.profile import Profile
from ..config import Config
from ..service.meeting_helper import _serialize_meeting, _ensure_meeting_created_with_webex, _get_participant_count, _get_primary_profile, _meeting_has_profile

TRENDING_LOOKAHEAD_DAYS = Config.get_variable("TRENDING_LOOKAHEAD_DAYS", 14)

meeting_bp = Blueprint('meeting', __name__)

@meeting_bp.route('/api/meetings', methods=['GET'])
@jwt_required()
def get_upcoming_meetings():
    """Get upcoming meetings for the user"""
    current_user_id = get_jwt_identity()
    account = Account.query.get(current_user_id)
    
    if not account:
        return jsonify({"msg": "User not found"}), 404
        
    profile = _get_primary_profile(account)
    if not profile:
        return jsonify({"meetings": []}), 200
        
    now = datetime.utcnow()
    
    # Meetings created by me
    created_meetings = Meeting.query.filter(
        Meeting.creator_id == profile.id,
        Meeting.start_time >= now,
        Meeting.status.in_(['pending_setup', 'active'])
    ).all()
    
    # Meetings I am participating in
    participating_meetings = [
        m for m in profile.meetings
        if m.start_time >= now and m.status in ['pending_setup', 'active']
    ]
    
    all_meetings = list(set(created_meetings + participating_meetings))
    all_meetings.sort(key=lambda x: x.start_time)
    
    result = []
    for m in all_meetings:
        result.append(_serialize_meeting(m, profile, account))
        
    return jsonify({"meetings": result}), 200

@meeting_bp.route('/api/meetings/public', methods=['GET'])
@jwt_required()
def get_public_meetings():
    current_user_id = get_jwt_identity()
    account = Account.query.get(current_user_id)
    if not account:
        return jsonify({"msg": "User not found"}), 404

    profile = _get_primary_profile(account)
    now = datetime.utcnow()

    meetings = Meeting.query.filter(
        Meeting.visibility == 'public',
        Meeting.start_time >= now,
        Meeting.status.in_(['pending_setup', 'active'])
    ).order_by(Meeting.start_time.asc()).all()

    return jsonify({"meetings": [_serialize_meeting(meeting, profile, account) for meeting in meetings]}), 200

@meeting_bp.route('/api/meetings/public/trending', methods=['GET'])
@jwt_required()
def get_public_trending_meetings():
    current_user_id = get_jwt_identity()
    account = Account.query.get(current_user_id)
    if not account:
        return jsonify({"msg": "User not found"}), 404

    profile = _get_primary_profile(account)
    now = datetime.utcnow()
    cutoff = now + timedelta(days=TRENDING_LOOKAHEAD_DAYS)

    meetings = Meeting.query.filter(
        Meeting.visibility == 'public',
        Meeting.start_time >= now,
        Meeting.start_time <= cutoff,
        Meeting.status.in_(['pending_setup', 'active'])
    ).all()

    def score(meeting: Meeting):
        participant_count = _get_participant_count(meeting)
        days_until = max((meeting.start_time - now).total_seconds() / 86400, 0)
        recency_factor = max(0.0, (TRENDING_LOOKAHEAD_DAYS - days_until) / TRENDING_LOOKAHEAD_DAYS)
        return (participant_count * 2.0) + recency_factor

    ranked = sorted(meetings, key=score, reverse=True)
    payload = []
    for meeting in ranked[:25]:
        serialized = _serialize_meeting(meeting, profile, account)
        serialized['trending_score'] = round(score(meeting), 4)
        payload.append(serialized)

    return jsonify({"meetings": payload}), 200

@meeting_bp.route('/api/meetings/<int:meeting_id>/join', methods=['POST'])
@jwt_required()
def join_public_meeting(meeting_id):
    current_user_id = get_jwt_identity()
    account = Account.query.get(current_user_id)
    if not account:
        return jsonify({"msg": "User not found"}), 404

    profile = _get_primary_profile(account)
    if not profile:
        return jsonify({"msg": "No profile found for account"}), 400

    meeting = Meeting.query.get(meeting_id)
    if not meeting:
        return jsonify({"msg": "Meeting not found"}), 404

    if meeting.visibility != 'public':
        return jsonify({"msg": "Only public meetings can be joined directly"}), 403

    if meeting.status == 'cancelled':
        return jsonify({"msg": "Meeting has been cancelled"}), 409

    if _meeting_has_profile(meeting, profile):
        return jsonify({"msg": "Already joined", "meeting": _serialize_meeting(meeting, profile, account)}), 200

    participant_count = _get_participant_count(meeting)
    if meeting.max_participants and participant_count >= meeting.max_participants:
        return jsonify({"msg": "Meeting is full"}), 409

    create_error = _ensure_meeting_created_with_webex(meeting)
    if create_error:
        return jsonify({"msg": create_error}), 403

    meeting.participants.append(profile)
    meeting.join_count = len(meeting.participants)
    db.session.commit()

    return jsonify({
        "msg": "Joined public meeting successfully",
        "meeting": _serialize_meeting(meeting, profile, account)
    }), 200