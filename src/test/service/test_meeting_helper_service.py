from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

import src.app.service.meeting_helper as meeting_helper


def test_get_primary_profile_and_profile_membership():
    account = SimpleNamespace(profiles=SimpleNamespace(first=lambda: "primary"))
    assert meeting_helper._get_primary_profile(account) == "primary"
    assert meeting_helper._get_primary_profile(None) is None

    meeting = SimpleNamespace(creator_id=1, participants=[SimpleNamespace(id=2), SimpleNamespace(id=3)])
    assert meeting_helper._meeting_has_profile(meeting, SimpleNamespace(id=1))
    assert meeting_helper._meeting_has_profile(meeting, SimpleNamespace(id=2))
    assert not meeting_helper._meeting_has_profile(meeting, SimpleNamespace(id=99))
    assert not meeting_helper._meeting_has_profile(meeting, None)


def test_get_participant_count_counts_unique_plus_creator():
    meeting = SimpleNamespace(creator_id=1, participants=[SimpleNamespace(id=1), SimpleNamespace(id=2), SimpleNamespace(id=2)])
    assert meeting_helper._get_participant_count(meeting) == 2


@pytest.mark.parametrize(
    "classroom_ids, creator_id, expected_ids, expected_error",
    [
        (None, 1, [], None),
        ("bad", 1, None, "classroom_ids must be an array"),
        (["dummy_1"], 1, None, "Cannot invite dummy classrooms. Please use real classrooms from your network."),
        (["x"], 1, None, "Invalid classroom_id format"),
        ([1], 1, None, "You cannot invite your own classroom"),
        (["2", 2, 3, 3], 1, [2, 3], None),
    ],
)
def test_normalize_invitee_ids(classroom_ids, creator_id, expected_ids, expected_error):
    normalized, error = meeting_helper._normalize_invitee_ids(classroom_ids, creator_id)
    assert normalized == expected_ids
    assert error == expected_error


def test_doc_similarity_and_intent_helpers():
    assert meeting_helper._get_doc_similarity({"similarity": "0.75"}) == 0.75
    assert meeting_helper._get_doc_similarity({"similarity": "bad"}) == 0.0
    assert meeting_helper._get_doc_similarity(None) == 0.0

    assert meeting_helper._is_meeting_intent_query("Can we schedule a webex meeting?")
    assert not meeting_helper._is_meeting_intent_query("Tell me a story")
    assert not meeting_helper._is_meeting_intent_query(None)
    assert meeting_helper._is_classroom_intent_query("show classroom posts")
    assert not meeting_helper._is_classroom_intent_query("hello world")
    assert not meeting_helper._is_classroom_intent_query(None)


def test_serialize_meeting_with_invitees_and_dedup(monkeypatch):
    class DummyField:
        def __eq__(self, other):
            return ("eq", other)

        def in_(self, values):
            return ("in", tuple(values))

        def desc(self):
            return "desc"

    invitations = [
        SimpleNamespace(id=11, receiver_profile_id=2, receiver=SimpleNamespace(name="Class A"), status="pending"),
        SimpleNamespace(id=12, receiver_profile_id=2, receiver=SimpleNamespace(name="Class A Duplicate"), status="accepted"),
        SimpleNamespace(id=13, receiver_profile_id=3, receiver=None, status="accepted"),
    ]

    class DummyQuery:
        def filter(self, *args):
            return self

        def order_by(self, *args):
            return self

        def all(self):
            return invitations

    class DummyInvitationModel:
        query = DummyQuery()
        meeting_id = DummyField()
        status = DummyField()
        created_at = DummyField()

    monkeypatch.setattr(meeting_helper, "MeetingInvitation", DummyInvitationModel)

    meeting = SimpleNamespace(
        id=1,
        title="Sync",
        description="Desc",
        start_time=datetime(2026, 1, 1, 9, 0, 0),
        end_time=datetime(2026, 1, 1, 10, 0, 0),
        web_link="link",
        password="pw",
        creator=SimpleNamespace(name="Host", account_id=10),
        creator_id=1,
        visibility="public",
        status="active",
        max_participants=2,
        join_count=1,
        participants=[SimpleNamespace(id=2)],
    )
    viewer_profile = SimpleNamespace(id=2)
    viewer_account = SimpleNamespace(id=10)

    payload = meeting_helper._serialize_meeting(
        meeting,
        profile=viewer_profile,
        account=viewer_account,
        include_invitees=True,
    )

    assert payload["id"] == 1
    assert payload["is_creator"] is True
    assert payload["is_participant"] is True
    assert payload["is_full"] is True
    assert len(payload["invited_classrooms"]) == 2
    assert payload["invited_classrooms"][0]["can_withdraw"] is True
    assert payload["invited_classrooms"][1]["receiver_name"] == "Unknown Classroom"


