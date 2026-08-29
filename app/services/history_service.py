from __future__ import annotations
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.logging import get_logger
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.history import ConversationDetail, ConversationItem, MessageSchema

logger = get_logger(__name__)


class HistoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_conversation(
        self,
        user_id: Optional[int],
        language: str,
        title: Optional[str] = None,
    ) -> Conversation:
        conv = Conversation(user_id=user_id, language=language, title=title)
        self.db.add(conv)
        await self.db.flush()
        await self.db.refresh(conv)
        return conv

    async def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        language: str,
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            language=language,
        )
        self.db.add(msg)
        await self.db.flush()
        await self.db.refresh(msg)
        return msg

    async def list_conversations(
        self,
        user_id: Optional[int],
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
    ) -> tuple[List[ConversationItem], int]:
        base_q = select(Conversation)
        if user_id is not None:
            base_q = base_q.where(Conversation.user_id == user_id)

        if search:
            base_q = base_q.join(Message).where(Message.content.ilike(f"%{search}%"))

        total_q = select(func.count()).select_from(base_q.subquery())
        total_result = await self.db.execute(total_q)
        total = total_result.scalar() or 0

        q = (
            base_q
            .order_by(Conversation.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .options(selectinload(Conversation.messages))
        )
        result = await self.db.execute(q)
        conversations = result.scalars().all()

        items = []
        for conv in conversations:
            user_msgs = [m for m in conv.messages if m.role == "user"]
            asst_msgs = [m for m in conv.messages if m.role == "assistant"]
            first_q = user_msgs[0].content if user_msgs else (conv.title or "")
            first_a = asst_msgs[0].content if asst_msgs else ""
            items.append(
                ConversationItem(
                    id=conv.id,
                    date=conv.created_at,
                    question=first_q[:200],
                    language=conv.language,
                    answer_preview=first_a[:100],
                )
            )
        return items, total

    async def get_conversation_detail(self, conversation_id: int, user_id: Optional[int]) -> Optional[ConversationDetail]:
        q = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        result = await self.db.execute(q)
        conv = result.scalar_one_or_none()
        if conv is None:
            return None
        if user_id and conv.user_id and conv.user_id != user_id:
            return None
        return ConversationDetail(
            id=conv.id,
            title=conv.title,
            language=conv.language,
            created_at=conv.created_at,
            messages=[
                MessageSchema(
                    id=m.id,
                    role=m.role,
                    content=m.content,
                    language=m.language,
                    created_at=m.created_at,
                )
                for m in conv.messages
            ],
        )

    async def delete_conversation(self, conversation_id: int, user_id: Optional[int]) -> bool:
        q = select(Conversation).where(Conversation.id == conversation_id)
        result = await self.db.execute(q)
        conv = result.scalar_one_or_none()
        if conv is None:
            return False
        if user_id and conv.user_id and conv.user_id != user_id:
            return False
        await self.db.delete(conv)
        await self.db.flush()
        return True
