"""
Chat API endpoints.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, jwt_manager

from ..service.chromadb_service import ChromaDBService
from ..service.openvino_service import generate_reply

import os
import threading
import mimetypes
import base64
import importlib
from pathlib import Path
import json
import tempfile
import re 

_CLASSROOM_TAG_RE = re.compile(r'<classroom\s+id="[^"]+"\s*/>')

WhisperModel = None

chat_bp = Blueprint('chat', __name__)

chroma_service = ChromaDBService(persist_directory="./chroma_db", collection_name="penpals_documents")

TRANSCRIBE_MAX_AUDIO_BYTES = int(os.getenv('TRANSCRIBE_MAX_AUDIO_BYTES', str(20 * 1024 * 1024)))
FASTER_WHISPER_MODEL_SIZE = os.getenv('FASTER_WHISPER_MODEL_SIZE', 'base')
FASTER_WHISPER_DEVICE = os.getenv('FASTER_WHISPER_DEVICE', 'cpu')
FASTER_WHISPER_COMPUTE_TYPE = os.getenv('FASTER_WHISPER_COMPUTE_TYPE', 'int8')
FASTER_WHISPER_BEAM_SIZE = int(os.getenv('FASTER_WHISPER_BEAM_SIZE', '1'))

_FASTER_WHISPER_MODEL = None
_FASTER_WHISPER_MODEL_LOCK = threading.Lock()


def _extract_context_classroom_ids(context_docs, limit: int = 3):
    ids = []
    if not isinstance(context_docs, list):
        return ids

    for doc in context_docs:
        metadata = doc.get("metadata", {}) if isinstance(doc, dict) else {}
        if isinstance(metadata, dict):
            classroom_id = metadata.get("classroom_id")
            if classroom_id:
                classroom_id = str(classroom_id)
                if classroom_id not in ids:
                    ids.append(classroom_id)
        if len(ids) >= limit:
            break
    return ids

def _inject_classroom_tags(reply: str, context_docs, limit: int = 3) -> str:
    if not isinstance(reply, str) or not reply:
        return reply
    if _CLASSROOM_TAG_RE.search(reply):
        return reply

    classroom_ids = _extract_context_classroom_ids(context_docs, limit)
    if not classroom_ids:
        return reply

    tags = "\n".join(f'<classroom id="{cid}"/>' for cid in classroom_ids)
    return reply.rstrip() + "\n" + tags




def _guess_uploaded_mime_type(file_storage) -> str:
    uploaded_mime = (getattr(file_storage, 'mimetype', '') or '').strip().lower()
    if uploaded_mime.startswith('audio/') or uploaded_mime.startswith('video/'):
        return uploaded_mime

    guessed, _ = mimetypes.guess_type(getattr(file_storage, 'filename', '') or '')
    if guessed:
        return guessed
    return 'audio/webm'

def _extract_transcript_text(vibevoice_content):
    if isinstance(vibevoice_content, str):
        content = vibevoice_content.strip()
        if not content:
            return ""

        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                parts = []
                for item in parsed:
                    if isinstance(item, dict):
                        part = item.get('Content') or item.get('content')
                        if isinstance(part, str) and part.strip():
                            parts.append(part.strip())
                if parts:
                    return " ".join(parts)
        except Exception:
            pass

        return content

    if isinstance(vibevoice_content, list):
        parts = []
        for item in vibevoice_content:
            if isinstance(item, dict):
                part = item.get('Content') or item.get('content')
                if isinstance(part, str) and part.strip():
                    parts.append(part.strip())
        return " ".join(parts)

    return str(vibevoice_content or "").strip()

def _audio_suffix_from_mime(mime_type: str) -> str:
    mime_to_suffix = {
        'audio/wav': '.wav',
        'audio/x-wav': '.wav',
        'audio/mpeg': '.mp3',
        'audio/mp4': '.m4a',
        'audio/flac': '.flac',
        'audio/ogg': '.ogg',
        'audio/webm': '.webm',
        'video/webm': '.webm',
        'video/mp4': '.mp4',
    }
    return mime_to_suffix.get((mime_type or '').lower(), '.webm')

def _get_faster_whisper_model():
    global WhisperModel
    if WhisperModel is None:
        try:
            faster_whisper_module = importlib.import_module('faster_whisper')
            WhisperModel = faster_whisper_module.WhisperModel
        except Exception as import_error:
            raise RuntimeError(f"faster-whisper is not installed: {import_error}")

    global _FASTER_WHISPER_MODEL
    with _FASTER_WHISPER_MODEL_LOCK:
        if _FASTER_WHISPER_MODEL is None:
            _FASTER_WHISPER_MODEL = WhisperModel(
                FASTER_WHISPER_MODEL_SIZE,
                device=FASTER_WHISPER_DEVICE,
                compute_type=FASTER_WHISPER_COMPUTE_TYPE,
            )
    return _FASTER_WHISPER_MODEL

def _transcribe_with_faster_whisper(audio_bytes: bytes, mime_type: str, hotwords: str = '') -> str:
    model = _get_faster_whisper_model()
    suffix = _audio_suffix_from_mime(mime_type)
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name

        initial_prompt = f"Important context terms: {hotwords}" if hotwords else None
        segments, _ = model.transcribe(
            temp_path,
            beam_size=FASTER_WHISPER_BEAM_SIZE,
            vad_filter=True,
            initial_prompt=initial_prompt,
        )
        transcript = " ".join(segment.text.strip() for segment in segments if segment.text and segment.text.strip()).strip()
        if not transcript:
            raise RuntimeError("faster-whisper returned an empty transcript")
        return transcript
    finally:
        if temp_path:
            try:
                os.remove(temp_path)
            except OSError:
                pass

@chat_bp.route('/api/chat', methods=['POST'])
def chat():
    """
    RAG-augmented chat endpoint using OpenVINO GenAI and ChromaDB.
    Expected JSON format:
    {
        "message": "user message",
        "history": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}],
        "n_result": 5
    }
    """

    try:
        data = request.json or {}
        message = data.get('message', '')
        history = data.get('history', [])
        n_results = data.get('n_results', 5)

        if not isinstance(message, str) or len(message.strip()) == 0:
            return jsonify({"status": "error", "message": "Missing or empty 'message' field"}), 400
        
        if not isinstance(history, list):
            return jsonify({"status": "error", "message": "'history' must be a list"}), 400
        
        if not isinstance(n_results, int) or n_results <= 0:
            n_results = 5

        query_result = chroma_service.query_documents(message, n_results)
        context_docs = []
        if isinstance(query_result, dict) and query_result.get('status') == 'success':
            context_docs = query_result.get('results', [])

        messages = history + [{"role": "user", "content": message}]
        reply = generate_reply(messages, context_docs)
        reply = _inject_classroom_tags(reply, context_docs, 3)

        return jsonify({
            "status": "success",
            "reply": reply,
            "context": context_docs
        }), 200
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
@chat_bp.route('/api/chat/transcribe', methods=['POST'])
def transcribe_chat_audio():
    """
    Transcribe uploaded audio using local faster-whisper.
    Expected multipart/form-data:
        - audio: uploaded audio/video file bob
        - hotwords: optional comma-separated context words
    """
    try:
        audio_file = request.files.get('audio') or request.files.get('file') or request.files.get('recording')
        if audio_file is None:
            return jsonify({
                "status": "error",
                "message": "Missing 'audio' file in form data",
                "received_file_keys": list(request.files.keys()),
                "content_type": request.content_type,
            }), 400

        audio_bytes = audio_file.read()
        if not audio_bytes:
            return jsonify({"status": "error", "message": "Uploaded audio file is empty"}), 400
        if len(audio_bytes) > TRANSCRIBE_MAX_AUDIO_BYTES:
            return jsonify({
                "status": "error",
                "message": f"Audio file too large. Max size is {TRANSCRIBE_MAX_AUDIO_BYTES} bytes"
            }), 413

        hotwords = (request.form.get('hotwords') or '').strip()
        mime_type = _guess_uploaded_mime_type(audio_file)
        transcript = _transcribe_with_faster_whisper(audio_bytes, mime_type, hotwords)
        return jsonify({
            "status": "success",
            "transcript": transcript,
            "engine": "faster-whisper",
        }), 200
    except RuntimeError as e:
        return jsonify({
            "status": "error",
            "message": f"Local transcription unavailable: {e}. Install faster-whisper and ffmpeg."
        }), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500