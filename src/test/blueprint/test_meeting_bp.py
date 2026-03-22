import pytest
from datetime import datetime, timedelta

from src.app.model import db
from src.app.model.meeting import Meeting


@pytest.mark.integration
def test_get_upcoming_meetings_returns_created_and_participating_sorted(
    client, auth_token, create_profile, create_account, create_jwt_token
):
    token, account = auth_token
    owner_profile = create_profile(account=account, name="Owner")

    participant_account = create_account("participant@example.com", "Participant123!")
    participant_profile = create_profile(account=participant_account, name="Participant")

    now = datetime.utcnow()
    later = now + timedelta(hours=2)
    much_later = now + timedelta(hours=4)

    created_meeting = Meeting(
        title="Created by owner",
        start_time=later,
        end_time=later + timedelta(hours=1),
        creator_id=owner_profile.id,
        web_link="https://example.com/a",
    )

    participating_meeting = Meeting(
        title="Owner participates",
        start_time=much_later,
        end_time=much_later + timedelta(hours=1),
        creator_id=participant_profile.id,
        web_link="https://example.com/b",
    )
    participating_meeting.participants.append(owner_profile)

    db.session.add_all([created_meeting, participating_meeting])
    db.session.commit()

    response = client.get(
        "/api/meetings",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    payload = response.get_json()
    assert len(payload["meetings"]) == 2
    assert payload["meetings"][0]["title"] == "Created by owner"
    assert payload["meetings"][1]["title"] == "Owner participates"


@pytest.mark.integration
def test_get_upcoming_meetings_excludes_past_meetings(client, auth_token, create_profile):
    token, account = auth_token
    owner_profile = create_profile(account=account, name="Owner")

    now = datetime.utcnow()
    past_meeting = Meeting(
        title="Past",
        start_time=now - timedelta(days=1),
        end_time=now - timedelta(days=1, hours=-1),
        creator_id=owner_profile.id,
        web_link="https://example.com/past",
    )

    db.session.add(past_meeting)
    db.session.commit()

    response = client.get(
        "/api/meetings",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    payload = response.get_json()
    assert payload["meetings"] == []
