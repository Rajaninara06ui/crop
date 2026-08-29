from __future__ import annotations
import io
from typing import Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from PIL import Image
from app.core.logging import get_logger
from app.schemas.disease import DiseaseDetectionResponse
from app.services.disease_service import DiseaseService
from app.utils.validators import validate_image_upload

router = APIRouter(prefix="/disease", tags=["Disease Detection"])
logger = get_logger(__name__)

_disease_service = None


def _get_disease_service() -> DiseaseService:
    global _disease_service
    if _disease_service is None:
        _disease_service = DiseaseService()
    return _disease_service


@router.post("/detect", response_model=DiseaseDetectionResponse)
async def detect_disease(
    image: UploadFile = File(..., description="Crop image (JPEG, PNG, WebP)"),
    crop: Optional[str] = Form(None, description="Crop name hint (e.g. tomato, paddy)"),
    language: Optional[str] = Form("en", description="Response language code"),
):
    image_bytes = await validate_image_upload(image)

    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        max_dim = 1024
        if max(img.size) > max_dim:
            img.thumbnail((max_dim, max_dim))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            image_bytes = buf.getvalue()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot read image: {exc}",
        )

    try:
        service = _get_disease_service()
        result = service.detect(image_bytes, crop_hint=crop)
        return DiseaseDetectionResponse(
            crop=result.crop,
            possible_disease=result.possible_disease,
            confidence=result.confidence,
            symptoms=result.symptoms,
            recommended_treatment=result.recommended_treatment,
            prevention=result.prevention,
            warning=result.warning,
            is_demo=result.is_demo,
        )
    except Exception as exc:
        logger.error("Disease detection failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Disease detection service is unavailable.",
        )
