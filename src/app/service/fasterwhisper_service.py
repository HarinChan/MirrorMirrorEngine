"""Local faster-whisper transcription service."""

import importlib
import mimetypes
import os
import tempfile
import threading


TRANSCRIBE_MAX_AUDIO_BYTES = int(os.getenv("TRANSCRIBE_MAX_AUDIO_BYTES", str(20 * 1024 * 1024)))
FASTER_WHISPER_MODEL_SIZE = os.getenv("FASTER_WHISPER_MODEL_SIZE", "base")
FASTER_WHISPER_DEVICE = os.getenv("FASTER_WHISPER_DEVICE", "cpu")
FASTER_WHISPER_COMPUTE_TYPE = os.getenv("FASTER_WHISPER_COMPUTE_TYPE", "int8")
FASTER_WHISPER_BEAM_SIZE = int(os.getenv("FASTER_WHISPER_BEAM_SIZE", "1"))

WhisperModel = None
_FASTER_WHISPER_MODEL = None
_FASTER_WHISPER_MODEL_LOCK = threading.Lock()


class TranscriptionInputError(Exception):
    """Raised when an uploaded file cannot be transcribed due to input issues."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def _guess_uploaded_mime_type(file_storage) -> str:
    uploaded_mime = (getattr(file_storage, "mimetype", "") or "").strip().lower()
    if uploaded_mime.startswith("audio/") or uploaded_mime.startswith("video/"):
        return uploaded_mime

    guessed, _ = mimetypes.guess_type(getattr(file_storage, "filename", "") or "")
    if guessed:
        return guessed
    return "audio/webm"


def _audio_suffix_from_mime(mime_type: str) -> str:
    mime_to_suffix = {
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/mpeg": ".mp3",
        "audio/mp4": ".m4a",
        "audio/flac": ".flac",
        "audio/ogg": ".ogg",
        "audio/webm": ".webm",
        "video/webm": ".webm",
        "video/mp4": ".mp4",
    }
    return mime_to_suffix.get((mime_type or "").lower(), ".webm")


def _get_faster_whisper_model():
    global WhisperModel
    if WhisperModel is None:
        try:
            faster_whisper_module = importlib.import_module("faster_whisper")
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


def transcribe_audio_bytes(audio_bytes: bytes, mime_type: str, hotwords: str = "") -> str:
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
        transcript = " ".join(
            segment.text.strip() for segment in segments if segment.text and segment.text.strip()
        ).strip()
        if not transcript:
            raise RuntimeError("faster-whisper returned an empty transcript")
        return transcript
    finally:
        if temp_path:
            try:
                os.remove(temp_path)
            except OSError:
                pass


def transcribe_uploaded_file(audio_file, hotwords: str = "") -> str:
    audio_bytes = audio_file.read()
    if not audio_bytes:
        raise TranscriptionInputError("Uploaded audio file is empty", status_code=400)

    if len(audio_bytes) > TRANSCRIBE_MAX_AUDIO_BYTES:
        raise TranscriptionInputError(
            f"Audio file too large. Max size is {TRANSCRIBE_MAX_AUDIO_BYTES} bytes",
            status_code=413,
        )

    mime_type = _guess_uploaded_mime_type(audio_file)
    return transcribe_audio_bytes(audio_bytes, mime_type, hotwords)
