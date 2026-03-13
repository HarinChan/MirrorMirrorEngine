from flask import current_app
from sqlalchemy import inspect, text
from typing import Optional
import re
from datetime import datetime, timedelta

from ..model import db
from ..model.account import Account
from ..model.meeting import Meeting
from ..model.meetinginvitation import MeetingInvitation
from ..model.profile import Profile
from ..service.webex_service import WebexService

from ..service.chromadb_service import ChromaDBService

chroma_service = ChromaDBService(persist_directory="./chroma_db", collection_name="penpals_documents")
webex_service = WebexService()

def _get_primary_profile(account: Account):
    return account.profiles.first() if account else None


def _get_participant_count(meeting: Meeting) -> int:
    participant_ids = {p.id for p in meeting.participants}
    participant_ids.add(meeting.creator_id)
    return len(participant_ids)


def _meeting_has_profile(meeting: Meeting, profile: Profile) -> bool:
    if not profile:
        return False
    return meeting.creator_id == profile.id or any(p.id == profile.id for p in meeting.participants)


def _normalize_invitee_ids(classroom_ids, creator_profile_id: int):
    if classroom_ids is None:
        return [], None

    if not isinstance(classroom_ids, list):
        return None, "classroom_ids must be an array"

    normalized_ids = []
    for classroom_id in classroom_ids:
        if isinstance(classroom_id, str) and classroom_id.startswith('dummy_'):
            return None, "Cannot invite dummy classrooms. Please use real classrooms from your network."
        try:
            parsed_id = int(classroom_id)
        except (ValueError, TypeError):
            return None, "Invalid classroom_id format"

        if parsed_id == creator_profile_id:
            return None, "You cannot invite your own classroom"

        if parsed_id not in normalized_ids:
            normalized_ids.append(parsed_id)

    return normalized_ids, None


def _serialize_meeting(meeting: Meeting, profile: Optional[Profile] = None, account: Optional[Account] = None, include_invitees: bool = False):
    participant_count = _get_participant_count(meeting)
    is_creator_for_viewer = bool(
        (account and meeting.creator and meeting.creator.account_id == account.id)
        or (profile and meeting.creator_id == profile.id)
    )
    payload = {
        "id": meeting.id,
        "title": meeting.title,
        "description": meeting.description,
        "start_time": meeting.start_time.isoformat(),
        "end_time": meeting.end_time.isoformat(),
        "web_link": meeting.web_link,
        "password": meeting.password,
        "creator_name": meeting.creator.name,
        "creator_id": meeting.creator_id,
        "visibility": meeting.visibility,
        "status": meeting.status,
        "max_participants": meeting.max_participants,
        "participant_count": participant_count,
        "join_count": meeting.join_count,
        "is_creator": is_creator_for_viewer,
        "is_participant": bool(profile and _meeting_has_profile(meeting, profile)),
        "is_full": bool(meeting.max_participants and participant_count >= meeting.max_participants),
    }

    if include_invitees:
        invitations = MeetingInvitation.query.filter(
            MeetingInvitation.meeting_id == meeting.id,
            MeetingInvitation.status.in_(['pending', 'accepted'])
        ).order_by(MeetingInvitation.created_at.desc()).all()

        invited_by_receiver = {}
        for invitation in invitations:
            if invitation.receiver_profile_id in invited_by_receiver:
                continue
            invited_by_receiver[invitation.receiver_profile_id] = {
                "invitation_id": invitation.id,
                "receiver_id": invitation.receiver_profile_id,
                "receiver_name": invitation.receiver.name if invitation.receiver else "Unknown Classroom",
                "status": invitation.status,
                "can_withdraw": invitation.status == 'pending',
            }

        payload["invited_classrooms"] = list(invited_by_receiver.values())

    return payload


def _refresh_webex_if_needed(account: Account):
    if not account or not account.webex_access_token:
        return "WebEx is not connected"

    if account.webex_token_expires_at and account.webex_token_expires_at < datetime.utcnow():
        try:
            token_data = webex_service.refresh_access_token(account.webex_refresh_token)
            account.webex_access_token = token_data.get('access_token')
            account.webex_refresh_token = token_data.get('refresh_token', account.webex_refresh_token)
            expires_in = token_data.get('expires_in')
            if expires_in:
                account.webex_token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            db.session.commit()
        except Exception:
            return "Failed to refresh organizer's WebEx session"
    return None


