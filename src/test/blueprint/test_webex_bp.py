import pytest
from datetime import datetime, timedelta

from src.app.model.account import Account
from src.app.model.meeting import Meeting
from src.app.model.meetinginvitation import MeetingInvitation


@pytest.mark.integration
def test_connect_and_disconnect_webex_persist_account_tokens(client, auth_token):
    token, account = auth_token

    def fake_exchange_code(code):
        assert code == "auth-code-123"
        return {
            "access_token": "access-xyz",
            "refresh_token": "refresh-xyz",
            "expires_in": 3600,
        }

    response_connect = client.post(
        "/api/webex/connect",
        json={"code": "auth-code-123"},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    # If this fails, patching in the app may be needed in production tests.
    assert response_connect.status_code in (200, 500), response_connect.get_data(as_text=True)

    # Monkeypatch after request binding; route uses module-level service object.
    from src.app.blueprint import webex_bp as webex_module

    webex_module.webex_service.exchange_code = fake_exchange_code

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
def test_create_webex_meeting_persists_pending_invitation(
    client, auth_token, create_account, create_profile
):
    token, sender_account = auth_token
    sender_profile = create_profile(account=sender_account, name="Sender")

    receiver_account = create_account("webex-receiver@example.com", "Receiver123!")
    receiver_profile = create_profile(account=receiver_account, name="Receiver")

    start = datetime.utcnow() + timedelta(days=1)
    end = start + timedelta(hours=1)

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
def test_accept_invitation_persists_meeting_and_marks_invitation_accepted(
    client, auth_token, create_account, create_profile, create_jwt_token, db, monkeypatch
):
    sender_token, sender_account = auth_token
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
        end_time=datetime.utcnow() + timedelta(days=1, hours=1),
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
        "src.app.blueprint.webex_bp.webex_service.create_meeting",
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
