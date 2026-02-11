"""
Main Flask application for PenPals backend.
Handles authentication, basic profile operations, and ChromaDB document management.
Account and classroom management is handled by separate blueprints.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
from sqlalchemy import desc
import os

from dotenv import load_dotenv
load_dotenv()

from .model import db
from .model.account import Account
from .model.notification import Notification
from .model.profile import Profile
from .model.relation import Relation
from .model.recentcall import RecentCall

from .blueprint.account_bp import account_bp
from .blueprint.chroma_bp import chroma_bp
from .blueprint.friends_bp import friends_bp
from .blueprint.meeting_bp import meeting_bp
from .blueprint.notification_bp import notification_bp
from .blueprint.posts_bp import post_bp
from .blueprint.profile_bp import profile_bp
from .blueprint.webex_bp import webex_bp

def print_tables():
    with application.app_context():
        print("Registered tables:", [table.name for table in db.metadata.sorted_tables])

application = Flask(__name__)
CORS(application)
print_tables()

application.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
application.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
application.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

db_uri = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///penpals_db/penpals.db')
if db_uri.startswith('sqlite:///') and not db_uri.startswith('sqlite:////'):
    rel_path = db_uri.replace('sqlite:///', '', 1)
    # Ensure the directory exists
    db_dir = os.path.dirname(rel_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    abs_path = os.path.abspath(rel_path)
    db_uri = f'sqlite:///{abs_path}'
application.config['SQLALCHEMY_DATABASE_URI'] = db_uri
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

capital_letters = [chr(i) for i in range(ord('A'), ord('Z')+1)]
lowercase_letters = [chr(i) for i in range(ord('a'), ord('z')+1)]
digits = [str(i) for i in range(10)]

db.init_app(application)
jwt = JWTManager(application)

# Initialize database tables
with application.app_context():
    db.create_all()
    print("Database initialized successfully!")

# register blue prints for API endpoints
application.register_blueprint(account_bp)
application.register_blueprint(chroma_bp)
application.register_blueprint(friends_bp)
application.register_blueprint(meeting_bp)
application.register_blueprint(notification_bp)
application.register_blueprint(post_bp)
application.register_blueprint(profile_bp)
application.register_blueprint(webex_bp)

# routes

@application.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new account"""
    data = request.json
    
    if not data:
        return jsonify({"msg": "Invalid request format"}), 400
    
    email = data.get('email')
    password = data.get('password')
    organization = data.get('organization')
    
    if not email or not password:
        return jsonify({"msg": "Missing required fields"}), 400
    
    # Password validation: at least 8 chars, one uppercase, one lowercase, one digit, one special char
    has_upper = any(c in capital_letters for c in password)
    has_lower = any(c in lowercase_letters for c in password)
    has_digit = any(c in digits for c in password)
    has_special = any(
        c not in capital_letters and c not in lowercase_letters and c not in digits
        for c in password
    )
    if not (len(password) >= 8 and has_upper and has_lower and has_digit and has_special):
        return jsonify({
            "msg": "Password must be at least 8 characters and include one uppercase, one lowercase, one digit, and one special character."
        }), 400
    
    # Check if account exists
    if Account.query.filter_by(email=email).first():
        return jsonify({"msg": "Account already exists"}), 409
    
    # Hash password using werkzeug
    password_hash = generate_password_hash(password)
    
    # Create account (no automatic profile creation)
    account = Account()
    account.email = email
    account.password_hash = password_hash
    account.organization = organization
    db.session.add(account)
    db.session.commit()
    
    return jsonify({
        "msg": "Account created successfully",
        "account_id": account.id
    }), 201


