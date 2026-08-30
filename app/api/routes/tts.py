from __future__ import annotations
import base64
from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator
from app.core.logging import get_logger
from app.data.languages import is_supported
from app.services.tts_service import get_tts_service

router = APIRouter(prefix="/tts", tags=["Text-to-Speech"])
logger = get_logger(__name__)


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    language: str = Field(default="en")

    @field_validator("language")
    @classmethod
    def validate_lang(cls, v: str) -> str:
        v = v.lower().strip()
        if not is_supported(v):
            return "en"
        return v


@router.post("")
async def text_to_speech(payload: TTSRequest, request: Request):
    """
    Synthesize text into natural Indian language speech using Sarvam Bulbul / TTS providers.
    Supports audio binary response or JSON with base64 audio.
    """
    try:
        service = get_tts_service()
        audio_bytes = await service.synthesize(payload.text, payload.language)
        
        # If client accepts JSON or requests json format
        accept_header = request.headers.get("accept", "")
        if "application/json" in accept_header:
            b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
            data_url = f"data:{service.content_type};base64,{b64_audio}"
            return {
                "audio_base64": b64_audio,
                "audio_url": data_url,
                "language": payload.language,
            }

        return Response(
            content=audio_bytes,
            media_type=service.content_type,
            headers={"Content-Disposition": "inline; filename=speech.wav"},
        )
    except Exception as exc:
        logger.error("TTS failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Text-to-speech service is currently unavailable.",
        )
