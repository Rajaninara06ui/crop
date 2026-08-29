from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


class SuccessResponse(BaseModel):
    success: bool = True
    data: Any = None


class HealthResponse(BaseModel):
    status: str
    database: str
    rag: str
    ai: str
    version: str