@application.route('/api/auth/login', methods=['POST'])
def login():
    """Login and receive JWT token"""
    data = request.json
    
    if not data:
        return jsonify({"msg": "Invalid request format"}), 400
    
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"msg": "Missing email or password"}), 400
    
    account = Account.query.filter_by(email=email).first()
    
    if not account or not check_password_hash(account.password_hash, password):
        return jsonify({"msg": "Invalid credentials"}), 401
    
    # Create JWT token with account ID as identity
    access_token = create_access_token(identity=str(account.id))
    
    return jsonify({
        "access_token": access_token,
        "account_id": account.id
    }), 200


@application.route('/api/auth/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current authenticated user's info, including classrooms and friends"""
    account_id = get_jwt_identity()
    account = Account.query.get(account_id)
    
    if not account:
        return jsonify({"msg": "Account not found"}), 404
    
    # Get all classrooms for this account with friend data
    classrooms = []
    
    # Collect notifications
    notifications = []
    for notif in account.notifications.order_by(desc(Notification.created_at)).all():
        notifications.append({
            "id": str(notif.id),
            "title": notif.title,
            "message": notif.message,
            "type": notif.type,
            "read": notif.read,
            "timestamp": notif.created_at.isoformat()
        })

    for classroom in account.profiles:
        # Fetch friends (relations)
        # We look for accepted relations where this classroom is either sender or receiver
        friends = []
        
        # Sent accepted requests (my friends)
        sent_relations = Relation.query.filter_by(from_profile_id=classroom.id, status='accepted').all()
        for rel in sent_relations:
            friend_profile = Profile.query.get(rel.to_profile_id)
            if friend_profile:
                friends.append({
                    "id": str(friend_profile.id),
                    "classroomId": str(friend_profile.id),
                    "classroomName": friend_profile.name,
                    "location": friend_profile.location,
                    "addedDate": rel.created_at.isoformat() if rel.created_at else None,
                    "friendshipStatus": "accepted"
                })
        
        # Received accepted requests (also my friends)
        received_relations = Relation.query.filter_by(to_profile_id=classroom.id, status='accepted').all()
        for rel in received_relations:
            friend_profile = Profile.query.get(rel.from_profile_id)
            if friend_profile:
                friends.append({
                    "id": str(friend_profile.id),
                    "classroomId": str(friend_profile.id),
                    "classroomName": friend_profile.name,
                    "location": friend_profile.location,
                    "addedDate": rel.created_at.isoformat() if rel.created_at else None,
                    "friendshipStatus": "accepted"
                })
        
        # Received Pending Friend Requests
        received_friend_requests = []
        for req in classroom.received_requests:
            if req.status == 'pending':
                received_friend_requests.append({
                    "id": str(req.id),
                    "senderId": str(req.sender.id),
                    "senderName": req.sender.name,
                    "location": req.sender.location,
                    "sentDate": req.created_at.isoformat()
                })

        # Recent Calls
        recent_calls = []
        # Calls made by this classroom
        for call in classroom.call_history:
            recent_calls.append({
                "id": str(call.id),
                "classroomId": call.target_classroom_id,
                "classroomName": call.target_classroom_name,
                "timestamp": call.timestamp.isoformat(),
                "duration": call.duration_seconds,
                "type": call.call_type
            })

        classrooms.append({
            "id": classroom.id,
            "name": classroom.name,
            "location": classroom.location,
            "latitude": classroom.lattitude,
            "longitude": classroom.longitude,
            "class_size": classroom.class_size,
            "interests": classroom.interests,
            "availability": classroom.availability, 
            "friends": friends,
            "receivedFriendRequests": received_friend_requests,
            "recent_calls": recent_calls
        })
    
    return jsonify({
        "account": {
            "id": account.id,
            "email": account.email,
            "organization": account.organization,
            "notifications": notifications,
            "friends": classrooms[0]["friends"] if classrooms else [], # flatten for convenience if needed by frontend
            "recentCalls": classrooms[0]["recent_calls"] if classrooms else [] # flatten
        },
        "classrooms": classrooms
    }), 200

if __name__ == '__main__':
    application.run(host='0.0.0.0', port=5001)
