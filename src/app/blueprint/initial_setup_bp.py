from flask import Blueprint, jsonify, request, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from ..service.local_config_service import LocalConfigService
from ..config import Config
from .admin_guard import require_admin_dashboard_enabled
from ..service.azure_keyvault_service import AzureKeyVaultService as azkv_service
from ..service.webex_service import WebexService
import json
import bcrypt

initial_setup_bp = Blueprint('initial_setup', __name__)

@initial_setup_bp.route('/admin/initial-setup', methods=['GET'])
@require_admin_dashboard_enabled
def initial_setup_page():
    if Config.initial_setup_completed():
        return render_template('initial_setup_completed.html')
    return render_template('initial_setup_page.html')

@initial_setup_bp.route('/admin/initial-setup', methods=['POST'])
@require_admin_dashboard_enabled
def submit_initial_setup():
    # Handle the submission of the initial setup form.
    data = request.get_json()
    initial_setup_key = data.get("initial_setup_key")
    if initial_setup_key != Config.settings["INITIAL_SETUP_KEY"]:
        return jsonify({"message": "Invalid initial setup key."}), 400
    # Validate and save the provided configuration values.
    # This should include checks to ensure all required keys are present and valid.
    for key in Config.settings["REQUIRED_SETUP_KEYs"]:
        if key not in data or not data[key]:
            return jsonify({"message": f"Missing required configuration: {key}"}), 400
        Config.set_variable(key, data[key], True, False)
    
    # all required keys are set and fulfilled.
    for lookup_key in Config.settings["SUGGESTED_SETUP_KEYs"]:
        if lookup_key in data and data[lookup_key]:
            Config.safe_set_variable(lookup_key, data[lookup_key], True, False)
    
    # Fetch the admin account.
    admin_accounts_json = data.get("ADMIN_ACCOUNTS")
    if not admin_accounts_json:
        return jsonify({"message": "Missing admin account data"}), 400
    new_admin_data = json.loads(admin_accounts_json)
    email, client_side_hash = next(iter(new_admin_data.items()))

    # Add admin Account
    config_admin_accounts = json.loads(Config.get_variable("ADMIN_ACCOUNTS", "{}"))

    if not email or not client_side_hash:
        return jsonify({"msg": "Missing email or password"}), 400
    if email in config_admin_accounts:
        return jsonify({"msg": "Admin account already exists"}), 409
    if email in config_admin_accounts:
        return jsonify({"msg": "Admin account already exists"}), 409

    config_admin_accounts[email] = client_side_hash
    Config.set_variable("ADMIN_ACCOUNTS", json.dumps(config_admin_accounts), True, False) # Deliberately ignores azure.

    print(f"Admin account added: {email}")

    # Process the data and perform necessary actions.

    WebexService.refresh_config() # Refresh WebEx config to ensure new values are loaded.
    azkv_service.refresh_config() # Refresh Azure Key Vault config to ensure new values are loaded.
    return jsonify({"message": "Initial setup completed successfully!"}), 200

@initial_setup_bp.route('/api/initial-setup/reset', methods=['POST'])
@require_admin_dashboard_enabled
@jwt_required()
def factory_reset():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"msg": "Admin access denied"}), 403
    data = request.get_json()
    if data.get("initial_setup_key") != Config.settings["INITIAL_SETUP_KEY"]:
        return jsonify({"message": "Invalid initial setup key."}), 400
    LocalConfigService.delete_all()
    Config.factory_reset()
    return jsonify({"message": "Initial setup has been reset."}), 200


@initial_setup_bp.route('/api/initial-setup/status', methods=['GET'])
def check_initial_setup_status():
    if Config.initial_setup_completed():
        return jsonify({"setup_completed": True}), 200
    else:
        message = {
            "setup_completed": False,
            "message": "Initial setup is not completed.",
            "required_keys": Config.settings["REQUIRED_SETUP_KEYs"],
            "suggested_keys": Config.settings["SUGGESTED_SETUP_KEYs"],
            "hashable_keys": Config.settings["HASHABLE_SETUP_KEYs"],
        }
        return jsonify(message), 200
