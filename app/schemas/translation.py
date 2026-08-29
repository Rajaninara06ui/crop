from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from app.data.languages import is_supported


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    source_language: str = Field(default="en")
    target_language: str

    @field_validator("source_language", "target_language")
    @classmethod
    def validate_lang(cls, v: str) -> str:
        v = v.lower().strip()
        if not is_supported(v):
            raise ValueError(f"Unsupported language: {v}")
        return v


class TranslateResponse(BaseModel):
    translated_text: str
    source_language: str
    target_language: str
