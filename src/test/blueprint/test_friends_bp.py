import pytest
from sqlalchemy.exc import IntegrityError

from src.app.model.friendrequest import FriendRequest
from src.app.model.notification import Notification
from src.app.model.relation import Relation


@pytest.mark.integration
def test_send_friend_request_new_request_path_raises_integrity_error(
    client, auth_token, create_account, create_profile, db
):
    token, sender_account = auth_token
    sender_profile = create_profile(account=sender_account, name="Sender")

    receiver_account = create_account("receiver@example.com", "Receiver123!")
    receiver_profile = create_profile(account=receiver_account, name="Receiver")

    with pytest.raises(IntegrityError):
        client.post(
            "/api/friends/request",
            json={"classroomId": receiver_profile.id},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )

    db.session.rollback()

    request_row = FriendRequest.query.filter_by(
        sender_profile_id=sender_profile.id,
        receiver_profile_id=receiver_profile.id,
        status="pending",
    ).first()
    assert request_row is None

    notif = Notification.query.filter_by(account_id=receiver_account.id).first()
    assert notif is None


@pytest.mark.integration
def test_send_friend_request_mutual_pending_auto_accepts_and_creates_relations(
    client, auth_token, create_account, create_profile, db
):
    token, sender_account = auth_token
    sender_profile = create_profile(account=sender_account, name="Sender")

    receiver_account = create_account("receiver2@example.com", "Receiver123!")
    receiver_profile = create_profile(account=receiver_account, name="Receiver")

    reverse_pending = FriendRequest(
        sender_profile_id=receiver_profile.id,
        receiver_profile_id=sender_profile.id,
        status="pending",
    )
    db.session.add(reverse_pending)
    db.session.commit()

    response = client.post(
        "/api/friends/request",
        json={"classroomId": receiver_profile.id},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert response.status_code == 200, response.get_data(as_text=True)

    refreshed = FriendRequest.query.get(reverse_pending.id)
    assert refreshed.status == "accepted"

    assert Relation.query.filter_by(
        from_profile_id=sender_profile.id, to_profile_id=receiver_profile.id
    ).first() is not None
    assert Relation.query.filter_by(
        from_profile_id=receiver_profile.id, to_profile_id=sender_profile.id
    ).first() is not None
