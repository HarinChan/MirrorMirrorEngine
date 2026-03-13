"""
Dashboard Webpage endpoints.
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..service.chromadb_service import ChromaDBService

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard/', methods=['GET'])