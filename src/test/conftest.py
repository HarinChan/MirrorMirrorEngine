"""
Pytest configuration and fixtures for test suite.
Provides test app, client, database, and authentication fixtures.
"""

import pytest
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from flask_jwt_extended import create_access_token

from src.app.model import db as _db
from src.app.model.account import Account
from src.app.model.profile import Profile
from src.app.model.post import Post
from src.app.model.relation import Relation
from src.app.model.meeting import Meeting
from src.app.model.notification import Notification


@pytest.fixture(scope='function')
def app():
    """
    Create and configure a test Flask application with in-memory database.
    Each test gets a fresh app instance.
    """
    from flask import Flask
    from flask_jwt_extended import JWTManager
    from flask_cors import CORS
    from datetime import timedelta
    
    # Create test app
    test_app = Flask(__name__)
    test_app.config['TESTING'] = True
    test_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    test_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    test_app.config['SECRET_KEY'] = 'test-secret-key'
    test_app.config['JWT_SECRET_KEY'] = 'test-jwt-secret-key'
    test_app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
    
    # Initialize extensions
    _db.init_app(test_app)
    jwt = JWTManager(test_app)
    CORS(test_app)
    
    # Import and register blueprints
    from src.app.blueprint.account_bp import account_bp
    from src.app.blueprint.chroma_bp import chroma_bp
    from src.app.blueprint.friends_bp import friends_bp
    from src.app.blueprint.meeting_bp import meeting_bp
    from src.app.blueprint.notification_bp import notification_bp
    from src.app.blueprint.posts_bp import post_bp
    from src.app.blueprint.profile_bp import profile_bp
    from src.app.blueprint.webex_bp import webex_bp
    
    test_app.register_blueprint(account_bp)
    test_app.register_blueprint(chroma_bp)
    test_app.register_blueprint(friends_bp)
    test_app.register_blueprint(meeting_bp)
    test_app.register_blueprint(notification_bp)
    test_app.register_blueprint(post_bp)
    test_app.register_blueprint(profile_bp)
    test_app.register_blueprint(webex_bp)
    
    # Register auth routes manually
    from werkzeug.security import generate_password_hash, check_password_hash
    from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
    from flask import jsonify, request
    from src.app.model.account import Account
    from src.app.model.profile import Profile
    from src.app.model.notification import Notification
    
    capital_letters = [chr(i) for i in range(ord('A'), ord('Z')+1)]
    lowercase_letters = [chr(i) for i in range(ord('a'), ord('z')+1)]
    digits = [str(i) for i in range(10)]
    
    @test_app.route('/api/auth/register', methods=['POST'])
    def register():
        """Register endpoint for tests."""
        data = request.json
        if not data:
            return jsonify({"msg": "Invalid request format"}), 400
        
        email = data.get('email')
        password = data.get('password')
        organization = data.get('organization')
        
        if not email or not password:
            return jsonify({"msg": "Missing required fields"}), 400
        
        has_upper = any(c in capital_letters for c in password)
        has_lower = any(c in lowercase_letters for c in password)
        has_digit = any(c in digits for c in password)
        has_special = any(c not in capital_letters and c not in lowercase_letters and c not in digits for c in password)
        
        if not (len(password) >= 8 and has_upper and has_lower and has_digit and has_special):
            return jsonify({
                "msg": "Password must be at least 8 characters and include one uppercase, one lowercase, one digit, and one special character."
            }), 400
        
        if Account.query.filter_by(email=email).first():
            return jsonify({"msg": "Account already exists"}), 409
        
        password_hash = generate_password_hash(password)
        account = Account()
        account.email = email
        account.password_hash = password_hash
        account.organization = organization
        _db.session.add(account)
        _db.session.commit()
        
        return jsonify({"msg": "Account created successfully", "account_id": account.id}), 201
    
    @test_app.route('/api/auth/login', methods=['POST'])
    def login():
        """Login endpoint for tests."""
        data = request.json
        if not data:
            return jsonify({"msg": "Invalid request format"}), 400
        
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({"msg": "Missing email or password"}), 400
        
        account = Account.query.filter_by(email=email).first()
        
        if not account or not check_password_hash(account.password_hash, password):
            return jsonify({"msg": "Invalid credentials"}), 401
        
        access_token = create_access_token(identity=account.id)
        return jsonify({"access_token": access_token}), 200
    
    @test_app.route('/api/auth/me', methods=['GET'])
    @jwt_required()
    def get_me():
        """Get current user endpoint for tests."""
        account_id = get_jwt_identity()
        account = _db.session.get(Account, account_id)
        
        if not account:
            return jsonify({"msg": "Account not found"}), 404
        
        profiles = Profile.query.filter_by(account_id=account.id).all()
        notifications = Notification.query.filter_by(account_id=account.id, read=False).all()
        
        return jsonify({
            "email": account.email,
            "account_id": account.id,
            "organization": account.organization,
            "profiles": [{"id": p.id, "name": p.name} for p in profiles],
            "notifications": [{"id": n.id, "title": n.title, "message": n.message} for n in notifications]
        }), 200
    
    # Create application context
    with test_app.app_context():
        _db.create_all()
        yield test_app
        _db.session.remove()
        _db.drop_all()
        _db.engine.dispose()


