"""
Chat API endpoints.
"""

from flask import Blueprint, jsonify, request

from ..service.chromadb_service import ChromaDBService
from ..service.fasterwhisper_service import TranscriptionInputError, transcribe_uploaded_file
from ..service.openvino_service import generate_reply

import json
import re 

_CLASSROOM_TAG_RE = re.compile(r'<classroom\s+id="[^"]+"\s*/>')

chat_bp = Blueprint('chat', __name__)

chroma_service = ChromaDBService(persist_directory="./chroma_db", collection_name="penpals_documents")


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

        hotwords = (request.form.get('hotwords') or '').strip()
        transcript = transcribe_uploaded_file(audio_file, hotwords)
        return jsonify({
            "status": "success",
            "transcript": transcript,
            "engine": "faster-whisper",
        }), 200
    except TranscriptionInputError as e:
        return jsonify({"status": "error", "message": str(e)}), e.status_code
    except RuntimeError as e:
        return jsonify({
            "status": "error",
            "message": f"Local transcription unavailable: {e}. Install faster-whisper and ffmpeg."
        }), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500