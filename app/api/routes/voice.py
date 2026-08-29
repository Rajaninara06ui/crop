from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from app.core.logging import get_logger
from app.schemas.voice import TranscribeResponse
from app.services.speech_service import get_speech_service
from app.utils.file_utils import delete_file, save_temp_file
from app.utils.validators import validate_audio_upload

router = APIRouter(prefix="/voice", tags=["Voice"])
logger = get_logger(__name__)


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    audio: UploadFile = File(..., description="Audio file (WAV, MP3, M4A, WebM)"),
    language: Optional[str] = Form(None, description="Optional language hint (e.g. 'te', 'hi')"),
):
    audio_bytes = await validate_audio_upload(audio)
    suffix = "." + (audio.filename or "audio.wav").split(".")[-1]
    temp_path = save_temp_file(audio_bytes, suffix=suffix)

    try:
        service = get_speech_service()
        result = await service.transcribe(temp_path, language_hint=language)
        return TranscribeResponse(
            text=result.text,
            language=result.language,
            confidence=result.confidence,
        )
    except Exception as exc:
        logger.error("Transcription failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Speech transcription service is unavailable. Please try again.",
        )
    finally:
        delete_file(temp_path)
