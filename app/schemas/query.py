from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from app.data.languages import is_supported


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    language: str = Field(default="en")
    crop: Optional[str] = None
    location: Optional[str] = None
    conversation_id: Optional[str] = None

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


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    language: str = Field(default="en")
    farmer_id: Optional[str] = None
    conversation_id: Optional[str] = None

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        v = v.lower().strip()
        if not is_supported(v):
            # fallback gracefully to en
            return "en"
        return v


class SourceSchema(BaseModel):
    title: str
    content: Optional[str] = None
    source: Optional[str] = None
    page: Optional[int] = None
    relevance_score: float = 0.90


class QueryResponse(BaseModel):
    id: Optional[str] = None
    answer: str
    language: str
    sources: List[SourceSchema] = []
    confidence: float
    possible_issue: Optional[str] = None
    explanation: Optional[str] = None
    recommended_actions: List[str] = []
    precautions: List[str] = []
    expert_advice: Optional[str] = None
    when_to_contact_expert: Optional[str] = None
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ChatData(BaseModel):
    intent: Optional[str] = "crop_advisory"
    crop: Optional[str] = None
    possible_issue: Optional[str] = None
    recommendation: Optional[str] = None
    follow_up_questions: List[str] = []
    precautions: List[str] = []
    sources: List[str] = []


class BackendChatResponse(BaseModel):
    success: bool = True
    language: str = "en"
    message: str
    conversation_id: str
    data: ChatData
