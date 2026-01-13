from flask import request, jsonify
from src.app.main import db, app
from src.app.model.profile import Profile
from src.app.model.account import Account
from src.app.model.post import Post
from src.app.model.relation import Relation
from werkzeug.security import generate_password_hash, check_password_hash

# Create an account
@app.route('/accounts', methods=['POST'])
def add_account():
    data = request.get_json()
    
    if Account.query.filter_by(email=data['email']).first():
        return jsonify({"message": "Email already exists"}), 400
    
    new_account = Account(
        email=data['email'],
        password_hash=generate_password_hash(data['password']),
        metadata=data.get('metadata')
    )
    
    db.session.add(new_account)
    db.session.commit()
    
    return jsonify({"message": "Account created", "id": new_account.id}), 201

# Read an account by ID
@app.route('/accounts/<int:id>', methods=['GET'])
def get_account(id):
    account = Account.query.get_or_404(id)
    return jsonify({
        "id": account.id,
        "email": account.email,
        "created_at": account.created_at.isoformat(),
        "metadata": account.metadata,
    }), 200

# Edit an account
@app.route('/accounts/<int:id>', methods=['PUT'])
def edit_account(id):
    account = Account.query.get_or_404(id)
    data = request.get_json()

    if 'email' in data:
        if Account.query.filter_by(email=data['email']).first():
            return jsonify({"message": "Email already exists"}), 400
        account.email = data['email']
    
    if 'password' in data:
        account.password_hash = generate_password_hash(data['password'])
    
    account.metadata = data.get('metadata', account.metadata)

    db.session.commit()
    return jsonify({"message": "Account updated"}), 200

# Delete an account
@app.route('/accounts/<int:id>', methods=['DELETE'])
def delete_account(id):
    account = Account.query.get_or_404(id)
    db.session.delete(account)
    db.session.commit()
    return jsonify({"message": "Account deleted"}), 200