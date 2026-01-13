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
import os

from dotenv import load_dotenv
load_dotenv()

from .model.account import Account
from .model.profile import Profile
from .model.relation import Relation
from .model.post import Post
from .model import db

from .blueprint.account_bp import account_bp
from .blueprint.profile_bp import profile_bp

from .chromadb.chromadb_service import ChromaDBService

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
application.register_blueprint(profile_bp)

chroma_service = ChromaDBService(persist_directory="./chroma_db", collection_name="penpals_documents")

# routes

@application.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new account"""
    data = request.json
    
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
    account = Account(email=email, password_hash=password_hash, organization=organization)
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
    """Get current authenticated user's info"""
    account_id = get_jwt_identity()
    account = Account.query.get(account_id)
    
    if not account:
        return jsonify({"msg": "Account not found"}), 404
    
    # Get all classrooms for this account
    classrooms = []
    for classroom in account.classrooms:
        classrooms.append({
            "id": classroom.id,
            "name": classroom.name,
            "location": classroom.location,
            "latitude": classroom.lattitude,  # Note: keeping original typo for consistency
            "longitude": classroom.longitude,
            "class_size": classroom.class_size,
            "interests": classroom.interests
        })
    
    return jsonify({
        "account": {
            "id": account.id,
            "email": account.email,
            "organization": account.organization
        },
        "classrooms": classrooms
    }), 200

@application.route('/api/profiles/get', methods=["GET"])
def get_profile():
    """Get profile by ID"""
    data = request.json

    id = data.get('id')

    if not id:
        return jsonify({"msg": "Profile not found"}), 404
    
    profile = Profile.query.filter_by(id=id).first()

    if not profile:
        return jsonify({"msg": "Profile not found"}), 404
    
    return jsonify({
        "id": profile.id,
        "account_id": profile.account_id,
        "name": profile.name,
        "location": profile.location,
        "lattitude": profile.lattitude,
        "longitude": profile.longitude,
        "class_size": profile.class_size,
        "availability": profile.availability,
        "interests": profile.interests
    }), 200

# Create a new profile from JSON
@application.route('/api/profiles/create', methods=["POST"])
def create_profile():
    """Create a new profile from JSON"""
    data = request.json

    required_fields = ["account_id", "name"]
    for field in required_fields:
        if not data.get(field):
            return jsonify({"msg": f"Missing required field: {field}"}), 400

    profile = Profile(
        account_id=data.get("account_id"),
        name=data.get("name"),
        location=data.get("location"),
        lattitude=data.get("lattitude"),
        longitude=data.get("longitude"),
        class_size=data.get("class_size"),
        availability=data.get("availability"),
        interests=data.get("interests")
    )
    db.session.add(profile)
    db.session.commit()

    return jsonify({
        "msg": "Profile created successfully",
        "id": profile.id
    }), 201


# ChromaDB Document Endpoints

@application.route('/api/documents/upload', methods=['POST'])
def upload_documents():
    """
    Upload documents to ChromaDB for embedding and storage
    Expected JSON format:
    {
        "documents": ["text1", "text2", ...],
        "metadatas": [{"key": "value"}, ...],  // optional
        "ids": ["id1", "id2", ...]  // optional
    }
    """
    try:
        data = request.json
        
        if not data or 'documents' not in data:
            return jsonify({"status": "error", "message": "Missing 'documents' field"}), 400
        
        documents = data.get('documents')
        metadatas = data.get('metadatas', None)
        ids = data.get('ids', None)
        
        if not isinstance(documents, list) or len(documents) == 0:
            return jsonify({"status": "error", "message": "'documents' must be a non-empty list"}), 400
        
        result = chroma_service.add_documents(documents, metadatas, ids)
        
        if result['status'] == 'success':
            return jsonify(result), 201
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@application.route('/api/documents/query', methods=['POST'])
def query_documents():
    """
    Query ChromaDB for similar documents
    Expected JSON format:
    {
        "query": "search text",
        "n_results": 5,  // optional, defaults to 5
        "where": {"key": "value"}  // optional metadata filter
    }
    """
    try:
        data = request.json
        
        if not data or 'query' not in data:
            return jsonify({"status": "error", "message": "Missing 'query' field"}), 400
        
        query_text = data.get('query')
        n_results = data.get('n_results', 5)
        where = data.get('where', None)
        
        if not isinstance(query_text, str) or len(query_text.strip()) == 0:
            return jsonify({"status": "error", "message": "'query' must be a non-empty string"}), 400
        
        result = chroma_service.query_documents(query_text, n_results, where)
        
        if result['status'] == 'success':
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@application.route('/api/documents/delete', methods=['DELETE'])
def delete_documents():
    """
    Delete documents from ChromaDB
    Expected JSON format:
    {
        "ids": ["id1", "id2", ...]
    }
    """
    try:
        data = request.json
        
        if not data or 'ids' not in data:
            return jsonify({"status": "error", "message": "Missing 'ids' field"}), 400
        
        ids = data.get('ids')
        
        if not isinstance(ids, list) or len(ids) == 0:
            return jsonify({"status": "error", "message": "'ids' must be a non-empty list"}), 400
        
        result = chroma_service.delete_documents(ids)
        
        if result['status'] == 'success':
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@application.route('/api/documents/info', methods=['GET'])
def get_collection_info():
    """
    Get information about the ChromaDB collection
    """
    try:
        result = chroma_service.get_collection_info()
        
        if result['status'] == 'success':
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@application.route('/api/documents/update', methods=['PUT'])
def update_document():
    """
    Update an existing document in ChromaDB
    Expected JSON format:
    {
        "id": "document_id",
        "document": "new text",
        "metadata": {"key": "value"}  // optional
    }
    """
    try:
        data = request.json
        
        if not data or 'id' not in data or 'document' not in data:
            return jsonify({"status": "error", "message": "Missing 'id' or 'document' field"}), 400
        
        document_id = data.get('id')
        document = data.get('document')
        metadata = data.get('metadata', None)
        
        if not isinstance(document_id, str) or len(document_id.strip()) == 0:
            return jsonify({"status": "error", "message": "'id' must be a non-empty string"}), 400
        
        if not isinstance(document, str) or len(document.strip()) == 0:
            return jsonify({"status": "error", "message": "'document' must be a non-empty string"}), 400
        
        result = chroma_service.update_document(document_id, document, metadata)
        
        if result['status'] == 'success':
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    application.run(host='0.0.0.0', port=5001)
