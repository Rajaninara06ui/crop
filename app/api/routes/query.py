from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_optional_user
from app.core.config import settings
from app.core.logging import get_logger
from app.database.database import get_db
from app.models.user import User
from app.schemas.query import QueryRequest, QueryResponse
from app.services.advisory_service import AdvisoryService
from app.services.history_service import HistoryService

router = APIRouter(tags=["Advisory"])
logger = get_logger(__name__)


@router.post("/query", response_model=QueryResponse)
async def query_advisory(
    payload: QueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    if not settings.ALLOW_ANONYMOUS_QUERY and current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to use the advisory service.",
        )

    advisory = AdvisoryService()
    history = HistoryService(db)

    try:
        result = await advisory.process(
            question=payload.question,
            language=payload.language,
            crop=payload.crop,
            location=payload.location,
        )
    except Exception as exc:
        logger.error("Advisory pipeline failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI advisory service is currently unavailable. Please try again.",
        )

    try:
        user_id = current_user.id if current_user else None
        conv_id = payload.conversation_id

        if conv_id is None:
            title = payload.question[:100]
            conv = await history.create_conversation(
                user_id=user_id, language=payload.language, title=title
            )
            conv_id = conv.id

        await history.add_message(
            conversation_id=conv_id,
            role="user",
            content=payload.question,
            language=payload.language,
        )
        asst_msg = await history.add_message(
            conversation_id=conv_id,
            role="assistant",
            content=result["answer"],
            language=payload.language,
        )
        result["conversation_id"] = conv_id
        result["message_id"] = asst_msg.id
    except Exception as exc:
        logger.warning("Failed to save conversation: %s", exc)

    return QueryResponse(**result)
