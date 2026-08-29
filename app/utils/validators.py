from __future__ import annotations
from pathlib import Path
from typing import Optional
from fastapi import HTTPException, UploadFile, status
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
ALLOWED_AUDIO_TYPES = {
    "audio/wav", "audio/mpeg", "audio/mp4", "audio/x-m4a",
    "audio/webm", "audio/ogg", "audio/x-wav", "video/webm",
}
ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".webm", ".ogg", ".mp4"}


def _mb_to_bytes(mb: int) -> int:
    return mb * 1024 * 1024


async def validate_image_upload(file: UploadFile) -> bytes:
    max_bytes = _mb_to_bytes(settings.MAX_IMAGE_SIZE_MB)
    data = await file.read()
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image exceeds {settings.MAX_IMAGE_SIZE_MB} MB limit.",
        )
    content_type = file.content_type or ""
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image type. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}",
        )
    return data


async def validate_audio_upload(file: UploadFile) -> bytes:
    max_bytes = _mb_to_bytes(settings.MAX_AUDIO_SIZE_MB)
    data = await file.read()
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Audio exceeds {settings.MAX_AUDIO_SIZE_MB} MB limit.",
        )
    content_type = file.content_type or ""
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if content_type not in ALLOWED_AUDIO_TYPES and ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported audio type. Allowed extensions: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}",
        )
    if len(data) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audio file is empty.")
    return data
