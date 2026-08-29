from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_optional_user
from app.database.database import get_db
from app.models.feedback import Feedback
from app.models.message import Message
from app.models.user import User

router = APIRouter(prefix="/feedback", tags=["Feedback"])


class FeedbackRequest(BaseModel):
    message_id: int
    helpful: bool
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: int
    message_id: int
    helpful: bool
    comment: Optional[str] = None


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    payload: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    result = await db.execute(select(Message).where(Message.id == payload.message_id))
    msg = result.scalar_one_or_none()
    if msg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")

    fb = Feedback(
        message_id=payload.message_id,
        helpful=payload.helpful,
        comment=payload.comment,
    )
    db.add(fb)
    await db.flush()
    await db.refresh(fb)
    return FeedbackResponse(
        id=fb.id,
        message_id=fb.message_id,
        helpful=fb.helpful,
        comment=fb.comment,
    )
