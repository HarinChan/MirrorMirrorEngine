import pytest

import src.app.service.openvino_service as openvino_service


class DummyConfig:
    def __init__(self):
        self.max_new_tokens = None
        self.temperature = None
        self.top_p = None


class DummyPipeline:
    def __init__(self):
        self.calls = []

    def get_generation_config(self):
        return DummyConfig()

    def generate(self, prompt, config, streamer=None):
        self.calls.append({"prompt": prompt, "config": config, "streamer": streamer})
        if streamer is not None:
            streamer("tok-1")
            streamer("tok-2")
        return "final reply"


def test_format_context_handles_empty_and_metadata():
    assert openvino_service._format_context([]) == "Context: (none)"

    context = openvino_service._format_context(
        [
            {"document": "Doc A", "metadata": {"source": "meeting"}},
            {"document": "Doc B", "metadata": "invalid"},
        ]
    )
    assert "[1] (meeting) Doc A" in context
    assert "[2] (document) Doc B" in context


def test_format_history_and_build_prompt():
    messages = [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello"},
    ]
    history = openvino_service._format_history(messages)
    assert "User: Hi" in history
    assert history.strip().endswith("Assistant:")

    prompt = openvino_service.build_prompt(messages, [{"document": "Context doc", "metadata": {"source": "post"}}])
    assert "PenPals assistant" in prompt
    assert "Context doc" in prompt


def test_get_generation_config_uses_module_constants(monkeypatch):
    pipeline = DummyPipeline()
    monkeypatch.setattr(openvino_service, "MAX_NEW_TOKENS", 111)
    monkeypatch.setattr(openvino_service, "TEMPERATURE", 0.2)
    monkeypatch.setattr(openvino_service, "TOP_P", 0.8)

    config = openvino_service._get_generation_config(pipeline)
    assert config.max_new_tokens == 111
    assert config.temperature == 0.2
    assert config.top_p == 0.8


def test_get_pipeline_raises_when_dependency_missing(monkeypatch):
    monkeypatch.setattr(openvino_service, "ov_genai", None)
    monkeypatch.setattr(openvino_service, "_PIPELINE", None)

    with pytest.raises(RuntimeError, match="openvino_genai is not installed"):
        openvino_service._get_pipeline()


def test_get_pipeline_raises_when_model_dir_missing(monkeypatch):
    class FakeOVGenAI:
        class LLMPipeline:
            def __init__(self, model_dir, device):
                self.model_dir = model_dir
                self.device = device

    monkeypatch.setattr(openvino_service, "ov_genai", FakeOVGenAI)
    monkeypatch.setattr(openvino_service, "_PIPELINE", None)
    monkeypatch.setattr(openvino_service.os.path, "isdir", lambda path: False)

    with pytest.raises(RuntimeError, match="OpenVINO model directory not found"):
        openvino_service._get_pipeline()


def test_get_pipeline_caches_instance(monkeypatch):
    created = {"count": 0}

    class FakeOVGenAI:
        class LLMPipeline:
            def __init__(self, model_dir, device):
                created["count"] += 1
                self.model_dir = model_dir
                self.device = device

    monkeypatch.setattr(openvino_service, "ov_genai", FakeOVGenAI)
    monkeypatch.setattr(openvino_service, "_PIPELINE", None)
    monkeypatch.setattr(openvino_service.os.path, "isdir", lambda path: True)

    first = openvino_service._get_pipeline()
    second = openvino_service._get_pipeline()

    assert first is second
    assert created["count"] == 1


def test_generate_reply_uses_pipeline(monkeypatch):
    pipeline = DummyPipeline()
    monkeypatch.setattr(openvino_service, "_get_pipeline", lambda: pipeline)

    result = openvino_service.generate_reply(
        [{"role": "user", "content": "Hello"}],
        [{"document": "Doc", "metadata": {"source": "post"}}],
    )

    assert result == "final reply"
    assert len(pipeline.calls) == 1
    assert "Hello" in pipeline.calls[0]["prompt"]


def test_generate_reply_stream_yields_tokens(monkeypatch):
    pipeline = DummyPipeline()
    monkeypatch.setattr(openvino_service, "_get_pipeline", lambda: pipeline)

    tokens = list(
        openvino_service.generate_reply_stream(
            [{"role": "user", "content": "Hello"}],
            [{"document": "Doc", "metadata": {"source": "post"}}],
        )
    )

    assert tokens == ["tok-1", "tok-2"]
