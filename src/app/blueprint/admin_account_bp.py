from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt  
from ..config import Config
import bcrypt
import json

admin_account_bp = Blueprint('admin_account', __name__)

"""
Admin account management endpoints
Only writes and deletes from local config to avoid issues with Azure App Configuration caching and propagation delays.
Admin accounts are stored in the "ADMIN_ACCOUNTS" config variable as a JSON object with email as key and password hash as value.
"""

@admin_account_bp.route('/api/config/admin-accounts', methods=['GET'])
@jwt_required()
def list_admin_accounts():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"msg": "Admin access denied"}), 403

    admin_accounts = json.loads(Config.get_variable("ADMIN_ACCOUNTS", "{}"))
    print(f"Admin accounts fetched: {list(admin_accounts.keys())}")
    return jsonify({"admin_accounts": list(admin_accounts.keys())}), 200

@admin_account_bp.route('/api/config/admin-accounts', methods=['POST'])
@jwt_required()
def add_admin_account():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"msg": "Admin access denied"}), 403
    data = request.json
    if not data:
        return jsonify({"msg": "Invalid request format"}), 400

    email = data.get("email")
    password = data.get("password")
    admin_accounts = json.loads(Config.get_variable("ADMIN_ACCOUNTS", "{}"))
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()
    
    if not email or not password:
        return jsonify({"msg": "Missing email or password"}), 400
    if email in admin_accounts:
        return jsonify({"msg": "Admin account already exists"}), 409
    if email in admin_accounts:
        return jsonify({"msg": "Admin account already exists"}), 409
    
    admin_accounts[email] = password_hash
    Config.set_variable("ADMIN_ACCOUNTS", json.dumps(admin_accounts), True, False) # Deliberately ignores azure.

    print(f"Admin account added: {email}")

    return jsonify({"msg": "Admin account added successfully"}), 201

@admin_account_bp.route('/api/config/admin-accounts', methods=['DELETE'])
@jwt_required()
def remove_admin_account():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"msg": "Admin access denied"}), 403
    data = request.json
    if not data:
        return jsonify({"msg": "Invalid request format"}), 400

    email = data.get("email")
    if not email:
        return jsonify({"msg": "Missing email"}), 400
    
    admin_accounts = json.loads(Config.get_variable("ADMIN_ACCOUNTS", "{}"))
    if email not in admin_accounts:
        return jsonify({"msg": "Admin account not found"}), 404
    
    del admin_accounts[email]
    Config.set_variable("ADMIN_ACCOUNTS", json.dumps(admin_accounts), True, False) # Deliberately ignores azure.

    print(f"Admin account removed: {email}")

    return jsonify({"msg": "Admin account removed successfully"}), 200
