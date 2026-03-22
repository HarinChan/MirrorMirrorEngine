import io

import pytest
import src.app.blueprint.chat_bp as chat_bp_module

from src.app.service.fasterwhisper_service import TranscriptionInputError


@pytest.fixture(scope="function")
def chat_client(app):
    from src.app.blueprint.chat_bp import chat_bp

    app.register_blueprint(chat_bp)
    return app.test_client()


@pytest.mark.integration
def test_chat_returns_success_and_merges_context_without_duplicates(chat_client, monkeypatch):
    calls = []

    def fake_query_documents(query_text, n_results=5, where=None, min_similarity=None):
        calls.append((query_text, n_results, where, min_similarity))
        if where is None:
            return {
                "status": "success",
                "results": [
                    {"id": "doc-1", "document": "alpha"},
                    {"id": "doc-2", "document": "beta"},
                ],
            }
        return {
            "status": "success",
            "results": [
                {"id": "doc-2", "document": "beta"},
                {"id": "doc-3", "document": "gamma"},
            ],
        }

    def fake_generate_reply(messages, context_docs):
        assert messages == [
            {"role": "assistant", "content": "previous"},
            {"role": "user", "content": "hello"},
        ]
        assert [doc["id"] for doc in context_docs] == ["doc-1", "doc-2", "doc-3"]
        return "model reply"

    monkeypatch.setattr("src.app.blueprint.chat_bp.chroma_service.query_documents", fake_query_documents)
    monkeypatch.setattr("src.app.blueprint.chat_bp.generate_reply", fake_generate_reply)
    monkeypatch.setattr("src.app.blueprint.chat_bp._strip_model_thinking", lambda text: text)
    monkeypatch.setattr("src.app.blueprint.chat_bp._inject_classroom_tags", lambda reply, docs, limit, user_query: reply)
    monkeypatch.setattr("src.app.blueprint.chat_bp._inject_meeting_tags", lambda reply, docs, limit, user_query: reply)

    response = chat_client.post(
        "/api/chat",
        json={
            "message": "hello",
            "history": [{"role": "assistant", "content": "previous"}],
            "n_results": 3,
        },
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    payload = response.get_json()
    assert payload["status"] == "success"
    assert payload["reply"] == "model reply"
    assert [doc["id"] for doc in payload["context"]] == ["doc-1", "doc-2", "doc-3"]
    assert calls == [
        ("hello", 3, None, None),
        ("hello", 3, {"source": "meeting", "visibility": "public"}, None),
    ]


@pytest.mark.integration
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"message": ""},
        {"message": "   "},
        {"message": 123},
    ],
)
def test_chat_missing_or_invalid_message_returns_400(chat_client, payload):
    response = chat_client.post(
        "/api/chat",
        json=payload,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400, response.get_data(as_text=True)
    body = response.get_json()
    assert body["status"] == "error"
    assert body["message"] == "Missing or empty 'message' field"


@pytest.mark.integration
def test_chat_history_must_be_list(chat_client):
    response = chat_client.post(
        "/api/chat",
        json={"message": "hello", "history": "invalid"},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400, response.get_data(as_text=True)
    body = response.get_json()
    assert body["status"] == "error"
    assert body["message"] == "'history' must be a list"


@pytest.mark.integration
@pytest.mark.parametrize("bad_n_results", [0, -1, "2", None])
def test_chat_invalid_n_results_falls_back_to_default(chat_client, monkeypatch, bad_n_results):
    calls = []

    def fake_query_documents(query_text, n_results=5, where=None, min_similarity=None):
        calls.append((query_text, n_results, where, min_similarity))
        return {"status": "success", "results": []}

    monkeypatch.setattr("src.app.blueprint.chat_bp.chroma_service.query_documents", fake_query_documents)
    monkeypatch.setattr("src.app.blueprint.chat_bp.generate_reply", lambda messages, docs: "ok")
    monkeypatch.setattr("src.app.blueprint.chat_bp._strip_model_thinking", lambda text: text)
    monkeypatch.setattr("src.app.blueprint.chat_bp._inject_classroom_tags", lambda reply, docs, limit, user_query: reply)
    monkeypatch.setattr("src.app.blueprint.chat_bp._inject_meeting_tags", lambda reply, docs, limit, user_query: reply)

    response = chat_client.post(
        "/api/chat",
        json={"message": "hello", "history": [], "n_results": bad_n_results},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    assert calls[0][1] == 5
    assert calls[1][1] == 5


@pytest.mark.integration
def test_chat_uses_empty_context_when_chroma_queries_fail(chat_client, monkeypatch):
    captured = {}

    def fake_query_documents(query_text, n_results=5, where=None, min_similarity=None):
        return {"status": "error", "message": "failed"}

    def fake_generate_reply(messages, context_docs):
        captured["context_docs"] = context_docs
        return "fallback reply"

    monkeypatch.setattr("src.app.blueprint.chat_bp.chroma_service.query_documents", fake_query_documents)
    monkeypatch.setattr("src.app.blueprint.chat_bp.generate_reply", fake_generate_reply)
    monkeypatch.setattr("src.app.blueprint.chat_bp._strip_model_thinking", lambda text: text)
    monkeypatch.setattr("src.app.blueprint.chat_bp._inject_classroom_tags", lambda reply, docs, limit, user_query: reply)
    monkeypatch.setattr("src.app.blueprint.chat_bp._inject_meeting_tags", lambda reply, docs, limit, user_query: reply)

    response = chat_client.post(
        "/api/chat",
        json={"message": "hello", "history": []},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    assert captured["context_docs"] == []
    payload = response.get_json()
    assert payload["status"] == "success"
    assert payload["context"] == []


@pytest.mark.integration
def test_chat_returns_500_on_unhandled_error(chat_client, monkeypatch):
    monkeypatch.setattr(
        "src.app.blueprint.chat_bp.chroma_service.query_documents",
        lambda query_text, n_results=5, where=None, min_similarity=None: {"status": "success", "results": []},
    )
    monkeypatch.setattr("src.app.blueprint.chat_bp.generate_reply", lambda messages, docs: (_ for _ in ()).throw(RuntimeError("chat boom")))

    response = chat_client.post(
        "/api/chat",
        json={"message": "hello", "history": []},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 500, response.get_data(as_text=True)
    body = response.get_json()
    assert body["status"] == "error"
    assert body["message"] == "chat boom"


@pytest.mark.integration
def test_transcribe_missing_audio_file_returns_400(chat_client):
    response = chat_client.post(
        "/api/chat/transcribe",
        data={"hotwords": "math"},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400, response.get_data(as_text=True)
    body = response.get_json()
    assert body["status"] == "error"
    assert body["message"] == "Missing 'audio' file in form data"
    assert body["received_file_keys"] == []


@pytest.mark.integration
def test_transcribe_with_audio_key_returns_transcript(chat_client, monkeypatch):
    calls = {}

    def fake_transcribe_uploaded_file(audio_file, hotwords):
        calls["filename"] = audio_file.filename
        calls["hotwords"] = hotwords
        return "transcribed text"

    monkeypatch.setattr("src.app.blueprint.chat_bp.transcribe_uploaded_file", fake_transcribe_uploaded_file)

    response = chat_client.post(
        "/api/chat/transcribe",
        data={
            "audio": (io.BytesIO(b"abc"), "clip.webm"),
            "hotwords": "  classroom, science  ",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    body = response.get_json()
    assert body == {"status": "success", "transcript": "transcribed text", "engine": "faster-whisper"}
    assert calls == {"filename": "clip.webm", "hotwords": "classroom, science"}


@pytest.mark.integration
@pytest.mark.parametrize("file_field", ["file", "recording"])
def test_transcribe_accepts_fallback_file_field_names(chat_client, monkeypatch, file_field):
    monkeypatch.setattr("src.app.blueprint.chat_bp.transcribe_uploaded_file", lambda audio_file, hotwords: "ok")

    response = chat_client.post(
        "/api/chat/transcribe",
        data={file_field: (io.BytesIO(b"audio"), "input.webm")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    assert response.get_json()["transcript"] == "ok"


@pytest.mark.integration
def test_transcribe_input_error_uses_exception_status_code(chat_client, monkeypatch):
    def fake_transcribe_uploaded_file(audio_file, hotwords):
        raise TranscriptionInputError("too large", status_code=413)

    monkeypatch.setattr("src.app.blueprint.chat_bp.transcribe_uploaded_file", fake_transcribe_uploaded_file)

    response = chat_client.post(
        "/api/chat/transcribe",
        data={"audio": (io.BytesIO(b"abc"), "clip.webm")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 413, response.get_data(as_text=True)
    body = response.get_json()
    assert body["status"] == "error"
    assert body["message"] == "too large"


@pytest.mark.integration
def test_transcribe_runtime_error_returns_local_unavailable_message(chat_client, monkeypatch):
    def fake_transcribe_uploaded_file(audio_file, hotwords):
        raise RuntimeError("missing backend")

    monkeypatch.setattr("src.app.blueprint.chat_bp.transcribe_uploaded_file", fake_transcribe_uploaded_file)

    response = chat_client.post(
        "/api/chat/transcribe",
        data={"audio": (io.BytesIO(b"abc"), "clip.webm")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 500, response.get_data(as_text=True)
    body = response.get_json()
    assert body["status"] == "error"
    assert "Local transcription unavailable" in body["message"]
    assert "missing backend" in body["message"]


@pytest.mark.integration
def test_transcribe_unhandled_exception_returns_500(chat_client, monkeypatch):
    def fake_transcribe_uploaded_file(audio_file, hotwords):
        raise ValueError("unexpected")

    monkeypatch.setattr("src.app.blueprint.chat_bp.transcribe_uploaded_file", fake_transcribe_uploaded_file)

    response = chat_client.post(
        "/api/chat/transcribe",
        data={"audio": (io.BytesIO(b"abc"), "clip.webm")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 500, response.get_data(as_text=True)
    body = response.get_json()
    assert body["status"] == "error"
    assert body["message"] == "unexpected"


def test_extract_context_classroom_ids_returns_empty_for_non_list():
    result = chat_bp_module._extract_context_classroom_ids(context_docs=None)
    assert result == []


def test_extract_context_classroom_ids_applies_intent_threshold_and_filters(monkeypatch):
    monkeypatch.setattr("src.app.blueprint.chat_bp._is_classroom_intent_query", lambda user_query: True)
    monkeypatch.setattr(
        "src.app.blueprint.chat_bp._get_doc_similarity",
        lambda doc: doc.get("similarity", 0),
    )

    docs = [
        {"id": "ignore-1", "similarity": 0.11, "metadata": {"source": "post", "profile_id": "c1"}},
        {"id": "ignore-2", "similarity": 0.20, "metadata": {"source": "meeting", "profile_id": "c2"}},
        {"id": "ok-1", "similarity": 0.12, "metadata": {"source": "post", "profile_id": "c1"}},
        {"id": "ok-2", "similarity": 0.50, "metadata": {"source": "post", "classroom_id": "c2"}},
        {"id": "dupe", "similarity": 0.60, "metadata": {"source": "post", "profile_id": "c1"}},
        "not-a-dict",
    ]

    result = chat_bp_module._extract_context_classroom_ids(docs, limit=3, user_query="show me classrooms")
    assert result == ["c1", "c2"]


def test_extract_context_classroom_ids_non_intent_uses_higher_threshold(monkeypatch):
    monkeypatch.setattr("src.app.blueprint.chat_bp._is_classroom_intent_query", lambda user_query: False)
    monkeypatch.setattr(
        "src.app.blueprint.chat_bp._get_doc_similarity",
        lambda doc: doc.get("similarity", 0),
    )

    docs = [
        {"similarity": 0.34, "metadata": {"source": "post", "profile_id": "c1"}},
        {"similarity": 0.35, "metadata": {"source": "post", "profile_id": "c2"}},
    ]

    result = chat_bp_module._extract_context_classroom_ids(docs, user_query="random question")
    assert result == ["c2"]


def test_inject_classroom_tags_behaviour(monkeypatch):
    assert chat_bp_module._inject_classroom_tags("", []) == ""
    assert chat_bp_module._inject_classroom_tags(None, []) is None

    reply_with_tag = 'Already tagged\n<classroom id="x"/>'
    assert chat_bp_module._inject_classroom_tags(reply_with_tag, [{"id": 1}]) == reply_with_tag

    monkeypatch.setattr("src.app.blueprint.chat_bp._extract_context_classroom_ids", lambda docs, limit, user_query: ["10", "11"])
    tagged = chat_bp_module._inject_classroom_tags("Answer with trailing space   ", [{"id": "a"}], 3, "query")
    assert tagged == 'Answer with trailing space\n<classroom id="10"/>\n<classroom id="11"/>'


@pytest.mark.parametrize(
    "value, expected",
    [
        ('[{"Content":"Hello"},{"content":"world"}]', "Hello world"),
        ([{"Content": "A"}, {"content": "B"}], "A B"),
        ("   plain transcript   ", "plain transcript"),
        (None, ""),
    ],
)
def test_extract_transcript_text_variants(value, expected):
    assert chat_bp_module._extract_transcript_text(value) == expected


def test_extract_context_meeting_ids_returns_empty_for_non_list():
    result = chat_bp_module._extract_context_meeting_ids(context_docs="not-list")
    assert result == []


def test_extract_context_meeting_ids_applies_threshold_and_filters(monkeypatch):
    monkeypatch.setattr("src.app.blueprint.chat_bp._is_meeting_intent_query", lambda user_query: True)
    monkeypatch.setattr(
        "src.app.blueprint.chat_bp._get_doc_similarity",
        lambda doc: doc.get("similarity", 0),
    )

    docs = [
        {"similarity": 0.10, "metadata": {"source": "meeting", "meeting_id": "m0"}},
        {"similarity": 0.12, "metadata": {"source": "meeting", "meeting_id": "m1"}},
        {"similarity": 0.20, "metadata": {"source": "post", "meeting_id": "m2"}},
        {"similarity": 0.30, "metadata": {"source": "meeting", "meeting_id": "m2"}},
        {"similarity": 0.40, "metadata": {"source": "meeting", "meeting_id": "m1"}},
    ]

    result = chat_bp_module._extract_context_meeting_ids(docs, limit=3, user_query="meeting info")
    assert result == ["m1", "m2"]


def test_extract_context_meeting_ids_non_intent_uses_higher_threshold(monkeypatch):
    monkeypatch.setattr("src.app.blueprint.chat_bp._is_meeting_intent_query", lambda user_query: False)
    monkeypatch.setattr(
        "src.app.blueprint.chat_bp._get_doc_similarity",
        lambda doc: doc.get("similarity", 0),
    )

    docs = [
        {"similarity": 0.34, "metadata": {"source": "meeting", "meeting_id": "m1"}},
        {"similarity": 0.35, "metadata": {"source": "meeting", "meeting_id": "m2"}},
    ]

    result = chat_bp_module._extract_context_meeting_ids(docs, user_query="random question")
    assert result == ["m2"]


def test_inject_meeting_tags_behaviour(monkeypatch):
    assert chat_bp_module._inject_meeting_tags("", []) == ""
    assert chat_bp_module._inject_meeting_tags(None, []) is None

    reply_with_tag = 'Already tagged\n<meeting id="x"/>'
    assert chat_bp_module._inject_meeting_tags(reply_with_tag, [{"id": 1}]) == reply_with_tag

    monkeypatch.setattr("src.app.blueprint.chat_bp._extract_context_meeting_ids", lambda docs, limit, user_query: ["21", "22"])
    tagged = chat_bp_module._inject_meeting_tags("Answer\n", [{"id": "a"}], 3, "query")
    assert tagged == 'Answer\n<meeting id="21"/>\n<meeting id="22"/>'