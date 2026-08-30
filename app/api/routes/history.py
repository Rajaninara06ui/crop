from __future__ import annotations
from typing import Any, List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_optional_user
from app.database.database import get_db
from app.database.mongodb import MongoDBService
from app.models.user import User
from app.schemas.history import ConversationDetail, HistoryListResponse
from app.services.history_service import HistoryService

router = APIRouter(prefix="/history", tags=["History"])


@router.get("", response_model=List[dict])
async def list_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    List conversation history. Returns list of HistoryItem objects directly for frontend compatibility.
    """
    # 1. Fetch from MongoDB
    try:
        user_id = str(current_user.id) if current_user else None
        mongo_items = await MongoDBService.list_conversations(user_id=user_id, limit=page_size)
        if mongo_items:
            return mongo_items
    except Exception:
        pass

    # 2. Fallback to SQL DB
    service = HistoryService(db)
    user_id_int = current_user.id if current_user else None
    items, _ = await service.list_conversations(
        user_id=user_id_int, page=page, page_size=page_size, search=search
    )
    return [
        {
            "id": str(item.id),
            "question": item.question,
            "answer_preview": item.answer_preview,
            "language": item.language,
            "timestamp": item.date.isoformat(),
        }
        for item in items
    ]


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Get full conversation detail."""
    service = HistoryService(db)
    user_id_int = current_user.id if current_user else None
    try:
        conv_id_int = int(conversation_id)
        detail = await service.get_conversation_detail(conv_id_int, user_id_int)
        if detail:
            return detail
    except ValueError:
        pass

    # Try MongoDB
    mongo_items = await MongoDBService.list_conversations(limit=100)
    for c in mongo_items:
        if c.get("id") == conversation_id:
            return c

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Delete a conversation."""
    await MongoDBService.delete_conversation(conversation_id)
    try:
        service = HistoryService(db)
        user_id_int = current_user.id if current_user else None
        await service.delete_conversation(int(conversation_id), user_id_int)
    except Exception:
        pass
    return None
