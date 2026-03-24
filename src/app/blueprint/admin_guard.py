"""Admin route access guard. Admin endpoints are enabled by default and can be disabled via ADMIN_DASHBOARD_ENABLED."""
import os
from functools import wraps
from flask import jsonify


def require_admin_dashboard_enabled(f):
    """
    Decorator to protect admin routes. Returns 403 only when ADMIN_DASHBOARD_ENABLED is explicitly set to 'false'.
    Note: Checks only .env to ensure security setting cannot be persisted and then forgotten.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin_enabled = os.getenv("ADMIN_DASHBOARD_ENABLED", "true").lower() == "true"
        if not admin_enabled:
            return jsonify({"msg": "Admin dashboard is not enabled"}), 403
        return f(*args, **kwargs)
    return decorated_function
