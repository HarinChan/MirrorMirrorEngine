import pytest

from src.app.model.account import Account
from src.app.model.profile import Profile

@pytest.mark.integration
def test_get_account_returns_current_account_and_profiles(
    client, auth_token, create_profile
):
    token, account = auth_token
    create_profile(account=account, name="Class A")
    create_profile(account=account, name="Class B")

    response = client.get(
        "/api/account",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    
    assert response.status_code == 200, response.get_data(as_text=True)
    data = response.get_json()
    assert "account" in data
    assert "classrooms" in data
    assert data["account"]["id"] == account.id
    assert data["account"]["classroom_count"] == 2
    assert len(data["classrooms"]) == 2

@pytest.mark.integration
def test_get_account_account_without_profile(client, auth_token, create_profile):
    token, account = auth_token
    
    response = client.get(
        "/api/account",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["classrooms"] == []
    assert data["account"]["classroom_count"] == 0

@pytest.mark.integration
def test_update_account_persists_to_db(client, auth_token, db):
    token, account = auth_token
    
    response = client.put(
        "/api/account",
        json={
            "email": "updated@example.com",
            "organization": "New Org",
            "password": "NewPassword123!"
        },
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    )

    assert response.status_code == 200, response.get_data(as_text=True)

    updated = db.session.get(Account, account.id)
    assert updated is not None
    assert updated.email == "updated@example.com"
    assert updated.organization == "New Org"

@pytest.mark.integration
def test_update_account_invalid_requests(client, auth_token, create_account):
    token, account = auth_token
    
    no_data = client.put("/api/account",
        json={},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    )

    invalid_email = client.put("/api/account", 
        json={"email":"-123"},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    )

    create_account("duplicate@example.com", "DupPass1234!")
    duplicate_email = client.put("/api/account",
        json={"email":"duplicate@example.com"},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    )

    org_too_long = client.put("/api/account",
        json={"organization":"Lorem ipsum dolor sit amet, consectetur adipiscing elit. Curabitur ut nibh quis magna sodales facilisis eget in odio. Etiam elementum urna ut varius vehicula. Interdum et malesuada fames ac ante ipsum primis in faucibus. Proin luctus eget eros eu efficitur. Etiam nec sem id magna rutrum vehicula sed a tellus. Nulla nec nisi sit amet neque suscipit pharetra. Integer consectetur odio ac enim aliquam feugiat. Suspendisse potenti. Aliquam erat volutpat. "},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    )

    short_pw = client.put("/api/account",
        json={"password": "a"},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    )

    basic_pw = client.put("/api/account",
        json={"password": "thisisalongbutbasicpassword"},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    )
    
    assert no_data.status_code == 400, no_data.get_data(as_text=True)
    assert invalid_email.status_code == 400, invalid_email.get_data(as_text=True)
    assert duplicate_email.status_code == 409, duplicate_email.get_data(as_text=True)
    assert org_too_long.status_code == 400, org_too_long.get_data(as_text=True)
    assert short_pw.status_code == 400, short_pw.get_data(as_text=True)
    assert basic_pw.status_code == 400, basic_pw.get_data(as_text=True)

@pytest.mark.integration
def test_delete_account_removes_account_and_profiles(client, auth_token, create_profile, db):
    token, account = auth_token
    create_profile(account=account, name="Class A")
    create_profile(account=account, name="Class B")

    response = client.delete("/api/account",
        json={"password": "a"},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    )

    assert response.status_code == 200, response.get_data(as_text=True)

    # Account removed
    deleted_account = db.session.get(Account, account.id)
    assert deleted_account is None

    # Cascade removed profiles
    remaining_profiles = Profile.query.filter_by(account_id=account.id).count()
    assert remaining_profiles == 0

@pytest.mark.integration
def test_get_account_profiles_returns_all_profiles(client, auth_token, create_profile):
    token, account = auth_token
    first = create_profile(account=account, name="Class A", interests=["coding", "math"])
    second = create_profile(account=account, name="Class B", interests=["science"])

    response = client.get(
        "/api/account/profiles",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    data = response.get_json()
    assert data["account_id"] == account.id
    assert data["total_count"] == 2
    assert len(data["classrooms"]) == 2

    ids = {c["id"] for c in data["classrooms"]}
    assert ids == {first.id, second.id}

    for classroom in data["classrooms"]:
        assert "friends_count" in classroom
        assert classroom["friends_count"] == 0

@pytest.mark.integration
def test_get_account_classrooms_empty_returns_zero_total_count(client, auth_token):
    token, account = auth_token

    response = client.get(
        "/api/account/profiles",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    data = response.get_json()
    assert data["account_id"] == account.id
    assert data["total_count"] == 0
    assert data["classrooms"] == []

@pytest.mark.integration
def test_get_account_stats_returns_aggregated_counts_and_unique_interests(
    client, auth_token, create_account, create_profile, create_relation
):
    token, account = auth_token

    profile_one = create_profile(account=account, name="Class A", interests=["coding", "math"])
    profile_two = create_profile(account=account, name="Class B", interests=["coding", "science"])

    other_account = create_account("other@example.com", "OtherPass123!")
    target_profile = create_profile(account=other_account, name="Class C", interests=["history"])

    create_relation(from_profile=profile_one, to_profile=target_profile)
    create_relation(from_profile=profile_two, to_profile=target_profile)

    response = client.get(
        "/api/account/stats",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    data = response.get_json()
    assert data["account_id"] == account.id
    assert data["total_classrooms"] == 2
    assert data["total_connections"] == 2
    assert data["unique_interests"] == 3
    assert "account_created" in data

@pytest.mark.integration
def test_get_account_stats_with_no_classrooms_returns_zero_counts(client, auth_token):
    token, account = auth_token

    response = client.get(
        "/api/account/stats",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    data = response.get_json()
    assert data["account_id"] == account.id
    assert data["total_classrooms"] == 0
    assert data["total_connections"] == 0
    assert data["unique_interests"] == 0
    assert "account_created" in data