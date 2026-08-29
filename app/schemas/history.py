from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class ConversationItem(BaseModel):
    id: int
    date: datetime
    question: str
    language: str
    answer_preview: str

    model_config = {"from_attributes": True}


class MessageSchema(BaseModel):
    id: int
    role: str
    content: str
    language: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetail(BaseModel):
    id: int
    title: Optional[str] = None
    language: str
    created_at: datetime
    messages: List[MessageSchema] = []

    model_config = {"from_attributes": True}


class HistoryListResponse(BaseModel):
    items: List[ConversationItem]
    total: int
    page: int
    page_size: int
