from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class TranscribeResponse(BaseModel):
    text: str
    language: str
    confidence: float
