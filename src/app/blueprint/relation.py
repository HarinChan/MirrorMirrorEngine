from flask import request, jsonify
from src.app.__init__ import db, app
from src.app.model.relation import Relation

# Create a relation
@app.route('/relations', methods=['POST'])
def add_relation():
    data = request.get_json()
    
    # Check if the relation already exists
    existing_relation = Relation.query.filter_by(
        from_profile_id=data['from_profile_id'],
        to_profile_id=data['to_profile_id']
    ).first()

    if existing_relation:
        return jsonify({"message": "Relation already exists"}), 400
    
    new_relation = Relation(
        from_profile_id=data['from_profile_id'],
        to_profile_id=data['to_profile_id'],
        status=data.get('status', 'pending')
    )
    
    db.session.add(new_relation)
    db.session.commit()
    
    return jsonify({"message": "Relation created", "id": new_relation.id}), 201

# Read a relation by ID
@app.route('/relations/<int:id>', methods=['GET'])
def get_relation(id):
    relation = Relation.query.get_or_404(id)
    return jsonify({
        "id": relation.id,
        "from_profile_id": relation.from_profile_id,
        "to_profile_id": relation.to_profile_id,
        "status": relation.status,
        "created_at": relation.created_at.isoformat()
    }), 200

# Update a relation
@app.route('/relations/<int:id>', methods=['PUT'])
def update_relation(id):
    relation = Relation.query.get_or_404(id)
    data = request.get_json()

    relation.status = data.get('status', relation.status)
    db.session.commit()
    
    return jsonify({"message": "Relation updated"}), 200

# Delete a relation
@app.route('/relations/<int:id>', methods=['DELETE'])
def delete_relation(id):
    relation = Relation.query.get_or_404(id)
    db.session.delete(relation)
    db.session.commit()
    return jsonify({"message": "Relation deleted"}), 200

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)