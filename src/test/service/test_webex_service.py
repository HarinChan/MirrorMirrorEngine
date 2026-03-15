from datetime import datetime

import pytest
import requests

from src.app.service.webex_service import WebexService


class DummyResponse:
    def __init__(self, payload=None, should_raise=False):
        self._payload = payload or {}
        self._should_raise = should_raise
        self.text = "error"

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self._should_raise:
            raise requests.exceptions.HTTPError("http error")


@pytest.fixture
def service(monkeypatch):
    monkeypatch.setenv("WEBEX_CLIENT_ID", "client")
    monkeypatch.setenv("WEBEX_CLIENT_SECRET", "secret")
    monkeypatch.setenv("WEBEX_REDIRECT_URI", "https://app.test/callback")
    return WebexService()


def test_get_auth_url_returns_empty_when_env_missing(monkeypatch):
    monkeypatch.delenv("WEBEX_CLIENT_ID", raising=False)
    monkeypatch.delenv("WEBEX_REDIRECT_URI", raising=False)

    svc = WebexService()
    assert svc.get_auth_url() == ""


def test_get_auth_url_contains_expected_parameters(service):
    url = service.get_auth_url()

    assert url.startswith("https://webexapis.com/v1/authorize?")
    assert "client_id=client" in url
    assert "response_type=code" in url
    assert "redirect_uri=https%3A%2F%2Fapp.test%2Fcallback" in url


def test_exchange_code_posts_payload_and_returns_json(service, monkeypatch):
    captured = {}

    def fake_post(url, json):
        captured["url"] = url
        captured["json"] = json
        return DummyResponse({"access_token": "token"})

    monkeypatch.setattr(requests, "post", fake_post)

    result = service.exchange_code("abc")
    assert result == {"access_token": "token"}
    assert captured["url"].endswith("/access_token")
    assert captured["json"]["grant_type"] == "authorization_code"


def test_exchange_code_raises_on_http_error(service, monkeypatch):
    monkeypatch.setattr(requests, "post", lambda url, json: DummyResponse(should_raise=True))

    with pytest.raises(requests.exceptions.HTTPError):
        service.exchange_code("abc")


def test_refresh_access_token_posts_payload(service, monkeypatch):
    captured = {}

    def fake_post(url, json):
        captured["json"] = json
        return DummyResponse({"access_token": "new-token"})

    monkeypatch.setattr(requests, "post", fake_post)

    result = service.refresh_access_token("refresh")
    assert result == {"access_token": "new-token"}
    assert captured["json"]["grant_type"] == "refresh_token"


def test_create_meeting_requires_access_token(service):
    with pytest.raises(ValueError):
        service.create_meeting(None, "Title", datetime(2026, 1, 1, 9, 0, 0), datetime(2026, 1, 1, 10, 0, 0))


def test_create_meeting_posts_expected_payload(service, monkeypatch):
    captured = {}

    def fake_post(url, headers, json):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return DummyResponse({"id": "meeting-1"})

    monkeypatch.setattr(requests, "post", fake_post)

    result = service.create_meeting(
        "token",
        "Team Sync",
        datetime(2026, 1, 1, 9, 0, 0),
        datetime(2026, 1, 1, 10, 0, 0),
    )

    assert result == {"id": "meeting-1"}
    assert captured["headers"]["Authorization"] == "Bearer token"
    assert captured["json"]["start"] == "2026-01-01T09:00:00"
    assert captured["json"]["end"] == "2026-01-01T10:00:00"


def test_delete_meeting_requires_access_token(service):
    with pytest.raises(ValueError):
        service.delete_meeting(None, "m-1")


def test_delete_meeting_calls_api_and_returns_true(service, monkeypatch):
    captured = {}

    def fake_delete(url, headers):
        captured["url"] = url
        captured["headers"] = headers
        return DummyResponse({})

    monkeypatch.setattr(requests, "delete", fake_delete)

    result = service.delete_meeting("token", "m-1")
    assert result is True
    assert captured["url"].endswith("/meetings/m-1")


def test_update_meeting_requires_access_token(service):
    with pytest.raises(ValueError):
        service.update_meeting(None, "m-1", datetime(2026, 1, 1, 9, 0, 0), datetime(2026, 1, 1, 10, 0, 0))


def test_update_meeting_posts_payload_with_optional_title(service, monkeypatch):
    captured = {}

    def fake_put(url, headers, json):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return DummyResponse({"id": "m-1", "title": "Updated"})

    monkeypatch.setattr(requests, "put", fake_put)

    result = service.update_meeting(
        "token",
        "m-1",
        datetime(2026, 1, 1, 9, 0, 0),
        datetime(2026, 1, 1, 10, 0, 0),
        title="Updated",
    )

    assert result["id"] == "m-1"
    assert captured["json"]["title"] == "Updated"