def test_ensure_meeting_schema_columns_handles_inspector_and_alter_errors(monkeypatch):
    executed = []
    committed = {"count": 0}
    rolled_back = {"count": 0}

    class DummyInspector:
        def get_columns(self, table_name):
            return [{"name": "id"}]

    def fake_execute(query):
        query_str = str(query)
        executed.append(query_str)
        if "description" in query_str:
            raise RuntimeError("fail one alter")

    monkeypatch.setattr(meeting_helper, "inspect", lambda engine: DummyInspector())
    monkeypatch.setattr(
        meeting_helper,
        "db",
        SimpleNamespace(
            engine=object(),
            session=SimpleNamespace(
                execute=fake_execute,
                commit=lambda: committed.__setitem__("count", committed["count"] + 1),
                rollback=lambda: rolled_back.__setitem__("count", rolled_back["count"] + 1),
            ),
        ),
    )

    meeting_helper.ensure_meeting_schema_columns()

    assert any("ADD COLUMN visibility" in q for q in executed)
    assert any("ADD COLUMN description" in q for q in executed)
    assert committed["count"] >= 1
    assert rolled_back["count"] == 1


def test_ensure_meeting_schema_columns_returns_when_inspector_fails(monkeypatch):
    class BrokenInspector:
        def get_columns(self, table_name):
            raise RuntimeError("cannot inspect")

    monkeypatch.setattr(meeting_helper, "inspect", lambda engine: BrokenInspector())
    monkeypatch.setattr(meeting_helper, "db", SimpleNamespace(engine=object()))

    # Should not raise
    meeting_helper.ensure_meeting_schema_columns()


def test_strip_model_thinking_and_build_index_document():
    raw = "<think>secret</think>Final answer\n\n\n<thinking>more</thinking>"
    assert meeting_helper._strip_model_thinking(raw) == "Final answer"
    assert meeting_helper._strip_model_thinking("") == ""

    meeting = SimpleNamespace(
        title="Title",
        description=" desc ",
        creator=SimpleNamespace(name="Host"),
        start_time=datetime(2026, 1, 1, 9, 0, 0),
        end_time=datetime(2026, 1, 1, 10, 0, 0),
    )
    doc = meeting_helper._build_meeting_index_document(meeting)
    assert "Meeting: Title" in doc
    assert "Description: desc" in doc
    assert "Host: Host" in doc


def test_refresh_webex_if_needed_paths(monkeypatch):
    assert meeting_helper._refresh_webex_if_needed(None) == "WebEx is not connected"

    account = SimpleNamespace(webex_access_token="token", webex_token_expires_at=None)
    assert meeting_helper._refresh_webex_if_needed(account) is None

    account_expired = SimpleNamespace(
        webex_access_token="old",
        webex_refresh_token="refresh",
        webex_token_expires_at=datetime.utcnow() - timedelta(minutes=1),
    )

    committed = {"count": 0}

    monkeypatch.setattr(
        meeting_helper,
        "webex_service",
        SimpleNamespace(refresh_access_token=lambda refresh: {"access_token": "new", "refresh_token": "new-r", "expires_in": 60}),
    )
    monkeypatch.setattr(
        meeting_helper,
        "db",
        SimpleNamespace(session=SimpleNamespace(commit=lambda: committed.__setitem__("count", committed["count"] + 1))),
    )

    assert meeting_helper._refresh_webex_if_needed(account_expired) is None
    assert account_expired.webex_access_token == "new"
    assert account_expired.webex_refresh_token == "new-r"
    assert committed["count"] == 1

    monkeypatch.setattr(
        meeting_helper,
        "webex_service",
        SimpleNamespace(refresh_access_token=lambda refresh: (_ for _ in ()).throw(RuntimeError("boom"))),
    )
    account_fail = SimpleNamespace(
        webex_access_token="old",
        webex_refresh_token="refresh",
        webex_token_expires_at=datetime.utcnow() - timedelta(minutes=1),
    )
    assert meeting_helper._refresh_webex_if_needed(account_fail) == "Failed to refresh organizer's WebEx session"


