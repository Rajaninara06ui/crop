from __future__ import annotations
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
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
            raise ValueError(f"Unsupported language: {v}")
        return v


@router.post("")
async def text_to_speech(payload: TTSRequest):
    try:
        service = get_tts_service()
        audio_bytes = await service.synthesize(payload.text, payload.language)
        return Response(
            content=audio_bytes,
            media_type=service.content_type,
            headers={"Content-Disposition": "inline; filename=response.mp3"},
        )
    except Exception as exc:
        logger.error("TTS failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Text-to-speech service is currently unavailable.",
        )
