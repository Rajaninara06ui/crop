from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
from app.core.config import settings
from app.core.logging import get_logger
from app.rag.document_loader import Document
from app.rag.vector_store import get_vector_store

logger = get_logger(__name__)


@dataclass
class RetrievedChunk:
    title: str
    content: str
    source: str
    page: Optional[int]
    relevance_score: float
    crop: Optional[str] = None
    category: Optional[str] = None


class Retriever:
    def __init__(self, top_k: int = settings.TOP_K, threshold: float = settings.SIMILARITY_THRESHOLD) -> None:
        self.top_k = top_k
        self.threshold = threshold
        self._store = get_vector_store()

    def retrieve(self, query: str, crop_hint: Optional[str] = None) -> List[RetrievedChunk]:
        raw = self._store.similarity_search(query, k=self.top_k, threshold=self.threshold)
        chunks = []
        for doc, score in raw:
            meta = doc.metadata
            chunk = RetrievedChunk(
                title=meta.get("title", "Agricultural Knowledge Base"),
                content=doc.content,
                source=meta.get("source", "knowledge_base"),
                page=meta.get("page"),
                relevance_score=round(score, 4),
                crop=meta.get("crop"),
                category=meta.get("category"),
            )
            if crop_hint and meta.get("crop", "").lower() == crop_hint.lower():
                chunk.relevance_score = min(1.0, chunk.relevance_score + 0.05)
            chunks.append(chunk)
        chunks.sort(key=lambda c: c.relevance_score, reverse=True)
        if chunks:
            logger.info("Retrieved %%d chunks (top score: %%.3f)", len(chunks), chunks[0].relevance_score)
        return chunks

    def build_context(self, chunks: List[RetrievedChunk], max_chars: int = 4000) -> str:
        lines = []
        total = 0
        for i, chunk in enumerate(chunks):
            block = f"[Source {i + 1}: {chunk.title}]\n{chunk.content}\n"
            if total + len(block) > max_chars:
                break
            lines.append(block)
            total += len(block)
        return "\n".join(lines)

    @property
    def is_ready(self) -> bool:
        return self._store.is_ready
