from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..model import db
from ..model.account import Account
from ..model.notification import Notification

notification_bp = Blueprint('notification', __name__)

@notification_bp.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@jwt_required()
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    current_user_id = get_jwt_identity()
    account = Account.query.get(current_user_id)
    
    notif = Notification.query.get(notification_id)
    if not notif or not account or notif.account_id != account.id:
        return jsonify({"msg": "Notification not found"}), 404
        
    notif.read = True
    db.session.commit()
    return jsonify({"msg": "Marked as read"}), 200

@notification_bp.route('/api/notifications/<int:notification_id>', methods=['DELETE'])
@jwt_required()
def delete_notification(notification_id):
    """Delete a notification"""
    current_user_id = get_jwt_identity()
    account = Account.query.get(current_user_id)
    
    notif = Notification.query.get(notification_id)
    if not notif or not account or notif.account_id != account.id:
        return jsonify({"msg": "Notification not found"}), 404
        
    # We can either soft delete or hard delete. Hard delete for now.
    db.session.delete(notif)
    db.session.commit()
    return jsonify({"msg": "Deleted"}), 200