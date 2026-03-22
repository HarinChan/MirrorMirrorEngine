import os 
import threading
import queue
from pathlib import Path
from typing import Any, Dict, Iterable, List

import openvino_genai as ov_genai

DEFAULT_MODEL_DIR = os.getenv(
    "OPENVINO_MODEL_DIR",
    str(
        Path(__file__).resolve().parents[3]
        / "models"
        / "DeepSeek-R1-Distill-Qwen-1.5B-int4-cw-ov"
    ),
)

MAX_NEW_TOKENS = int(os.getenv("OPENVINO_MAX_NEW_TOKENS", "256"))
TEMPERATURE = float(os.getenv("OPENVINO_TEMPERATURE", "0.7"))
TOP_P = float(os.getenv("OPENVINO_TOP_P", "0.9"))

_PIPELINE_LOCK = threading.Lock()
_PIPELINE = None


def _get_pipeline():
    if ov_genai is None:
        raise RuntimeError(
            "openvino_genai is not installed. Add openvino-genai to requirements.txt."
        )

    global _PIPELINE
    with _PIPELINE_LOCK:
        if _PIPELINE is None:
            if not os.path.isdir(DEFAULT_MODEL_DIR):
                raise RuntimeError(
                    f"OpenVINO model directory not found: {DEFAULT_MODEL_DIR}"
                )
            _PIPELINE = ov_genai.LLMPipeline(DEFAULT_MODEL_DIR, "CPU")
        return _PIPELINE
    
def _get_generation_config(pipeline):
    config = pipeline.get_generation_config()
    config.max_new_tokens = MAX_NEW_TOKENS
    config.temperature = TEMPERATURE
    config.top_p = TOP_P
    return config


def _format_context(context_docs: List[Dict[str, Any]]) -> str:
    if not context_docs:
        return "Context: (none)"

    lines = ["Context:"]
    for idx, doc in enumerate(context_docs, start=1):
        text = doc.get("document", "")
        metadata = doc.get("metadata", {})
        source = metadata.get("source", "document") if isinstance(metadata, dict) else "document"
        lines.append(f"[{idx}] ({source}) {text}")
    return "\n".join(lines)

def _format_history(messages: List[Dict[str, str]]) -> str:
    lines = []
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        if role == "assistant":
            lines.append(f"Assistant: {content}")
        else:
            lines.append(f"User: {content}")
    lines.append("Assistant:")
    return "\n".join(lines)


def build_prompt(messages: List[Dict[str, str]], context_docs: List[Dict[str, Any]]) -> str:
    system = (
        "You are the PenPals assistant. Use the provided context when it is relevant. "
        "If the context is missing or does not help, answer based on general knowledge "
        "and say you are not sure when appropriate. Keep responses concise and helpful."
    )
    context = _format_context(context_docs)
    history = _format_history(messages)
    return f"{system}\n\n{context}\n\n{history}"

def generate_reply(messages: List[Dict[str, str]], context_docs: List[Dict[str, Any]]) -> str:
    pipeline = _get_pipeline()
    prompt = build_prompt(messages, context_docs)
    config = _get_generation_config(pipeline)
    return pipeline.generate(prompt, config)


def generate_reply_stream(
    messages: List[Dict[str, str]],
    context_docs: List[Dict[str, Any]],
) -> Iterable[str]:
    pipeline = _get_pipeline()
    prompt = build_prompt(messages, context_docs)
    config = _get_generation_config(pipeline)

    token_queue: "queue.Queue[str | None]" = queue.Queue()

    def streamer(token: str):
        token_queue.put(token)

    def run_generation():
        try:
            pipeline.generate(prompt, config, streamer=streamer)
        finally:
            token_queue.put(None)

    thread = threading.Thread(target=run_generation, daemon=True)
    thread.start()

    while True:
        item = token_queue.get()
        if item is None:
            break
        yield item