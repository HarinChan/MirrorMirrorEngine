import pytest
import requests
from datetime import datetime, timedelta

from src.app.model.account import Account
from src.app.model.meeting import Meeting
from src.app.model.meetinginvitation import MeetingInvitation
from src.app.blueprint.webex_bp import validate_meeting_schedule


@pytest.fixture(autouse=True)
def block_outbound_http(monkeypatch):
    def _deny_network(*args, **kwargs):
        raise AssertionError("Outbound HTTP is blocked in tests. Mock the Webex call target instead.")

    monkeypatch.setattr(requests.sessions.Session, "request", _deny_network)


@pytest.mark.integration
def test_validate_meeting_schedule_rules():
    now = datetime.utcnow()

    assert validate_meeting_schedule(now + timedelta(hours=1), now) == "end_time must be after start_time"

    too_short = validate_meeting_schedule(now, now + timedelta(minutes=10))
    assert "Meeting duration must be between" in too_short

    too_long = validate_meeting_schedule(now, now + timedelta(minutes=80))
    assert "Meeting duration must be between" in too_long

    too_far = validate_meeting_schedule(now + timedelta(days=15), now + timedelta(days=15, minutes=30))
    assert "Meetings can be scheduled up to" in too_far

    assert validate_meeting_schedule(now + timedelta(hours=1), now + timedelta(hours=1, minutes=30)) is None


