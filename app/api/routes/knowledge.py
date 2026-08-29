from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from app.core.logging import get_logger
from app.rag.retriever import Retriever

router = APIRouter(prefix="/knowledge", tags=["Knowledge"])
logger = get_logger(__name__)

KNOWLEDGE_CATEGORIES = [
    {"id": "crops", "name": "Crops", "description": "Crop cultivation guides and best practices"},
    {"id": "diseases", "name": "Diseases", "description": "Plant disease identification and management"},
    {"id": "pests", "name": "Pests", "description": "Pest control and integrated pest management"},
    {"id": "irrigation", "name": "Irrigation", "description": "Irrigation methods and water management"},
    {"id": "fertilizers", "name": "Fertilizers", "description": "Fertilizer recommendations and soil nutrition"},
    {"id": "weather", "name": "Weather", "description": "Weather-based agricultural guidance"},
    {"id": "soil", "name": "Soil", "description": "Soil health, testing, and management"},
]


class KnowledgeCategory(BaseModel):
    id: str
    name: str
    description: str


class KnowledgeSearchResult(BaseModel):
    title: str
    content: str
    source: Optional[str] = None
    relevance_score: float
    category: Optional[str] = None


@router.get("/categories", response_model=List[KnowledgeCategory])
async def get_categories():
    return KNOWLEDGE_CATEGORIES


@router.get("/search", response_model=List[KnowledgeSearchResult])
async def search_knowledge(q: str = Query(..., min_length=2, description="Search query")):
    try:
        retriever = Retriever()
        chunks = retriever.retrieve(q)
        return [
            KnowledgeSearchResult(
                title=c.title,
                content=c.content[:500],
                source=c.source,
                relevance_score=c.relevance_score,
                category=c.category,
            )
            for c in chunks
        ]
    except Exception as exc:
        logger.error("Knowledge search failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge base search is unavailable.",
        )
