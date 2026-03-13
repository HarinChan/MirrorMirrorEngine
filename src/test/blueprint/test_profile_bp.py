import pytest

from src.app.model.profile import Profile
from src.app.model.relation import Relation


@pytest.mark.integration
def test_create_profile_persists_sanitized_fields(client, auth_token, monkeypatch):
    token, _ = auth_token

    monkeypatch.setattr(
        "src.app.blueprint.profile_bp.chroma_service.add_documents",
        lambda documents, metadatas, ids: {"status": "success"},
    )

    response = client.post(
        "/api/profiles",
        json={
            "name": "  Class A  ",
            "location": "  London  ",
            "latitude": "51.5",
            "longitude": "-0.12",
            "class_size": 25,
            "availability": [{"day": "monday", "time": "09:00-10:00"}],
            "interests": [" Coding ", "coding", "Math"],
        },
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert response.status_code == 201, response.get_data(as_text=True)
    payload = response.get_json()
    created_id = payload["classroom"]["id"]

    profile = Profile.query.get(created_id)
    assert profile is not None
    assert profile.name == "Class A"
    assert profile.location == "London"
    assert profile.class_size == 25
    assert profile.interests == ["coding", "math"]


@pytest.mark.integration
@pytest.mark.parametrize(
    "payload, expected_message",
    [
        ({}, "No data provided"),
        ({"location": "London"}, "Profile name is required"),
        ({"name": "x" * 101}, "Profile name too long (max 100 characters)"),
        ({"name": "Class A", "latitude": "-333351.5", "longitude": "snens"}, "Invalid coordinates"),
        ({"name": "Class A", "availability": "invalid"}, "Invalid availability format"),
        ({"name": "Class A", "class_size": 0}, "Class size must be between 1 and 100"),
        ({"name": "Class A", "class_size": "huge"}, "Invalid class size"),
    ],
)
def test_create_profile_invalid_request(client, auth_token, payload, expected_message):
    token, _ = auth_token

    response = client.post(
        "/api/profiles",
        json=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert response.status_code == 400, response.get_data(as_text=True)
    assert response.get_json()["msg"] == expected_message


@pytest.mark.integration
def test_get_profile_by_id(client, auth_token, create_profile):
    token, account = auth_token
    profile = create_profile(account=account, name="FindMeLater")

    found = client.get(
        f"/api/profiles/{profile.id}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    not_found = client.get(
        "/api/profiles/7567484",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    payload = found.get_json()

    assert found.status_code == 200, found.get_data(as_text=True)
    assert payload["profile"]["id"] == profile.id
    assert not_found.status_code == 404, not_found.get_data(as_text=True)


@pytest.mark.integration
def test_update_profile_persists_changes(client, auth_token, create_profile, monkeypatch):
    token, account = auth_token
    profile = create_profile(account=account, name="Old Name", interests=["coding"])

    monkeypatch.setattr("src.app.blueprint.profile_bp.chroma_service.delete_documents", lambda ids: {"status": "success"})
    monkeypatch.setattr(
        "src.app.blueprint.profile_bp.chroma_service.add_documents",
        lambda documents, metadatas, ids: {"status": "success"},
    )

    response = client.put(
        f"/api/profiles/{profile.id}",
        json={
            "name": "New Name",
            "location": "Paris",
            "class_size": 40,
            "interests": ["Science", "science", "Music"],
            "availability": [{"day": "friday", "time": "12:00-13:00"}],
        },
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert response.status_code == 200, response.get_data(as_text=True)

    refreshed = Profile.query.get(profile.id)
    assert refreshed is not None
    assert refreshed.name == "New Name"
    assert refreshed.location == "Paris"
    assert refreshed.class_size == 40
    assert refreshed.interests == ["science", "music"]


@pytest.mark.integration
@pytest.mark.parametrize(
    "payload, expected_message",
    [
        ({}, "No data provided"),
        ({"name": ""}, "Profile name cannot be empty"),
        ({"name": "x" * 101}, "Profile name too long (max 100 characters)"),
        ({"latitude": "NaN", "longitude": "NaN"}, "Invalid coordinates"),
        ({"class_size": 101}, "Class size must be between 1 and 100"),
        ({"class_size": "big"}, "Invalid class size"),
        ({"availability": "bad"}, "Invalid availability format"),
    ],
)
def test_update_profile_validation_errors(client, auth_token, create_profile, payload, expected_message):
    token, account = auth_token
    profile = create_profile(account=account, name="Old Name")

    response = client.put(
        f"/api/profiles/{profile.id}",
        json=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert response.status_code == 400, response.get_data(as_text=True)
    assert response.get_json()["msg"] == expected_message


@pytest.mark.integration
def test_update_profile_unauthorized_or_not_found(client, auth_token, create_account, create_profile, create_jwt_token):
    token, account = auth_token
    profile = create_profile(account=account, name="Owner")

    other_account = create_account("profile-other@example.com", "Other123!")
    other_token = create_jwt_token(str(other_account.id))

    unauthorized = client.put(
        f"/api/profiles/{profile.id}",
        json={"name": "Hacked"},
        headers={"Authorization": f"Bearer {other_token}", "Content-Type": "application/json"},
    )

    missing = client.put(
        "/api/profiles/999999",
        json={"name": "Any"},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert unauthorized.status_code == 403, unauthorized.get_data(as_text=True)
    assert unauthorized.get_json()["msg"] == "Not authorized to update this profile"
    assert missing.status_code == 404, missing.get_data(as_text=True)


@pytest.mark.integration
def test_delete_profile_removes_profile_row(client, auth_token, create_profile, monkeypatch):
    token, account = auth_token
    profile = create_profile(account=account, name="Delete Me")

    monkeypatch.setattr("src.app.blueprint.profile_bp.chroma_service.delete_documents", lambda ids: {"status": "success"})

    response = client.delete(
        f"/api/profiles/{profile.id}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    assert Profile.query.get(profile.id) is None


@pytest.mark.integration
def test_delete_profile_unauthorized_or_not_found(client, auth_token, create_account, create_profile, create_jwt_token):
    token, account = auth_token
    profile = create_profile(account=account, name="Owner")

    other_account = create_account("delete-other@example.com", "Other123!")
    other_token = create_jwt_token(str(other_account.id))

    unauthorized = client.delete(
        f"/api/profiles/{profile.id}",
        headers={"Authorization": f"Bearer {other_token}", "Content-Type": "application/json"},
    )

    missing = client.delete(
        "/api/profiles/999999",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert unauthorized.status_code == 403, unauthorized.get_data(as_text=True)
    assert unauthorized.get_json()["msg"] == "Not authorized to delete this profile"
    assert missing.status_code == 404, missing.get_data(as_text=True)


@pytest.mark.integration
def test_search_profiles_success_and_limit_cap(client, auth_token, create_profile, monkeypatch):
    token, account = auth_token
    p1 = create_profile(account=account, name="Alpha", interests=["coding", "math"])
    p2 = create_profile(account=account, name="Beta", interests=["music"])

    captured = {}

    def fake_query(search_query, n_results):
        captured["search_query"] = search_query
        captured["n_results"] = n_results
        return {
            "status": "success",
            "results": [
                {"metadata": {"profile_id": p1.id}, "similarity": 0.9123},
                {"metadata": {"profile_id": p2.id}, "similarity": 0.4},
            ],
        }

    monkeypatch.setattr("src.app.blueprint.profile_bp.chroma_service.query_documents", fake_query)

    response = client.post(
        "/api/profiles/search",
        json={"interests": [" Coding ", "math"], "n_results": 500},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    body = response.get_json()
    assert body["search_query"] == "coding math"
    assert body["total_results"] == 2
    assert captured["n_results"] == 50
    assert body["matched_profiles"][0]["id"] == p1.id
    assert "manual_similarity" in body["matched_profiles"][0]


@pytest.mark.integration
@pytest.mark.parametrize(
    "payload, expected_message",
    [
        ({}, "No data provided"),
        ({"foo": "bar"}, "Interests are required for search"),
        ({"interests": ["   "]}, "No valid interests provided"),
    ],
)
def test_search_profiles_validation_errors(client, auth_token, payload, expected_message):
    token, _ = auth_token

    response = client.post(
        "/api/profiles/search",
        json=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert response.status_code == 400, response.get_data(as_text=True)
    assert response.get_json()["msg"] == expected_message


@pytest.mark.integration
def test_search_profiles_chroma_failure_returns_500(client, auth_token, monkeypatch):
    token, _ = auth_token

    monkeypatch.setattr(
        "src.app.blueprint.profile_bp.chroma_service.query_documents",
        lambda query, n_results: {"status": "error", "message": "db down"},
    )

    response = client.post(
        "/api/profiles/search",
        json={"interests": ["coding"]},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert response.status_code == 500, response.get_data(as_text=True)
    assert response.get_json()["msg"] == "Search failed"


@pytest.mark.integration
def test_connect_and_disconnect_profiles_persist_relations(client, auth_token, create_account, create_profile):
    token, account = auth_token
    from_profile = create_profile(account=account, name="From")

    other_account = create_account("target@example.com", "TargetPass123!")
    to_profile = create_profile(account=other_account, name="To")

    connect_response = client.post(
        f"/api/profiles/{to_profile.id}/connect",
        json={"from_profile_id": from_profile.id},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert connect_response.status_code == 201, connect_response.get_data(as_text=True)

    relation_forward = Relation.query.filter_by(from_profile_id=from_profile.id, to_profile_id=to_profile.id).first()
    relation_reverse = Relation.query.filter_by(from_profile_id=to_profile.id, to_profile_id=from_profile.id).first()
    assert relation_forward is not None
    assert relation_reverse is not None

    disconnect_response = client.delete(
        f"/api/profiles/{to_profile.id}/disconnect",
        json={"from_profile_id": from_profile.id},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert disconnect_response.status_code == 200, disconnect_response.get_data(as_text=True)
    assert Relation.query.filter_by(from_profile_id=from_profile.id, to_profile_id=to_profile.id).first() is None
    assert Relation.query.filter_by(from_profile_id=to_profile.id, to_profile_id=from_profile.id).first() is None


@pytest.mark.integration
@pytest.mark.parametrize(
    "path, method, payload, expected_status, expected_msg",
    [
        ("/api/profiles/{id}/connect", "POST", {}, 400, "No data provided"),
        ("/api/profiles/{id}/connect", "POST", {"foo": "bar"}, 400, "from_profile_id is required"),
        ("/api/profiles/{id}/disconnect", "DELETE", {}, 400, "No data provided"),
        ("/api/profiles/{id}/disconnect", "DELETE", {"foo": "bar"}, 400, "from_profile_id is required"),
    ],
)
def test_connect_disconnect_missing_payload_fields(
    client, auth_token, create_account, create_profile, path, method, payload, expected_status, expected_msg
):
    token, account = auth_token
    create_profile(account=account, name="From")
    other_account = create_account("target2@example.com", "TargetPass123!")
    to_profile = create_profile(account=other_account, name="To")

    endpoint = path.format(id=to_profile.id)
    response = client.open(
        endpoint,
        method=method,
        json=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert response.status_code == expected_status, response.get_data(as_text=True)
    assert response.get_json()["msg"] == expected_msg


@pytest.mark.integration
def test_connect_profiles_rejects_unauthorized_target_self_and_duplicate(client, auth_token, create_account, create_profile, create_jwt_token):
    token, account = auth_token
    from_profile = create_profile(account=account, name="From")

    other_account = create_account("target3@example.com", "TargetPass123!")
    to_profile = create_profile(account=other_account, name="To")
    other_token = create_jwt_token(str(other_account.id))

    unauthorized = client.post(
        f"/api/profiles/{to_profile.id}/connect",
        json={"from_profile_id": from_profile.id},
        headers={"Authorization": f"Bearer {other_token}", "Content-Type": "application/json"},
    )
    assert unauthorized.status_code == 403

    self_connect = client.post(
        f"/api/profiles/{from_profile.id}/connect",
        json={"from_profile_id": from_profile.id},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    assert self_connect.status_code == 400

    first_connect = client.post(
        f"/api/profiles/{to_profile.id}/connect",
        json={"from_profile_id": from_profile.id},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    assert first_connect.status_code == 201

    duplicate = client.post(
        f"/api/profiles/{to_profile.id}/connect",
        json={"from_profile_id": from_profile.id},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    assert duplicate.status_code == 409


@pytest.mark.integration
def test_get_profile_friends_sorted_and_not_found(client, auth_token, create_account, create_profile, create_relation):
    token, account = auth_token
    profile = create_profile(account=account, name="Main", interests=["coding", "math"])

    friend_account_1 = create_account("friend-1@example.com", "Friend123!")
    friend_1 = create_profile(account=friend_account_1, name="Friend 1", interests=["coding", "math"])

    friend_account_2 = create_account("friend-2@example.com", "Friend123!")
    friend_2 = create_profile(account=friend_account_2, name="Friend 2", interests=["history"])

    create_relation(profile, friend_2)
    create_relation(profile, friend_1)

    response = client.get(
        f"/api/profiles/{profile.id}/friends",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    friends = response.get_json()["friends"]
    assert friends[0]["id"] == friend_1.id

    missing = client.get(
        "/api/profiles/999999/friends",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    assert missing.status_code == 404


@pytest.mark.integration
def test_disconnect_no_friendship_and_unauthorized(client, auth_token, create_account, create_profile, create_jwt_token):
    token, account = auth_token
    from_profile = create_profile(account=account, name="From")
    other_account = create_account("target4@example.com", "TargetPass123!")
    to_profile = create_profile(account=other_account, name="To")

    no_friendship = client.delete(
        f"/api/profiles/{to_profile.id}/disconnect",
        json={"from_profile_id": from_profile.id},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    assert no_friendship.status_code == 404

    other_token = create_jwt_token(str(other_account.id))
    unauthorized = client.delete(
        f"/api/profiles/{to_profile.id}/disconnect",
        json={"from_profile_id": from_profile.id},
        headers={"Authorization": f"Bearer {other_token}", "Content-Type": "application/json"},
    )
    assert unauthorized.status_code == 403


@pytest.mark.integration
def test_get_all_classrooms_limit_and_order(client, auth_token, create_profile):
    token, account = auth_token
    create_profile(account=account, name="First")
    latest = create_profile(account=account, name="Latest")

    limited = client.get(
        "/api/profiles?limit=1",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert limited.status_code == 200, limited.get_data(as_text=True)
    body = limited.get_json()
    assert body["count"] == 1
    assert body["classrooms"][0]["id"] == latest.id