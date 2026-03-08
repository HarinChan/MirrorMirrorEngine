import pytest

from src.app.model.profile import Profile
from src.app.model.relation import Relation


@pytest.mark.integration
def test_create_profile_persists_sanitized_fields(client, auth_token):
    token, _ = auth_token

    response = client.post("/api/profiles",
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
    created_id = payload["profile"]["id"]

    profile = Profile.query.get(created_id)
    assert profile is not None
    assert profile.name == "Class A"
    assert profile.location == "London"
    assert profile.class_size == 25
    assert profile.interests == ["coding", "math"]

@pytest.mark.integration
def test_create_profile_invalid_request(client, auth_token):
    token, _ = auth_token

    no_data = client.post("/api/profiles",
        json={},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    )

    missing_name = client.post("/api/profiles",
        json={
            "location": "  London  ",
            "latitude": "51.5",
            "longitude": "-0.12",
            "class_size": 25,
            "availability": [{"day": "monday", "time": "09:00-10:00"}],
            "interests": [" Coding ", "coding", "Math"],
        },
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    long_name = client.post("/api/profiles",
        json={
            "name": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Curabitur ut nibh quis magna sodales facilisis eget in odio. Etiam elementum urna ut varius vehicula. Interdum et malesuada fames ac ante ipsum primis in faucibus. Proin luctus eget eros eu efficitur. Etiam nec sem id magna rutrum vehicula sed a tellus. Nulla nec nisi sit amet neque suscipit pharetra. Integer consectetur odio ac enim aliquam feugiat. Suspendisse potenti. Aliquam erat volutpat.  ",
            "location": "  London  ",
            "latitude": "51.5",
            "longitude": "-0.12",
            "class_size": 25,
            "availability": [{"day": "monday", "time": "09:00-10:00"}],
            "interests": [" Coding ", "coding", "Math"],
        },
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    invalid_coords = client.post("/api/profiles",
        json={
            "name": "  Class A  ",
            "location": "  London  ",
            "latitude": "-333351.5",
            "longitude": "snens",
            "class_size": 25,
            "availability": [{"day": "monday", "time": "09:00-10:00"}],
            "interests": [" Coding ", "coding", "Math"],
        },
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    invalid_availabilty = client.post("/api/profiles",
        json={
            "name": "  Class A  ",
            "location": "  London  ",
            "latitude": "51.5",
            "longitude": "-0.12",
            "class_size": 25,
            "availability": [{"day": "monday", "time": "09:00-27:00"}],
            "interests": [" Coding ", "coding", "Math"],
        },
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    huge_class = client.post("/api/profiles",
        json={
            "name": "  Class A  ",
            "location": "  London  ",
            "latitude": "51.5",
            "longitude": "-0.12",
            "class_size": 1000000000000999999999999,
            "availability": [{"day": "monday", "time": "09:00-10:00"}],
            "interests": [" Coding ", "coding", "Math"],
        },
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert no_data.status_code == 400, no_data.get_data(as_text=True)
    assert missing_name.status_code == 400, missing_name.get_data(as_text=True)
    assert long_name.status_code == 400, long_name.get_data(as_text=True)
    assert invalid_coords.status_code == 400, invalid_coords.get_data(as_text=True)
    assert invalid_availabilty.status_code == 400, invalid_availabilty.get_data(as_text=True)
    assert huge_class.status_code == 400, huge_class.get_data(as_text=True)

@pytest.mark.integration
def test_get_profile_by_id(client, auth_token, create_profile):
    token, account = auth_token
    profile = create_profile(account=account, name="FindMeLater")

    found = client.get(
        f"/api/profiles/{profile.id}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    not_found = client.get(
        f"/api/profiles/{7567484}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    payload = found.get_json()
    
    assert found.status_code == 200, found.get_data(as_text=True)
    assert payload["profile"]["id"] == profile.id
    assert not_found.status_code == 404, not_found.get_data(as_text=True)

@pytest.mark.integration
def test_update_profile_persists_changes(client, auth_token, create_profile):
    token, account = auth_token
    profile = create_profile(account=account, name="Old Name", interests=["coding"])

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
def test_delete_profile_removes_profile_row(client, auth_token, create_profile):
    token, account = auth_token
    profile = create_profile(account=account, name="Delete Me")

    response = client.delete(
        f"/api/profiles/{profile.id}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    assert Profile.query.get(profile.id) is None


@pytest.mark.integration
def test_connect_and_disconnect_profiles_persist_relations(
    client, auth_token, create_account, create_profile
):
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

    relation_forward = Relation.query.filter_by(
        from_profile_id=from_profile.id, to_profile_id=to_profile.id
    ).first()
    relation_reverse = Relation.query.filter_by(
        from_profile_id=to_profile.id, to_profile_id=from_profile.id
    ).first()
    assert relation_forward is not None
    assert relation_reverse is not None

    disconnect_response = client.delete(
        f"/api/profiles/{to_profile.id}/disconnect",
        json={"from_profile_id": from_profile.id},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert disconnect_response.status_code == 200, disconnect_response.get_data(as_text=True)
    assert Relation.query.filter_by(
        from_profile_id=from_profile.id, to_profile_id=to_profile.id
    ).first() is None
    assert Relation.query.filter_by(
        from_profile_id=to_profile.id, to_profile_id=from_profile.id
    ).first() is None