@pytest.fixture(scope='function')
def client(app):
    """
    Provides a test client for making API requests.
    """
    return app.test_client()


@pytest.fixture(scope='function')
def db(app):
    """
    Provides database session with automatic rollback after test.
    """
    with app.app_context():
        yield _db
        try:
            _db.session.rollback()
        finally:
            _db.session.close()
            _db.engine.dispose()


@pytest.fixture
def create_account(db):
    """
    Factory fixture to create test accounts.
    Usage: account = create_account(email='test@example.com', password='Password123!')
    """
    def _create_account(email='test@example.com', password='Password123!', organization=None):
        account = Account()
        account.email = email
        account.password_hash = generate_password_hash(password)
        account.organization = organization

        db.session.add(account)
        db.session.commit()
        return account
    
    return _create_account


@pytest.fixture
def create_profile(db):
    """
    Factory fixture to create test profiles.
    Usage: profile = create_profile(account=account, name='Test Class')
    """
    def _create_profile(account, name='Test Classroom', location='London', 
                       lattitude=51.5074, longitude=-0.1278, 
                       class_size=30, interests=None, availability=None):
        if interests is None:
            interests = ['coding', 'math']
        if availability is None:
            availability = {'monday': '9-5', 'tuesday': '9-5'}
        
        profile = Profile()
        profile.account_id = account.id
        profile.name = name
        profile.location = location
        profile.lattitude = lattitude
        profile.longitude = longitude
        profile.class_size = class_size
        profile.interests = interests
        profile.availability = availability

        db.session.add(profile)
        db.session.commit()
        return profile
    
    return _create_profile


@pytest.fixture
def create_post(db):
    """
    Factory fixture to create test posts.
    Usage: post = create_post(profile=profile, content='Test content')
    """
    def _create_post(profile, content='Test post content', image_url=None, quoted_post_id=None):
        post = Post()
        post.profile_id = profile.id
        post.content = content
        post.image_url = image_url
        post.quoted_post_id = quoted_post_id
        post.likes = 0
        post.comments_count = 0

        db.session.add(post)
        db.session.commit()
        return post
    
    return _create_post


@pytest.fixture
def create_relation(db):
    """
    Factory fixture to create test relations (friendships).
    Usage: relation = create_relation(from_profile=profile1, to_profile=profile2)
    """
    def _create_relation(from_profile, to_profile, status='accepted'):
        relation = Relation()
        relation.from_profile_id = from_profile.id
        relation.to_profile_id = to_profile.id
        relation.status = status

        db.session.add(relation)
        db.session.commit()
        return relation
    
    return _create_relation


@pytest.fixture
def create_notification(db):
    """
    Factory fixture to create test notifications.
    """
    def _create_notification(account, title='Test Notification', message='Test message', 
                           notification_type='info', read=False, related_id=None):
        notification = Notification()
        notification.account_id = account.id
        notification.title = title
        notification.message = message
        notification.type = notification_type
        notification.read = read
        notification.related_id = related_id

        db.session.add(notification)
        db.session.commit()
        return notification
    
    return _create_notification


