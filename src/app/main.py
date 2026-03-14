"""
Main Flask application for PenPals backend.
Handles authentication, basic profile operations, and ChromaDB document management.
Account and classroom management is handled by separate blueprints.
"""

from flask import Flask, jsonify, request, g
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import timedelta
from sqlalchemy import desc
import os
import bcrypt
import json
import time
import math

from dotenv import load_dotenv
load_dotenv()

from .service.health_check_service import HealthCheckService

from .model import db
from .model.account import Account
from .model.notification import Notification
from .model.profile import Profile
from .model.relation import Relation
from .model.recentcall import RecentCall

from .blueprint.account_bp import account_bp
from .blueprint.chat_bp import chat_bp
from .blueprint.chroma_bp import chroma_bp, chroma_service
from .blueprint.dashboard_bp import dashboard_bp
from .blueprint.friends_bp import friends_bp
from .blueprint.meeting_bp import meeting_bp
from .blueprint.notification_bp import notification_bp
from .blueprint.posts_bp import post_bp
from .blueprint.profile_bp import profile_bp
from .blueprint.webex_bp import webex_bp, webex_service

from .helper import PenpalsHelper as helper
from .config import Config

def print_tables():
    with application.app_context():
        print("Registered tables:", [table.name for table in db.metadata.sorted_tables])

application = Flask(__name__)
CORS(application)
print_tables()

# Respect reverse-proxy headers (e.g., X-Forwarded-Proto) in deployed environments.
application.wsgi_app = ProxyFix(application.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

application.config['SECRET_KEY'] = Config.get_variable('FLASK_SECRET_KEY')
application.config['JWT_SECRET_KEY'] = Config.get_variable('JWT_SECRET_KEY')
application.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
application.config['PREFERRED_URL_SCHEME'] = Config.get_variable('PREFERRED_URL_SCHEME', 'http')

db_uri = Config.get_variable('SQLALCHEMY_DATABASE_URI', 'sqlite:///penpals_db/penpals.db')
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

# initialize healtcheck service
health_check_service = HealthCheckService()

# register blue prints for API endpoints
application.register_blueprint(account_bp)
application.register_blueprint(chat_bp)
application.register_blueprint(chroma_bp)
application.register_blueprint(dashboard_bp)
application.register_blueprint(friends_bp)
application.register_blueprint(meeting_bp)
application.register_blueprint(notification_bp)
application.register_blueprint(post_bp)
application.register_blueprint(profile_bp)
application.register_blueprint(webex_bp)

# latency tracking

@application.before_request
def start_timer():
    g.start_time = time.perf_counter()

@application.after_request
def log_latency(response):
    if hasattr(g, 'start_time'):
        # Calculate the delta in milliseconds
        latency = math.floor((time.perf_counter() - g.start_time) * 1000)
        request_log = f"[{request.method}] {request.path}"
        health_check_service.log_latency(request_log,latency)
        print(f"{request_log} - Latency: {latency:.2f}ms")
    return response


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
    
    # Check if account exists
    if Account.query.filter_by(email=email).first():
        return jsonify({"msg": "Account already exists"}), 409
    
    # Password is a client-side SHA-256 hash; bcrypt it for storage
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()
    
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
    
    # compare against admin accounts first
    admin_accounts = json.loads(Config.get_variable("ADMIN_ACCOUNTS", "{}"))
    if email in admin_accounts:
        admin_password_hash = admin_accounts[email]
        if bcrypt.checkpw(password.encode(), admin_password_hash.encode()):
            claims = {"role": "admin"}
            access_token = create_access_token(identity=email, additional_claims=claims)
            account_id = email
            return jsonify({
                "access_token": access_token,
                "account_id": account_id,
            }), 200

    # then compare against user accounts

    account = Account.query.filter_by(email=email).first()
    
    # Password is a client-side SHA-256 hash; bcrypt it and compare
    if not account or not bcrypt.checkpw(password.encode(), account.password_hash.encode()):
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
            "latitude": classroom.latitude,
            "longitude": classroom.longitude,
            "class_size": classroom.class_size,
            "description": classroom.description,
            "avatar": classroom.avatar,
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

@application.route('/api/health', methods=['GET'])
def health_check():
    health_status = health_check_service.perform_comprehensive_health_check(chroma_service, webex_service, db)
    status = health_status.get("status", "unhealthy")

    # Use a dictionary to map status to HTTP codes
    status_codes = {
        "healthy": 200,
        "degraded": 200,
        "unhealthy": 503  # Standard practice is 503 (Service Unavailable)
    }

    # Get the code, defaulting to 500 if something totally unexpected happens
    http_code = status_codes.get(status, 500)

    return jsonify({
        "status": status,
        "details": health_status
    }), http_code


# admin dahsboard routes

@application.route('/auth/admin', methods=['GET'])
@jwt_required()
def authenticate_admin():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"msg": "Admin access denied"}), 403
    return jsonify({"msg": "Admin authenticated successfully"}), 200

@application.route('/api/config', methods=['GET'])
@jwt_required()
def admin_config_status():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"msg": "Admin access denied"}), 403


    status = {
        "safe_get_keys_whitelist": Config.settings["safe_get_keys_whitelist"], # list[str]
        "safe_set_keys_whitelist": Config.settings["safe_set_keys_whitelist"], # list[str]
        "current_safe_variables": Config.get_all_safe_variables() # dictionary{str:str}
    }
    return jsonify(status), 200


@application.route('/api/config', methods=['POST'])
@jwt_required()
def admin_config_update():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"msg": "Admin access denied"}), 403
    data = request.json
    if not data:
        return jsonify({"msg": "Invalid request format"}), 400
    key = data.get("key")
    value = data.get("value")
    ignore_azure = data.get("ignoreAzure", False)
    Config.safe_set_variable(key, value, ignore_azure=ignore_azure)
    return jsonify({"msg": "Configuration updated successfully"}), 200

if __name__ == '__main__':
    application.run(host='0.0.0.0', port=5001)
