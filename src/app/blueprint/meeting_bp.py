"""
Meeting API endpoints.
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

from ..model.account import Account
from ..model.meeting import Meeting

meeting_bp = Blueprint('meeting', __name__)

@meeting_bp.route('/api/meetings', methods=['GET'])
@jwt_required()
def get_upcoming_meetings():
    """Get upcoming meetings for the user"""
    current_user_id = get_jwt_identity()
    account = Account.query.get(current_user_id)
    
    if not account:
        return jsonify({"msg": "User not found"}), 404
        
    profile = account.classrooms.first()
    if not profile:
        return jsonify({"meetings": []}), 200
        
    now = datetime.utcnow()
    
    # Meetings created by me
    created_meetings = Meeting.query.filter(
        Meeting.creator_id == profile.id,
        Meeting.start_time >= now
    ).all()
    
    # Meetings I am participating in
    participating_meetings = [m for m in profile.meetings if m.start_time >= now]
    
    all_meetings = list(set(created_meetings + participating_meetings))
    all_meetings.sort(key=lambda x: x.start_time)
    
    result = []
    for m in all_meetings:
        result.append({
            "id": m.id,
            "title": m.title,
            "start_time": m.start_time.isoformat(),
            "end_time": m.end_time.isoformat(),
            "web_link": m.web_link,
            "password": m.password,
            "creator_name": m.creator.name
        })
        
    return jsonify({"meetings": result}), 200