def test_ensure_meeting_created_with_webex_paths(monkeypatch):
    meeting_existing = SimpleNamespace(webex_id="id", web_link="link")
    assert meeting_helper._ensure_meeting_created_with_webex(meeting_existing) is None

    meeting = SimpleNamespace(
        webex_id=None,
        web_link=None,
        creator=SimpleNamespace(account=SimpleNamespace(webex_access_token="token")),
        title="T",
        start_time=datetime(2026, 1, 1, 9, 0, 0),
        end_time=datetime(2026, 1, 1, 10, 0, 0),
        password=None,
        status="pending_setup",
    )

    monkeypatch.setattr(meeting_helper, "_refresh_webex_if_needed", lambda account: "refresh failed")
    assert meeting_helper._ensure_meeting_created_with_webex(meeting) == "refresh failed"

    monkeypatch.setattr(meeting_helper, "_refresh_webex_if_needed", lambda account: None)
    monkeypatch.setattr(
        meeting_helper,
        "webex_service",
        SimpleNamespace(create_meeting=lambda token, title, start, end: {"id": "w1", "webLink": "url", "password": "pwd"}),
    )

    assert meeting_helper._ensure_meeting_created_with_webex(meeting) is None
    assert meeting.webex_id == "w1"
    assert meeting.web_link == "url"
    assert meeting.password == "pwd"
    assert meeting.status == "active"

    monkeypatch.setattr(
        meeting_helper,
        "webex_service",
        SimpleNamespace(create_meeting=lambda token, title, start, end: (_ for _ in ()).throw(RuntimeError("api down"))),
    )
    meeting2 = SimpleNamespace(
        webex_id=None,
        web_link=None,
        creator=SimpleNamespace(account=SimpleNamespace(webex_access_token="token")),
        title="T",
        start_time=datetime(2026, 1, 1, 9, 0, 0),
        end_time=datetime(2026, 1, 1, 10, 0, 0),
    )
    monkeypatch.setattr(meeting_helper, "_refresh_webex_if_needed", lambda account: None)
    assert meeting_helper._ensure_meeting_created_with_webex(meeting2).startswith("Failed to create WebEx meeting")


def test_sync_meeting_in_chroma_paths(monkeypatch):
    deleted = []
    added = []

    monkeypatch.setattr(
        meeting_helper,
        "chroma_service",
        SimpleNamespace(
            delete_documents=lambda ids: deleted.append(ids),
            add_documents=lambda docs, metadatas, ids: added.append({"docs": docs, "metadatas": metadatas, "ids": ids}),
        ),
    )

    meeting_helper._sync_meeting_in_chroma(None)
    assert deleted == []

    private_meeting = SimpleNamespace(
        id=1,
        visibility="private",
        status="active",
        description="desc",
        title="t",
        creator=SimpleNamespace(name="Host"),
        creator_id=5,
        start_time=datetime(2026, 1, 1, 9, 0, 0),
        end_time=datetime(2026, 1, 1, 10, 0, 0),
    )
    meeting_helper._sync_meeting_in_chroma(private_meeting)
    assert deleted[-1] == ["meeting-1"]

    public_meeting = SimpleNamespace(
        id=2,
        visibility="public",
        status="active",
        description="some description",
        title="Public",
        creator=SimpleNamespace(name="Host"),
        creator_id=9,
        start_time=datetime(2026, 1, 1, 11, 0, 0),
        end_time=datetime(2026, 1, 1, 12, 0, 0),
    )
    meeting_helper._sync_meeting_in_chroma(public_meeting)

    assert deleted[-1] == ["meeting-2"]
    assert added[-1]["ids"] == ["meeting-2"]
    assert added[-1]["metadatas"][0]["source"] == "meeting"


def test_sync_meeting_in_chroma_warning_and_pass_branches(monkeypatch):
    warnings = []

    monkeypatch.setattr(
        meeting_helper,
        "current_app",
        SimpleNamespace(logger=SimpleNamespace(warning=lambda msg, err: warnings.append((msg, str(err))))),
    )

    # not-should-index branch: delete fails and logs warning
    monkeypatch.setattr(
        meeting_helper,
        "chroma_service",
        SimpleNamespace(
            delete_documents=lambda ids: (_ for _ in ()).throw(RuntimeError("delete fail")),
            add_documents=lambda docs, metadatas, ids: None,
        ),
    )

    cancelled = SimpleNamespace(
        id=3,
        visibility="public",
        status="cancelled",
        description="desc",
        title="x",
        creator=SimpleNamespace(name="Host"),
        creator_id=1,
        start_time=datetime(2026, 1, 1, 9, 0, 0),
        end_time=datetime(2026, 1, 1, 10, 0, 0),
    )
    meeting_helper._sync_meeting_in_chroma(cancelled)
    assert any("Failed removing meeting from ChromaDB" in msg for msg, _ in warnings)

    # should-index branch: initial delete fails silently, add fails and logs warning
    monkeypatch.setattr(
        meeting_helper,
        "chroma_service",
        SimpleNamespace(
            delete_documents=lambda ids: (_ for _ in ()).throw(RuntimeError("delete again")),
            add_documents=lambda docs, metadatas, ids: (_ for _ in ()).throw(RuntimeError("add fail")),
        ),
    )

    active_public = SimpleNamespace(
        id=4,
        visibility="public",
        status="active",
        description="desc",
        title="x",
        creator=SimpleNamespace(name="Host"),
        creator_id=1,
        start_time=datetime(2026, 1, 1, 9, 0, 0),
        end_time=datetime(2026, 1, 1, 10, 0, 0),
    )
    meeting_helper._sync_meeting_in_chroma(active_public)
    assert any("Failed indexing meeting in ChromaDB" in msg for msg, _ in warnings)
