from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from app.data.languages import is_supported


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    language: str = Field(default="en")
    crop: Optional[str] = None
    location: Optional[str] = None
    conversation_id: Optional[int] = None

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        v = v.lower().strip()
        if not is_supported(v):
            raise ValueError(f"Unsupported language code: {v}")
        return v

    @field_validator("question")
    @classmethod
    def clean_question(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Question cannot be empty")
        return v


class SourceSchema(BaseModel):
    title: str
    content: Optional[str] = None
    source: Optional[str] = None
    page: Optional[int] = None
    relevance_score: float


class QueryResponse(BaseModel):
    answer: str
    language: str
    sources: List[SourceSchema] = []
    confidence: float
    possible_issue: Optional[str] = None
    recommended_actions: List[str] = []
    precautions: List[str] = []
    when_to_contact_expert: Optional[str] = None
    conversation_id: Optional[int] = None
    message_id: Optional[int] = None
