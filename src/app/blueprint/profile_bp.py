"""
Profile management and matching system.
Handles profile CRUD operations, semantic interest matching via ChromaDB,
and automatic bidirectional connections between profiles.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..model import db
from ..model.account import Account
from ..helper import PenpalsHelper
from ..chromadb.chromadb_service import ChromaDBService


profile_bp = Blueprint('profile', __name__)

chroma_service = ChromaDBService(persist_directory="./chroma_db", collection_name="profile_interests")


@profile_bp.route('/api/profiles', methods=['POST'])
@jwt_required()
def create_profile():
    """Create a new profile for the current account"""
    try:
        account_id = get_jwt_identity()
        account = Account.query.get(account_id)
        
        if not account:
            return jsonify({"msg": "Account not found"}), 404
        
        data = request.json
        if not data:
            return jsonify({"msg": "No data provided"}), 400
        
        # Validate required fields
        name = data.get('name', '').strip()
        if not name:
            return jsonify({"msg": "Profile name is required"}), 400
        
        if len(name) > 100:
            return jsonify({"msg": "Profile name too long (max 100 characters)"}), 400
        
        # Validate coordinates if provided
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        if not PenpalsHelper.validate_coordinates(latitude, longitude):
            return jsonify({"msg": "Invalid coordinates"}), 400
        
        # Validate and sanitize interests
        raw_interests = data.get('interests', [])
        interests = PenpalsHelper.sanitize_interests(raw_interests)
        
        # Validate availability format
        availability = data.get('availability')
        if not PenpalsHelper.validate_availability_format(availability):
            return jsonify({"msg": "Invalid availability format"}), 400
        
        # Validate class size
        class_size = data.get('class_size')
        if class_size is not None:
            try:
                class_size = int(class_size)
                if class_size < 1 or class_size > 100:
                    return jsonify({"msg": "Class size must be between 1 and 100"}), 400
            except (ValueError, TypeError):
                return jsonify({"msg": "Invalid class size"}), 400
        
        profile = Profile(
            account_id=account.id,
            name=name,
            location=data.get('location', '').strip() or None,
            lattitude=latitude,  # keeping original typo for consistency
            longitude=longitude,
            class_size=class_size,
            availability=availability,
            interests=interests
        )
        
        db.session.add(profile)
        db.session.flush()
        
        # Store interests in ChromaDB for semantic matching
        if interests:
            interests_text = " ".join(interests)
            chroma_result = chroma_service.add_documents(
                documents=[interests_text],
                metadatas=[{
                    "profile_id": profile.id,
                    "profile_name": profile.name,
                    "location": profile.location or ""
                }],
                ids=[f"profile_{profile.id}"]
            )
            
            if chroma_result['status'] != 'success':
                print(f"ChromaDB add warning: {chroma_result.get('message')}")
        
        db.session.commit()
        
        profile_data = PenpalsHelper.format_profile_response(profile)
        
        return jsonify({
            "msg": "Profile created successfully",
            "profile": profile_data
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Internal server error", "error": str(e)}), 500


@profile_bp.route('/api/profiles/<int:profile_id>', methods=['GET'])
@jwt_required()
def get_profile(profile_id):
    """Get profile details with friends"""
    try:
        profile = Profile.query.get(profile_id)
        
        if not profile:
            return jsonify({"msg": "Profile not found"}), 404
        
        profile_data = PenpalsHelper.format_profile_response(profile, include_friends=True)
        
        return jsonify({"profile": profile_data}), 200
    
    except Exception as e:
        return jsonify({"msg": "Internal server error", "error": str(e)}), 500


@profile_bp.route('/api/profiles/<int:profile_id>', methods=['PUT'])
@jwt_required()
def update_profile(profile_id):
    """Update profile information (only owner can update)"""
    try:
        account_id = get_jwt_identity()
        profile = Profile.query.get(profile_id)
        
        if not profile:
            return jsonify({"msg": "Profile not found"}), 404
        
        if profile.account_id != int(account_id):
            return jsonify({"msg": "Not authorized to update this profile"}), 403
        
        data = request.json
        if not data:
            return jsonify({"msg": "No data provided"}), 400
        
        old_interests = profile.interests or []
        
        # Validate and update fields
        if 'name' in data:
            name = data['name'].strip()
            if not name:
                return jsonify({"msg": "Profile name cannot be empty"}), 400
            if len(name) > 100:
                return jsonify({"msg": "Profile name too long (max 100 characters)"}), 400
            profile.name = name
        
        if 'location' in data:
            location = data['location']
            profile.location = location.strip() if location else None
        
        if 'latitude' in data or 'longitude' in data:
            new_lat = data.get('latitude', profile.lattitude)
            new_lng = data.get('longitude', profile.longitude)
            if not PenpalsHelper.validate_coordinates(new_lat, new_lng):
                return jsonify({"msg": "Invalid coordinates"}), 400
            profile.lattitude = new_lat
            profile.longitude = new_lng
        
        if 'class_size' in data:
            class_size = data['class_size']
            if class_size is not None:
                try:
                    class_size = int(class_size)
                    if class_size < 1 or class_size > 100:
                        return jsonify({"msg": "Class size must be between 1 and 100"}), 400
                except (ValueError, TypeError):
                    return jsonify({"msg": "Invalid class size"}), 400
            profile.class_size = class_size
        
        if 'availability' in data:
            availability = data['availability']
            if not PenpalsHelper.validate_availability_format(availability):
                return jsonify({"msg": "Invalid availability format"}), 400
            profile.availability = availability
        
        if 'interests' in data:
            raw_interests = data['interests']
            interests = PenpalsHelper.sanitize_interests(raw_interests)
            profile.interests = interests
        
        # Update ChromaDB if interests changed
        new_interests = profile.interests or []
        if old_interests != new_interests:
            try:
                # Delete old entry
                chroma_service.delete_documents([f"profile_{profile.id}"])
                
                # Add new entry if interests exist
                if new_interests:
                    interests_text = " ".join(new_interests)
                    chroma_service.add_documents(
                        documents=[interests_text],
                        metadatas=[{
                            "profile_id": profile.id,
                            "profile_name": profile.name,
                            "location": profile.location or ""
                        }],
                        ids=[f"profile_{profile.id}"]
                    )
            except Exception as e:
                print(f"ChromaDB update error: {e}")
        
        db.session.commit()
        
        profile_data = PenpalsHelper.format_profile_response(profile)
        
        return jsonify({
            "msg": "Profile updated successfully",
            "profile": profile_data
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Internal server error", "error": str(e)}), 500


@profile_bp.route('/api/profiles/<int:profile_id>', methods=['DELETE'])
@jwt_required()
def delete_profile(profile_id):
    """Delete profile (only owner can delete)"""
    try:
        account_id = get_jwt_identity()
        profile = Profile.query.get(profile_id)
        
        if not profile:
            return jsonify({"msg": "Profile not found"}), 404
        
        if profile.account_id != int(account_id):
            return jsonify({"msg": "Not authorized to delete this profile"}), 403
        
        # Get connection count for confirmation
        connections_count = profile.sent_relations.count()
        
        # Remove from ChromaDB
        try:
            chroma_service.delete_documents([f"profile_{profile.id}"])
        except Exception as e:
            print(f"ChromaDB delete error: {e}")
        
        db.session.delete(profile)
        db.session.commit()
        
        return jsonify({
            "msg": "Profile deleted successfully",
            "deleted_connections": connections_count
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Internal server error", "error": str(e)}), 500


@profile_bp.route('/api/profiles/search', methods=['POST'])
@jwt_required()
def search_profiles():
    """Search for profiles by interests using semantic search"""
    try:
        data = request.json
        if not data:
            return jsonify({"msg": "No data provided"}), 400
        
        if not data.get('interests'):
            return jsonify({"msg": "Interests are required for search"}), 400
        
        interests = data.get('interests')
        n_results = min(data.get('n_results', 10), 50)  # Limit max results
        
        # Sanitize search interests
        if isinstance(interests, list):
            search_interests = PenpalsHelper.sanitize_interests(interests)
            search_query = " ".join(search_interests)
        else:
            search_query = str(interests).strip()
        
        if not search_query:
            return jsonify({"msg": "No valid interests provided"}), 400
        
        # Search using ChromaDB
        result = chroma_service.query_documents(search_query, n_results)
        
        if result['status'] != 'success':
            return jsonify({"msg": "Search failed", "error": result.get('message')}), 500
        
        # Get profile details from database
        matched_profiles = []
        if result.get('results'):
            for search_result in result['results']:
                metadata = search_result['metadata']
                profile_id = metadata['profile_id']
                profile = Profile.query.get(profile_id)
                
                if profile:
                    profile_data = PenpalsHelper.format_profile_response(profile)
                    profile_data["similarity_score"] = round(search_result['similarity'], 3)
                    
                    # Add manual similarity calculation as well
                    manual_similarity = PenpalsHelper.calculate_interest_similarity(
                        search_interests if isinstance(interests, list) else [search_query],
                        profile.interests or []
                    )
                    profile_data["manual_similarity"] = round(manual_similarity, 3)
                    
                    matched_profiles.append(profile_data)
        
        return jsonify({
            "matched_profiles": matched_profiles,
            "search_query": search_query,
            "total_results": len(matched_profiles)
        }), 200
        
    except Exception as e:
        return jsonify({"msg": "Search error", "error": str(e)}), 500


@profile_bp.route('/api/profiles/<int:profile_id>/connect', methods=['POST'])
@jwt_required()
def connect_profiles(profile_id):
    """Add a profile as a friend (automatic bidirectional connection)"""
    try:
        account_id = get_jwt_identity()
        data = request.json
        
        if not data:
            return jsonify({"msg": "No data provided"}), 400
        
        from_profile_id = data.get('from_profile_id')
        
        if not from_profile_id:
            return jsonify({"msg": "from_profile_id is required"}), 400
        
        # Validate from_profile ownership
        from_profile = Profile.query.get(from_profile_id)
        if not from_profile or from_profile.account_id != int(account_id):
            return jsonify({"msg": "Not authorized to connect from this profile"}), 403
        
        # Validate target profile exists
        to_profile = Profile.query.get(profile_id)
        if not to_profile:
            return jsonify({"msg": "Target profile not found"}), 404
        
        # Prevent self-connection
        if from_profile_id == profile_id:
            return jsonify({"msg": "Cannot connect profile to itself"}), 400
        
        # Check if friendship already exists
        existing_relation = Relation.query.filter_by(
            from_profile_id=from_profile_id,
            to_profile_id=profile_id
        ).first()
        
        if existing_relation:
            return jsonify({"msg": "Profiles are already friends"}), 409
        
        # Create bidirectional friendship
        relation1 = Relation(from_profile_id=from_profile_id, to_profile_id=profile_id)
        relation2 = Relation(from_profile_id=profile_id, to_profile_id=from_profile_id)
        
        db.session.add(relation1)
        db.session.add(relation2)
        db.session.commit()
        
        return jsonify({
            "msg": "Profiles are now friends!",
            "connection": {
                "from_profile": from_profile.name,
                "to_profile": to_profile.name,
                "connected_at": PenpalsHelper.get_current_utc_timestamp().isoformat()
            }
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Internal server error", "error": str(e)}), 500


@profile_bp.route('/api/profiles/<int:profile_id>/friends', methods=['GET'])
@jwt_required()
def get_profile_friends(profile_id):
    """Get all friends for a profile"""
    try:
        profile = Profile.query.get(profile_id)
        
        if not profile:
            return jsonify({"msg": "Profile not found"}), 404
        
        friends = []
        for relation in profile.sent_relations:
            friend = relation.to_profile
            friend_data = {
                "id": friend.id,
                "name": friend.name,
                "location": friend.location,
                "class_size": friend.class_size,
                "interests": friend.interests,
                "friends_since": relation.created_at.isoformat()
            }
            
            # Calculate interest similarity
            similarity = PenpalsHelper.calculate_interest_similarity(
                profile.interests or [],
                friend.interests or []
            )
            friend_data["interest_similarity"] = round(similarity, 3)
            
            friends.append(friend_data)
        
        # Sort friends by similarity score (descending)
        friends.sort(key=lambda x: x["interest_similarity"], reverse=True)
        
        return jsonify({
            "profile_id": profile_id,
            "profile_name": profile.name,
            "friends": friends,
            "friends_count": len(friends)
        }), 200
    
    except Exception as e:
        return jsonify({"msg": "Internal server error", "error": str(e)}), 500


@profile_bp.route('/api/profiles/<int:profile_id>/disconnect', methods=['DELETE'])
@jwt_required()
def disconnect_profiles(profile_id):
    """Remove friendship between profiles"""
    try:
        account_id = get_jwt_identity()
        data = request.json
        
        if not data:
            return jsonify({"msg": "No data provided"}), 400
        
        from_profile_id = data.get('from_profile_id')
        
        if not from_profile_id:
            return jsonify({"msg": "from_profile_id is required"}), 400
        
        # Validate from_profile ownership
        from_profile = Profile.query.get(from_profile_id)
        if not from_profile or from_profile.account_id != int(account_id):
            return jsonify({"msg": "Not authorized to disconnect from this profile"}), 403
        
        # Find and delete both directions of the relationship
        relation1 = Relation.query.filter_by(
            from_profile_id=from_profile_id,
            to_profile_id=profile_id
        ).first()
        
        relation2 = Relation.query.filter_by(
            from_profile_id=profile_id,
            to_profile_id=from_profile_id
        ).first()
        
        if not relation1 and not relation2:
            return jsonify({"msg": "No friendship exists between these profiles"}), 404
        
        if relation1:
            db.session.delete(relation1)
        if relation2:
            db.session.delete(relation2)
        
        db.session.commit()
        
        return jsonify({"msg": "Profiles disconnected successfully"}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Internal server error", "error": str(e)}), 500