def _ensure_meeting_created_with_webex(meeting: Meeting):
    if meeting.webex_id and meeting.web_link:
        return None

    organizer_account = meeting.creator.account
    refresh_error = _refresh_webex_if_needed(organizer_account)
    if refresh_error:
        return refresh_error

    try:
        webex_meeting = webex_service.create_meeting(
            organizer_account.webex_access_token,
            meeting.title,
            meeting.start_time,
            meeting.end_time
        )
        meeting.webex_id = webex_meeting.get('id')
        meeting.web_link = webex_meeting.get('webLink')
        meeting.password = webex_meeting.get('password')
        meeting.status = 'active'
        return None
    except Exception as e:
        return f"Failed to create WebEx meeting: {str(e)}"


def ensure_meeting_schema_columns():
    inspector = inspect(db.engine)
    try:
        meeting_columns = {col['name'] for col in inspector.get_columns('meetings')}
    except Exception:
        return

    alterations = []
    if 'visibility' not in meeting_columns:
        alterations.append("ALTER TABLE meetings ADD COLUMN visibility VARCHAR(20) NOT NULL DEFAULT 'private'")
    if 'status' not in meeting_columns:
        alterations.append("ALTER TABLE meetings ADD COLUMN status VARCHAR(30) NOT NULL DEFAULT 'pending_setup'")
    if 'max_participants' not in meeting_columns:
        alterations.append("ALTER TABLE meetings ADD COLUMN max_participants INTEGER")
    if 'join_count' not in meeting_columns:
        alterations.append("ALTER TABLE meetings ADD COLUMN join_count INTEGER NOT NULL DEFAULT 0")
    if 'created_at' not in meeting_columns:
        alterations.append("ALTER TABLE meetings ADD COLUMN created_at DATETIME")
    if 'description' not in meeting_columns:
        alterations.append("ALTER TABLE meetings ADD COLUMN description TEXT")

    for query in alterations:
        try:
            db.session.execute(text(query))
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Schema update skipped for query '{query}': {e}")

def _get_doc_similarity(doc: dict) -> float:
    if not isinstance(doc, dict):
        return 0.0
    try:
        similarity = float(doc.get("similarity", 0.0))
    except (TypeError, ValueError):
        return 0.0
    return similarity


def _is_meeting_intent_query(query: str) -> bool:
    if not isinstance(query, str):
        return False

    lowered = query.lower()
    meeting_keywords = [
        "meeting", "meet", "schedule", "call", "webex", "invite", "invitation",
        "join", "host", "time", "availability", "slot", "event"
    ]
    return any(keyword in lowered for keyword in meeting_keywords)


def _is_classroom_intent_query(query: str) -> bool:
    if not isinstance(query, str):
        return False

    lowered = query.lower()
    classroom_keywords = [
        "classroom", "class", "school", "teacher", "student", "students",
        "friend", "friends", "post", "posts"
    ]
    return any(keyword in lowered for keyword in classroom_keywords)


def _strip_model_thinking(reply: str) -> str:
    if not isinstance(reply, str) or not reply:
        return reply

    cleaned = re.sub(r"<think>.*?</think>", "", reply, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<thinking>.*?</thinking>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()            

def _build_meeting_index_document(meeting: Meeting) -> str:
    description = (meeting.description or "").strip()
    return (
        f"Meeting: {meeting.title}\n"
        f"Description: {description}\n"
        f"Host: {meeting.creator.name if meeting.creator else 'Unknown'}\n"
        f"Starts: {meeting.start_time.isoformat()}\n"
        f"Ends: {meeting.end_time.isoformat()}"
    )

def _sync_meeting_in_chroma(meeting: Meeting):
    if not meeting:
        return

    doc_id = f"meeting-{meeting.id}"
    description = (meeting.description or "").strip()
    should_index = meeting.visibility == 'public' and meeting.status != 'cancelled' and len(description) > 0

    if not should_index:
        try:
            chroma_service.delete_documents([doc_id])
        except Exception as e:
            current_app.logger.warning("Failed removing meeting from ChromaDB: %s", e)
        return

    metadata = {
        "source": "meeting",
        "meeting_id": str(meeting.id),
        "title": meeting.title,
        "description": description,
        "creator_name": meeting.creator.name if meeting.creator else "Unknown",
        "creator_id": str(meeting.creator_id),
        "start_time": meeting.start_time.isoformat(),
        "end_time": meeting.end_time.isoformat(),
        "visibility": meeting.visibility,
        "status": meeting.status,
    }

    try:
        chroma_service.delete_documents([doc_id])
    except Exception:
        pass

    try:
        chroma_service.add_documents(
            [_build_meeting_index_document(meeting)],
            metadatas=[metadata],
            ids=[doc_id]
        )
    except Exception as e:
        current_app.logger.warning("Failed indexing meeting in ChromaDB: %s", e)