@pytest.mark.integration
def test_get_webex_auth_url_returns_mocked_service_value(client, auth_token, monkeypatch):
    token, _ = auth_token

    monkeypatch.setattr(
        "src.app.blueprint.webex_bp.webex_service.get_auth_url",
        lambda: "https://example.test/oauth",
    )

    response = client.get(
        "/api/webex/auth-url",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    assert response.get_json() == {"url": "https://example.test/oauth"}


@pytest.mark.integration
def test_connect_and_disconnect_webex_persist_account_tokens(client, auth_token, monkeypatch):
    token, account = auth_token

    def fake_exchange_code(code):
        assert code == "auth-code-123"
        return {
            "access_token": "access-xyz",
            "refresh_token": "refresh-xyz",
            "expires_in": 3600,
        }

    monkeypatch.setattr("src.app.blueprint.webex_bp.webex_service.exchange_code", fake_exchange_code)

    response_connect = client.post(
        "/api/webex/connect",
        json={"code": "auth-code-123"},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert response_connect.status_code == 200, response_connect.get_data(as_text=True)

    refreshed_account = Account.query.get(account.id)
    assert refreshed_account.webex_access_token == "access-xyz"
    assert refreshed_account.webex_refresh_token == "refresh-xyz"

    response_disconnect = client.post(
        "/api/webex/disconnect",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert response_disconnect.status_code == 200, response_disconnect.get_data(as_text=True)

    disconnected_account = Account.query.get(account.id)
    assert disconnected_account.webex_access_token is None
    assert disconnected_account.webex_refresh_token is None
    assert disconnected_account.webex_token_expires_at is None


@pytest.mark.integration
def test_connect_webex_missing_code_returns_400(client, auth_token):
    token, _ = auth_token

    response = client.post(
        "/api/webex/connect",
        json={},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert response.status_code == 400, response.get_data(as_text=True)
    assert response.get_json()["msg"] == "Missing auth code"


@pytest.mark.integration
def test_connect_webex_exchange_failure_returns_500(client, auth_token, monkeypatch):
    token, _ = auth_token

    monkeypatch.setattr(
        "src.app.blueprint.webex_bp.webex_service.exchange_code",
        lambda code: (_ for _ in ()).throw(RuntimeError("exchange failed")),
    )

    response = client.post(
        "/api/webex/connect",
        json={"code": "bad"},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert response.status_code == 500, response.get_data(as_text=True)
    assert response.get_json()["msg"] == "exchange failed"


@pytest.mark.integration
def test_webex_status_reflects_connected_state(client, auth_token):
    token, account = auth_token

    account.webex_access_token = None
    response_disconnected = client.get(
        "/api/webex/status",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    assert response_disconnected.status_code == 200, response_disconnected.get_data(as_text=True)
    assert response_disconnected.get_json() == {"connected": False}

    account.webex_access_token = "token"
    from src.app.model import db

    db.session.commit()

    response_connected = client.get(
        "/api/webex/status",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    assert response_connected.status_code == 200, response_connected.get_data(as_text=True)
    assert response_connected.get_json() == {"connected": True}


@pytest.mark.integration
def test_create_webex_meeting_requires_invitee_for_private(client, auth_token, create_profile):
    token, account = auth_token
    create_profile(account=account, name="Sender")

    start = datetime.utcnow() + timedelta(days=1)
    end = start + timedelta(minutes=30)

    response = client.post(
        "/api/webex/meeting",
        json={
            "title": "Planning Meeting",
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "is_public": False,
        },
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert response.status_code == 400, response.get_data(as_text=True)
    assert "classroom_id or classroom_ids is required" in response.get_json()["msg"]


@pytest.mark.integration
def test_create_webex_meeting_invalid_max_participants_returns_400(client, auth_token, create_profile):
    token, account = auth_token
    create_profile(account=account, name="Sender")

    start = datetime.utcnow() + timedelta(days=1)
    end = start + timedelta(minutes=30)

    response = client.post(
        "/api/webex/meeting",
        json={
            "title": "Planning Meeting",
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "classroom_ids": [999],
            "max_participants": "not-a-number",
        },
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert response.status_code == 400, response.get_data(as_text=True)
    assert response.get_json()["msg"] == "max_participants must be a number"


@pytest.mark.integration
def test_create_webex_meeting_persists_pending_invitation(client, auth_token, create_account, create_profile, monkeypatch):
    token, sender_account = auth_token
    sender_profile = create_profile(account=sender_account, name="Sender")

    receiver_account = create_account("webex-receiver@example.com", "Receiver123!")
    receiver_profile = create_profile(account=receiver_account, name="Receiver")

    monkeypatch.setattr("src.app.blueprint.webex_bp._sync_meeting_in_chroma", lambda meeting: None)

    start = datetime.utcnow() + timedelta(days=1)
    end = start + timedelta(minutes=30)

    response = client.post(
        "/api/webex/meeting",
        json={
            "title": "Planning Meeting",
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "classroom_id": receiver_profile.id,
        },
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert response.status_code == 201, response.get_data(as_text=True)

    invitation = MeetingInvitation.query.filter_by(
        sender_profile_id=sender_profile.id,
        receiver_profile_id=receiver_profile.id,
        status="pending",
    ).first()
    assert invitation is not None
    assert invitation.title == "Planning Meeting"


@pytest.mark.integration
def test_manage_meeting_get_returns_meeting_for_creator(client, auth_token, create_profile, db):
    token, account = auth_token
    profile = create_profile(account=account, name="Creator")

    meeting = Meeting(
        title="Details",
        start_time=datetime.utcnow() + timedelta(days=1),
        end_time=datetime.utcnow() + timedelta(days=1, minutes=30),
        creator_id=profile.id,
        visibility="private",
        status="pending_setup",
    )
    db.session.add(meeting)
    db.session.commit()

    response = client.get(
        f"/api/webex/meeting/{meeting.id}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    body = response.get_json()
    assert body["id"] == meeting.id
    assert body["title"] == "Details"


@pytest.mark.integration
def test_manage_meeting_put_rejects_invalid_visibility(client, auth_token, create_profile, db):
    token, account = auth_token
    profile = create_profile(account=account, name="Creator")

    meeting = Meeting(
        title="Editable",
        start_time=datetime.utcnow() + timedelta(days=1),
        end_time=datetime.utcnow() + timedelta(days=1, minutes=30),
        creator_id=profile.id,
        visibility="private",
        status="pending_setup",
    )
    db.session.add(meeting)
    db.session.commit()

    response = client.put(
        f"/api/webex/meeting/{meeting.id}",
        json={"visibility": "friends-only"},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert response.status_code == 400, response.get_data(as_text=True)
    assert response.get_json()["msg"] == "visibility must be 'private' or 'public'"


@pytest.mark.integration
def test_manage_meeting_delete_non_creator_returns_403(client, auth_token, create_account, create_profile, create_jwt_token, db):
    creator_token, creator_account = auth_token
    creator_profile = create_profile(account=creator_account, name="Creator")

    other_account = create_account("other-delete@example.com", "Other123!")
    other_profile = create_profile(account=other_account, name="Other")
    other_token = create_jwt_token(str(other_account.id))

    meeting = Meeting(
        title="Delete test",
        start_time=datetime.utcnow() + timedelta(days=1),
        end_time=datetime.utcnow() + timedelta(days=1, minutes=30),
        creator_id=creator_profile.id,
        visibility="private",
        status="pending_setup",
    )
    db.session.add(meeting)
    db.session.commit()

    assert other_profile.id != creator_profile.id

    response = client.delete(
        f"/api/webex/meeting/{meeting.id}",
        headers={"Authorization": f"Bearer {other_token}", "Content-Type": "application/json"},
    )

    assert response.status_code == 403, response.get_data(as_text=True)
    assert response.get_json()["msg"] == "Unauthorized"


@pytest.mark.integration
def test_accept_invitation_persists_meeting_and_marks_invitation_accepted(
    client, auth_token, create_account, create_profile, create_jwt_token, db, monkeypatch
):
    _, sender_account = auth_token
    sender_profile = create_profile(account=sender_account, name="Sender")

    receiver_account = create_account("webex-accept@example.com", "Receiver123!")
    receiver_profile = create_profile(account=receiver_account, name="Receiver")
    receiver_token = create_jwt_token(str(receiver_account.id))

    sender_account.webex_access_token = "sender-token"
    sender_account.webex_refresh_token = "sender-refresh"
    sender_account.webex_token_expires_at = datetime.utcnow() + timedelta(hours=1)

    invitation = MeetingInvitation(
        sender_profile_id=sender_profile.id,
        receiver_profile_id=receiver_profile.id,
        title="Accept Test",
        start_time=datetime.utcnow() + timedelta(days=1),
        end_time=datetime.utcnow() + timedelta(days=1, minutes=30),
        status="pending",
    )
    db.session.add(invitation)
    db.session.commit()

    def fake_create_meeting(access_token, title, start_time, end_time):
        assert access_token == "sender-token"
        return {
            "id": "webex-123",
            "title": title,
            "webLink": "https://meet.webex.com/abc",
            "password": "secret",
        }

    monkeypatch.setattr(
        "src.app.service.meeting_helper.webex_service.create_meeting",
        fake_create_meeting,
    )

    response = client.post(
        f"/api/webex/invitations/{invitation.id}/accept",
        headers={"Authorization": f"Bearer {receiver_token}", "Content-Type": "application/json"},
    )

    assert response.status_code == 201, response.get_data(as_text=True)

    refreshed_invitation = MeetingInvitation.query.get(invitation.id)
    assert refreshed_invitation.status == "accepted"

    created_meeting = Meeting.query.filter_by(webex_id="webex-123").first()
    assert created_meeting is not None
    assert created_meeting.creator_id == sender_profile.id
    assert receiver_profile in created_meeting.participants


@pytest.mark.integration
def test_accept_invitation_uses_ensure_error_as_403(
    client, auth_token, create_account, create_profile, create_jwt_token, db, monkeypatch
):
    _, sender_account = auth_token
    sender_profile = create_profile(account=sender_account, name="Sender")

    receiver_account = create_account("webex-accept-error@example.com", "Receiver123!")
    receiver_profile = create_profile(account=receiver_account, name="Receiver")
    receiver_token = create_jwt_token(str(receiver_account.id))

    invitation = MeetingInvitation(
        sender_profile_id=sender_profile.id,
        receiver_profile_id=receiver_profile.id,
        title="Accept Error Test",
        start_time=datetime.utcnow() + timedelta(days=1),
        end_time=datetime.utcnow() + timedelta(days=1, minutes=30),
        status="pending",
    )
    db.session.add(invitation)
    db.session.commit()

    monkeypatch.setattr(
        "src.app.blueprint.webex_bp._ensure_meeting_created_with_webex",
        lambda meeting: "Failed to create WebEx meeting: blocked",
    )

    response = client.post(
        f"/api/webex/invitations/{invitation.id}/accept",
        headers={"Authorization": f"Bearer {receiver_token}", "Content-Type": "application/json"},
    )

    assert response.status_code == 403, response.get_data(as_text=True)
    assert response.get_json()["msg"] == "Failed to create WebEx meeting: blocked"


@pytest.mark.integration
def test_decline_and_cancel_invitation_paths(client, auth_token, create_account, create_profile, create_jwt_token, db):
    sender_token, sender_account = auth_token
    sender_profile = create_profile(account=sender_account, name="Sender")

    receiver_account = create_account("webex-decline@example.com", "Receiver123!")
    receiver_profile = create_profile(account=receiver_account, name="Receiver")
    receiver_token = create_jwt_token(str(receiver_account.id))

    invitation = MeetingInvitation(
        sender_profile_id=sender_profile.id,
        receiver_profile_id=receiver_profile.id,
        title="Decline Test",
        start_time=datetime.utcnow() + timedelta(days=1),
        end_time=datetime.utcnow() + timedelta(days=1, minutes=30),
        status="pending",
    )
    db.session.add(invitation)
    db.session.commit()

    response_decline = client.post(
        f"/api/webex/invitations/{invitation.id}/decline",
        headers={"Authorization": f"Bearer {receiver_token}", "Content-Type": "application/json"},
    )

    assert response_decline.status_code == 200, response_decline.get_data(as_text=True)
    assert MeetingInvitation.query.get(invitation.id).status == "declined"

    invitation2 = MeetingInvitation(
        sender_profile_id=sender_profile.id,
        receiver_profile_id=receiver_profile.id,
        title="Cancel Test",
        start_time=datetime.utcnow() + timedelta(days=2),
        end_time=datetime.utcnow() + timedelta(days=2, minutes=30),
        status="pending",
    )
    db.session.add(invitation2)
    db.session.commit()

    response_cancel = client.post(
        f"/api/webex/invitations/{invitation2.id}/cancel",
        headers={"Authorization": f"Bearer {sender_token}", "Content-Type": "application/json"},
    )

    assert response_cancel.status_code == 200, response_cancel.get_data(as_text=True)
    assert MeetingInvitation.query.get(invitation2.id).status == "cancelled"
