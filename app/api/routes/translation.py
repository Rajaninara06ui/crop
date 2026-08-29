from __future__ import annotations
from fastapi import APIRouter, HTTPException, status
from app.core.logging import get_logger
from app.schemas.translation import TranslateRequest, TranslateResponse
from app.services.translation_service import get_translation_service

router = APIRouter(prefix="/translate", tags=["Translation"])
logger = get_logger(__name__)


@router.post("", response_model=TranslateResponse)
async def translate_text(payload: TranslateRequest):
    try:
        service = get_translation_service()
        translated = await service.translate(
            text=payload.text,
            source_lang=payload.source_language,
            target_lang=payload.target_language,
        )
        return TranslateResponse(
            translated_text=translated,
            source_language=payload.source_language,
            target_language=payload.target_language,
        )
    except Exception as exc:
        logger.error("Translation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Translation service is currently unavailable.",
        )
