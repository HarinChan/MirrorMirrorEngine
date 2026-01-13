"""
Account management endpoints for teacher accounts.
Handles account CRUD operations, password updates, and multi-classroom management.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash
from src.app.main import db
from src.app.model.account import Account
from src.app.helper import PenpalsHelper

account_bp = Blueprint('account', __name__)


@account_bp.route('/api/account', methods=['GET'])
@jwt_required()
def get_account():
    """Get current account details with all classrooms"""
    try:
        account_id = get_jwt_identity()
        account = Account.query.get(account_id)
        
        if not account:
            return jsonify({"msg": "Account not found"}), 404
        
        classrooms = []
        for classroom in account.classrooms:
            classroom_data = PenpalsHelper.format_classroom_response(classroom)
            classrooms.append(classroom_data)
        
        return jsonify({
            "account": {
                "id": account.id,
                "email": account.email,
                "organization": account.organization,
                "created_at": account.created_at.isoformat(),
                "classroom_count": len(classrooms)
            },
            "classrooms": classrooms
        }), 200
    
    except Exception as e:
        return jsonify({"msg": "Internal server error", "error": str(e)}), 500


@account_bp.route('/api/account', methods=['PUT'])
@jwt_required()
def update_account():
    """Update account information"""
    try:
        account_id = get_jwt_identity()
        account = Account.query.get(account_id)
        
        if not account:
            return jsonify({"msg": "Account not found"}), 404
        
        data = request.json
        if not data:
            return jsonify({"msg": "No data provided"}), 400
        
        # Validate email format if provided
        if 'email' in data:
            new_email = data['email']
            if not PenpalsHelper.validate_email(new_email):
                return jsonify({"msg": "Invalid email format"}), 400
            
            # Check if email is already taken by another account
            existing = Account.query.filter_by(email=new_email).first()
            if existing and existing.id != account.id:
                return jsonify({"msg": "Email already in use"}), 409
            account.email = new_email
        
        if 'organization' in data:
            organization = data['organization']
            if organization and len(organization.strip()) > 120:
                return jsonify({"msg": "Organization name too long (max 120 characters)"}), 400
            account.organization = organization.strip() if organization else None
        
        if 'password' in data:
            password = data['password']
            if not password or len(password) < 8:
                return jsonify({"msg": "Password must be at least 8 characters long"}), 400
            
            # Enhanced password validation
            capital_letters = [chr(i) for i in range(ord('A'), ord('Z')+1)]
            lowercase_letters = [chr(i) for i in range(ord('a'), ord('z')+1)]
            digits = [str(i) for i in range(10)]
            
            has_upper = any(c in capital_letters for c in password)
            has_lower = any(c in lowercase_letters for c in password)
            has_digit = any(c in digits for c in password)
            has_special = any(
                c not in capital_letters and c not in lowercase_letters and c not in digits
                for c in password
            )
            
            if not (has_upper and has_lower and has_digit and has_special):
                return jsonify({
                    "msg": "Password must include one uppercase, one lowercase, one digit, and one special character."
                }), 400
            
            account.password_hash = generate_password_hash(password)
        
        db.session.commit()
        
        return jsonify({
            "msg": "Account updated successfully",
            "account": {
                "id": account.id,
                "email": account.email,
                "organization": account.organization
            }
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Internal server error", "error": str(e)}), 500


@account_bp.route('/api/account', methods=['DELETE'])
@jwt_required()
def delete_account():
    """Delete account and all associated classrooms"""
    try:
        account_id = get_jwt_identity()
        account = Account.query.get(account_id)
        
        if not account:
            return jsonify({"msg": "Account not found"}), 404
        
        # Get classroom count for confirmation
        classroom_count = account.classrooms.count()
        
        db.session.delete(account)
        db.session.commit()
        
        return jsonify({
            "msg": "Account deleted successfully",
            "deleted_classrooms": classroom_count
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Internal server error", "error": str(e)}), 500


@account_bp.route('/api/account/classrooms', methods=['GET'])
@jwt_required()
def get_account_classrooms():
    """Get all classrooms for the current account with enhanced details"""
    try:
        account_id = get_jwt_identity()
        account = Account.query.get(account_id)
        
        if not account:
            return jsonify({"msg": "Account not found"}), 404
        
        classrooms = []
        for classroom in account.classrooms:
            friends_count = classroom.sent_relations.count()
            classroom_data = PenpalsHelper.format_classroom_response(classroom)
            classroom_data["friends_count"] = friends_count
            classrooms.append(classroom_data)
        
        return jsonify({
            "classrooms": classrooms,
            "total_count": len(classrooms),
            "account_id": account.id
        }), 200
    
    except Exception as e:
        return jsonify({"msg": "Internal server error", "error": str(e)}), 500


@account_bp.route('/api/account/stats', methods=['GET'])
@jwt_required()
def get_account_stats():
    """Get account statistics"""
    try:
        account_id = get_jwt_identity()
        account = Account.query.get(account_id)
        
        if not account:
            return jsonify({"msg": "Account not found"}), 404
        
        total_classrooms = account.classrooms.count()
        total_connections = 0
        all_interests = set()
        
        for classroom in account.classrooms:
            total_connections += classroom.sent_relations.count()
            if classroom.interests:
                all_interests.update(classroom.interests)
        
        return jsonify({
            "account_id": account.id,
            "total_classrooms": total_classrooms,
            "total_connections": total_connections,
            "unique_interests": len(all_interests),
            "account_created": account.created_at.isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({"msg": "Internal server error", "error": str(e)}), 500