@pytest.fixture
def auth_token(app, create_account):
    """
    Creates a test account and returns a valid JWT token.
    Usage: token = auth_token
    """
    account = create_account(email='auth@example.com', password='Password123!')
    
    with app.app_context():
        token = create_access_token(identity=account.id)
    
    return token, account


@pytest.fixture
def auth_headers(auth_token):
    """
    Returns authorization headers with valid JWT token.
    Usage: response = client.get('/api/account', headers=auth_headers)
    """
    token, account = auth_token
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }


@pytest.fixture
def create_jwt_token(app):
    """
    Factory to create JWT tokens for specific account IDs.
    Usage: token = create_jwt_token(account.id)
    """
    def _create_token(account_id, expires_delta=None):
        with app.app_context():
            if expires_delta:
                token = create_access_token(identity=account_id, expires_delta=expires_delta)
            else:
                token = create_access_token(identity=account_id)
            return token
    
    return _create_token


@pytest.fixture
def mock_chromadb_service(monkeypatch):
    """
    Mocks ChromaDB service to avoid external dependencies.
    """
    class MockChromaDBService:
        def __init__(self, collection_name, persist_directory):
            self.collection_name = collection_name
            self.persist_directory = persist_directory
            self.documents = {}
        
        def add_documents(self, documents, metadatas, ids):
            for i, doc_id in enumerate(ids):
                self.documents[doc_id] = {
                    'document': documents[i],
                    'metadata': metadatas[i] if metadatas else None
                }
            return True
        
        def query_documents(self, query_text, n_results=5):
            # Return mock results
            return {
                'ids': [['doc1', 'doc2']],
                'distances': [[0.1, 0.2]],
                'documents': [['Sample document 1', 'Sample document 2']],
                'metadatas': [[{'source': 'test1'}, {'source': 'test2'}]]
            }
        
        def delete_documents(self, ids):
            for doc_id in ids:
                if doc_id in self.documents:
                    del self.documents[doc_id]
            return True
        
        def get_collection_info(self):
            return {
                'name': self.collection_name,
                'count': len(self.documents)
            }
        
        def update_document(self, document_id, document, metadata=None):
            if document_id in self.documents:
                self.documents[document_id] = {
                    'document': document,
                    'metadata': metadata
                }
                return True
            return False
    
    return MockChromaDBService


@pytest.fixture
def mock_webex_service(monkeypatch):
    """
    Mocks WebEx service to avoid external API calls.
    """
    class MockWebExService:
        def __init__(self, client_id, client_secret, redirect_uri):
            self.client_id = client_id
            self.client_secret = client_secret
            self.redirect_uri = redirect_uri
        
        def get_auth_url(self):
            return f"https://webexapis.com/v1/authorize?client_id={self.client_id}&response_type=code&redirect_uri={self.redirect_uri}&scope=meeting:schedules_read meeting:schedules_write"
        
        def exchange_code(self, code):
            if code == 'invalid_code':
                return None
            return {
                'access_token': 'mock_access_token',
                'refresh_token': 'mock_refresh_token',
                'expires_in': 3600
            }
        
        def refresh_access_token(self, refresh_token):
            if refresh_token == 'invalid_refresh':
                return None
            return {
                'access_token': 'new_mock_access_token',
                'refresh_token': 'new_mock_refresh_token',
                'expires_in': 3600
            }
        
        def create_meeting(self, access_token, title, start_time, end_time):
            if access_token == 'invalid_token':
                return None
            return {
                'id': 'mock_webex_meeting_id',
                'title': title,
                'start': start_time,
                'end': end_time,
                'webLink': 'https://meet.webex.com/mock-meeting',
                'password': 'mock123'
            }
        
        def update_meeting(self, access_token, meeting_id, title=None, start_time=None, end_time=None):
            if access_token == 'invalid_token' or meeting_id == 'invalid_meeting':
                return None
            return {
                'id': meeting_id,
                'title': title or 'Updated Meeting',
                'start': start_time,
                'end': end_time
            }
        
        def delete_meeting(self, access_token, meeting_id):
            if access_token == 'invalid_token' or meeting_id == 'invalid_meeting':
                return False
            return True
    
    return MockWebExService


# Helper function available to all tests
def get_jwt_headers(token):
    """
    Helper to create authorization headers from a token string.
    """
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
