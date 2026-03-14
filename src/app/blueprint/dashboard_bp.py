"""
DashboardDB API endpoints.
"""
from flask import Blueprint, jsonify, request, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..config import Config

dashboard_bp = Blueprint('dashboard', __name__)

# This route serves the actual webpage
@dashboard_bp.route('/admin/login', methods=['GET'])
def render_login_page():
    return render_template('admin_login.html')

@dashboard_bp.route('/admin/dashboard', methods=['GET'])
def render_dashboard_page():
    return render_template('dashboard.html')
    # let js handle auth and data fetching
