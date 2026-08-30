from __future__ import annotations
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_mongo_client: Optional[AsyncIOMotorClient] = None
_mongo_db: Optional[AsyncIOMotorDatabase] = None
_in_memory_db: Dict[str, List[Dict[str, Any]]] = {
    "users": [],
    "conversations": [],
    "messages": [],
    "feedback": [],
    "knowledge": [],
}


def get_mongo_client() -> Optional[AsyncIOMotorClient]:
    global _mongo_client
    if _mongo_client is None:
        try:
            _mongo_client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                serverSelectionTimeoutMS=2000,
            )
        except Exception as exc:
            logger.warning("Could not initialize MongoDB client: %s", exc)
    return _mongo_client


def get_mongo_db() -> Optional[AsyncIOMotorDatabase]:
    global _mongo_db
    if _mongo_db is None:
        client = get_mongo_client()
        if client is not None:
            _mongo_db = client[settings.MONGODB_DB_NAME]
    return _mongo_db


async def check_mongodb_connection() -> bool:
    try:
        client = get_mongo_client()
        if client is not None:
            await client.admin.command("ping")
            return True
    except Exception as exc:
        logger.debug("MongoDB connection check: %s", exc)
    return False


class MongoDBService:
    @classmethod
    async def create_conversation(
        cls,
        user_id: Optional[str],
        language: str,
        title: Optional[str] = None,
    ) -> Dict[str, Any]:
        conv_id = f"conv-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        doc = {
            "id": conv_id,
            "user_id": user_id,
            "title": title or "Agricultural Query",
            "language": language,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "messages": [],
        }
        db = get_mongo_db()
        if db is not None and await check_mongodb_connection():
            await db["conversations"].insert_one(doc.copy())
        _in_memory_db["conversations"].append(doc)
        return doc

    @classmethod
    async def add_message(
        cls,
        conversation_id: str,
        role: str,
        content: str,
        language: str,
        advisory_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        msg_id = f"msg-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        msg = {
            "id": msg_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "language": language,
            "advisory_data": advisory_data,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        db = get_mongo_db()
        if db is not None and await check_mongodb_connection():
            await db["messages"].insert_one(msg.copy())
            await db["conversations"].update_one(
                {"id": conversation_id},
                {"$push": {"messages": msg}, "$set": {"updated_at": msg["created_at"]}},
            )
        _in_memory_db["messages"].append(msg)
        for c in _in_memory_db["conversations"]:
            if c["id"] == conversation_id:
                if "messages" not in c:
                    c["messages"] = []
                c["messages"].append(msg)
                c["updated_at"] = msg["created_at"]
                break
        return msg

    @classmethod
    async def list_conversations(
        cls,
        user_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        db = get_mongo_db()
        items = []
        if db is not None and await check_mongodb_connection():
            query = {"user_id": user_id} if user_id else {}
            cursor = db["conversations"].find(query).sort("created_at", -1).limit(limit)
            items = await cursor.to_list(length=limit)
        else:
            items = sorted(
                _in_memory_db["conversations"],
                key=lambda x: x["created_at"],
                reverse=True,
            )[:limit]

        result = []
        for c in items:
            msgs = c.get("messages", [])
            user_msgs = [m for m in msgs if m.get("role") == "user"]
            asst_msgs = [m for m in msgs if m.get("role") == "assistant"]
            first_q = user_msgs[0].get("content") if user_msgs else c.get("title", "")
            first_a = asst_msgs[0].get("content") if asst_msgs else ""
            result.append({
                "id": str(c.get("id")),
                "question": first_q,
                "answer_preview": first_a[:120] if first_a else "",
                "language": c.get("language", "en"),
                "timestamp": c.get("created_at", datetime.now(timezone.utc).isoformat()),
            })
        return result

    @classmethod
    async def delete_conversation(cls, conversation_id: str) -> bool:
        db = get_mongo_db()
        if db is not None and await check_mongodb_connection():
            await db["conversations"].delete_one({"id": conversation_id})
            await db["messages"].delete_many({"conversation_id": conversation_id})
        _in_memory_db["conversations"] = [
            c for c in _in_memory_db["conversations"] if c.get("id") != conversation_id
        ]
        _in_memory_db["messages"] = [
            m for m in _in_memory_db["messages"] if m.get("conversation_id") != conversation_id
        ]
        return True
