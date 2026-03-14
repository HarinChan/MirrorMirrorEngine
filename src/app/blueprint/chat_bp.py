"""
Chat API endpoints.
"""

from flask import Blueprint, jsonify, request
import json
import re 

from ..service.chromadb_service import ChromaDBService
from ..service.fasterwhisper_service import TranscriptionInputError, transcribe_uploaded_file
from ..service.openvino_service import generate_reply
from ..service.meeting_helper import _is_classroom_intent_query, _get_doc_similarity, _is_meeting_intent_query, _strip_model_thinking

_CLASSROOM_TAG_RE = re.compile(r'<classroom\s+id="[^"]+"\s*/>')
_MEETING_TAG_RE = re.compile(r'<meeting\s+id="[^"]+"\s*/>')
CLASSROOM_WIDGET_SIMILARITY_THRESHOLD = 0.12
CLASSROOM_WIDGET_NON_INTENT_SIMILARITY_THRESHOLD = 0.35
MEETING_WIDGET_SIMILARITY_THRESHOLD = 0.12
MEETING_WIDGET_NON_INTENT_SIMILARITY_THRESHOLD = 0.35

chat_bp = Blueprint('chat', __name__)

chroma_service = ChromaDBService(persist_directory="./chroma_db", collection_name="penpals_documents")

def _extract_context_classroom_ids(context_docs, limit: int = 3, user_query: str = ""):
    ids = []
    if not isinstance(context_docs, list):
        return ids
    
    is_classroom_query = _is_classroom_intent_query(user_query)
    required_similarity = (
        CLASSROOM_WIDGET_SIMILARITY_THRESHOLD
        if is_classroom_query
        else CLASSROOM_WIDGET_NON_INTENT_SIMILARITY_THRESHOLD
    )

    for doc in context_docs:
        if not isinstance(doc, dict):
            continue

        if _get_doc_similarity(doc) < required_similarity:
            continue
        metadata = doc.get("metadata", {}) if isinstance(doc, dict) else {}
        if isinstance(metadata, dict):
            if metadata.get("source") != "post":
                continue
            classroom_id = metadata.get("profile_id") or metadata.get("classroom_id")
            if classroom_id:
                classroom_id = str(classroom_id)
                if classroom_id not in ids:
                    ids.append(classroom_id)
        if len(ids) >= limit:
            break
    return ids

def _inject_classroom_tags(reply: str, context_docs, limit: int = 3, user_query: str = "") -> str:
    if not isinstance(reply, str) or not reply:
        return reply
    if _CLASSROOM_TAG_RE.search(reply):
        return reply

    classroom_ids = _extract_context_classroom_ids(context_docs, limit, user_query)
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

def _extract_context_meeting_ids(context_docs, limit: int = 3, user_query: str = ""):
    meeting_ids = []
    if not isinstance(context_docs, list):
        return meeting_ids

    is_meeting_query = _is_meeting_intent_query(user_query)
    required_similarity = (
        MEETING_WIDGET_SIMILARITY_THRESHOLD
        if is_meeting_query
        else MEETING_WIDGET_NON_INTENT_SIMILARITY_THRESHOLD
    )

    for doc in context_docs:
        if not isinstance(doc, dict):
            continue

        if _get_doc_similarity(doc) < required_similarity:
            continue

        metadata = doc.get("metadata", {})
        if not isinstance(metadata, dict):
            continue

        if metadata.get("source") != "meeting":
            continue

        meeting_id = metadata.get("meeting_id")
        if meeting_id:
            meeting_id = str(meeting_id)
            if meeting_id not in meeting_ids:
                meeting_ids.append(meeting_id)
        if len(meeting_ids) >= limit:
            break

    return meeting_ids


def _inject_meeting_tags(reply: str, context_docs, limit: int = 3, user_query: str = "") -> str:
    if not isinstance(reply, str) or not reply:
        return reply
    if _MEETING_TAG_RE.search(reply):
        return reply

    meeting_ids = _extract_context_meeting_ids(context_docs, limit, user_query)
    if not meeting_ids:
        return reply

    tags = "\n".join(f'<meeting id="{mid}"/>' for mid in meeting_ids)
    return reply.rstrip() + "\n" + tags

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
        meeting_query_result = chroma_service.query_documents(
            message,
            n_results,
            where={"source": "meeting", "visibility": "public"}
        )
        context_docs = []
        if isinstance(query_result, dict) and query_result.get('status') == 'success':
            context_docs = query_result.get('results', [])

        meeting_context_docs = []
        if isinstance(meeting_query_result, dict) and meeting_query_result.get('status') == 'success':
            meeting_context_docs = meeting_query_result.get('results', [])

        merged_docs = []
        seen_doc_ids = set()
        for source_docs in [context_docs, meeting_context_docs]:
            for doc in source_docs:
                if not isinstance(doc, dict):
                    continue
                doc_id = str(doc.get('id', ''))
                if doc_id and doc_id in seen_doc_ids:
                    continue
                if doc_id:
                    seen_doc_ids.add(doc_id)
                merged_docs.append(doc)

        messages = history + [{"role": "user", "content": message}]
        reply = generate_reply(messages, merged_docs)
        reply = _strip_model_thinking(reply)
        reply = _inject_classroom_tags(reply, merged_docs, 3, message)
        reply = _inject_meeting_tags(reply, merged_docs, 3, message)

        return jsonify({
            "status": "success",
            "reply": reply,
            "context": merged_docs
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