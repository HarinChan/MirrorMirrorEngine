"""Admin route access guard. Protects admin endpoints unless ADMIN_DASHBOARD_ENABLED is true."""
import os
from functools import wraps
from flask import jsonify


def require_admin_dashboard_enabled(f):
    """
    Decorator to protect admin routes. Returns 403 if ADMIN_DASHBOARD_ENABLED is not set to 'true'.
    Note: Checks only .env to ensure security setting cannot be persisted and then forgotten.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin_enabled = os.getenv("ADMIN_DASHBOARD_ENABLED", "false").lower() == "true"
        if not admin_enabled:
            return jsonify({"msg": "Admin dashboard is not enabled"}), 403
        return f(*args, **kwargs)
    return decorated_function
