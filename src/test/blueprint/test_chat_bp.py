import io

import pytest

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