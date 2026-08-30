from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_optional_user
from app.core.config import settings
from app.core.logging import get_logger
from app.database.database import get_db
from app.database.mongodb import MongoDBService
from app.models.user import User
from app.schemas.query import (
    BackendChatResponse,
    ChatData,
    ChatRequest,
    QueryRequest,
    QueryResponse,
)
from app.services.advisory_service import AdvisoryService
from app.services.history_service import HistoryService

router = APIRouter(tags=["Advisory"])
logger = get_logger(__name__)


@router.post("/chat", response_model=BackendChatResponse)
async def chat_advisory(payload: ChatRequest):
    """
    Direct endpoint matching frontend `sendQuery` call.
    Receives farmer message and returns structured advisory in requested language.
    """
    advisory = AdvisoryService()

    try:
        result = await advisory.process(
            question=payload.message,
            language=payload.language,
        )
    except Exception as exc:
        logger.error("Chat advisory processing error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI advisory service is currently unavailable. Please try again.",
        )

    # Save to MongoDB
    conv_id = payload.conversation_id
    try:
        if not conv_id:
            conv = await MongoDBService.create_conversation(
                user_id=payload.farmer_id or "anonymous-farmer",
                language=payload.language,
                title=payload.message[:80],
            )
            conv_id = conv["id"]

        await MongoDBService.add_message(
            conversation_id=conv_id,
            role="user",
            content=payload.message,
            language=payload.language,
        )
        await MongoDBService.add_message(
            conversation_id=conv_id,
            role="assistant",
            content=result["answer"],
            language=payload.language,
            advisory_data=result,
        )
    except Exception as exc:
        logger.warning("MongoDB record save notice: %s", exc)

    source_titles = [s.title for s in result.get("sources", [])]
    actions_text = "\n".join(result.get("recommended_actions", []))

    follow_ups = [
        "Are other nearby plants showing similar symptoms?",
        "How frequently are you irrigating the crop?"
    ]
    if payload.language == "te":
        follow_ups = [
            "పక్కనున్న ఇతర మొక్కలకు కూడా ఇలాంటి లక్షణాలు కనిపిస్తున్నాయా?",
            "మీరు పంటకు ఎన్ని రోజులకు ఒకసారి నీరు పెడుతున్నారు?"
        ]
    elif payload.language == "hi":
        follow_ups = [
            "क्या आसपास के अन्य पौधों में भी ऐसे लक्षण दिखाई दे रहे हैं?",
            "आप कितने दिनों के अंतराल पर फसल की सिंचाई कर रहे हैं?"
        ]

    return BackendChatResponse(
        success=True,
        language=payload.language,
        message=result["answer"],
        conversation_id=conv_id or "conv-default",
        data=ChatData(
            intent="crop_advisory",
            crop=None,
            possible_issue=result.get("possible_issue") or ("వ్యవసాయ సలహా మార్గదర్శకం" if payload.language == "te" else "Crop Advisory Guidance"),
            recommendation=actions_text or result["answer"],
            follow_up_questions=follow_ups,
            precautions=result.get("precautions", []),
            sources=source_titles if source_titles else (["వ్యవసాయ విజ్ఞాన సమాచారం"] if payload.language == "te" else ["Agricultural Knowledge Base"]),
        ),
    )


@router.post("/query", response_model=QueryResponse)
async def query_advisory(
    payload: QueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Standard RAG Query endpoint returning detailed agricultural advice.
    """
    if not settings.ALLOW_ANONYMOUS_QUERY and current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to use the advisory service.",
        )

    advisory = AdvisoryService()

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

    conv_id = payload.conversation_id
    try:
        if not conv_id:
            m_conv = await MongoDBService.create_conversation(
                user_id=str(current_user.id) if current_user else "anonymous",
                language=payload.language,
                title=payload.question[:80],
            )
            conv_id = m_conv["id"]

        await MongoDBService.add_message(
            conversation_id=str(conv_id),
            role="user",
            content=payload.question,
            language=payload.language,
        )
        await MongoDBService.add_message(
            conversation_id=str(conv_id),
            role="assistant",
            content=result["answer"],
            language=payload.language,
            advisory_data=result,
        )
        result["conversation_id"] = str(conv_id)
        result["id"] = str(conv_id)
        result["explanation"] = result.get("answer")
        result["expert_advice"] = result.get("when_to_contact_expert")
    except Exception as exc:
        logger.warning("Failed to save conversation in MongoDB: %s", exc)

    return QueryResponse(**result)
