import pytest

from src.app.model.notification import Notification


@pytest.mark.integration
def test_mark_notification_read_persists_read_flag(client, auth_token, create_notification):
    token, account = auth_token
    notification = create_notification(account=account, title="Read me", message="body")

    response = client.post(
        f"/api/notifications/{notification.id}/read",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert response.status_code == 200, response.get_data(as_text=True)

    refreshed = Notification.query.get(notification.id)
    assert refreshed is not None
    assert refreshed.read is True


@pytest.mark.integration
def test_delete_notification_removes_row(client, auth_token, create_notification):
    token, account = auth_token
    notification = create_notification(account=account, title="Delete me", message="body")

    response = client.delete(
        f"/api/notifications/{notification.id}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    assert Notification.query.get(notification.id) is None
