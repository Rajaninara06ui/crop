from __future__ import annotations
from typing import Any, Dict, List, Optional
from app.core.logging import get_logger
from app.rag.retriever import Retriever, RetrievedChunk
from app.services.llm_service import get_llm_service
from app.services.safety_service import SafetyService

logger = get_logger(__name__)


class RAGService:
    def __init__(self) -> None:
        self.retriever = Retriever()
        self.llm = get_llm_service()
        self.safety = SafetyService()

    async def answer(
        self,
        question: str,
        language: str,
        crop: Optional[str] = None,
        location: Optional[str] = None,
    ) -> Dict[str, Any]:
        logger.info("RAG pipeline: question='%s' lang=%s crop=%s", question[:80], language, crop)

        chunks: List[RetrievedChunk] = self.retriever.retrieve(question, crop_hint=crop)
        context = self.retriever.build_context(chunks)

        if not chunks:
            logger.warning("No relevant documents found for query.")
            context = ""

        llm_result = await self.llm.generate_answer(
            question=question,
            context=context,
            language=language,
            crop=crop,
            location=location,
        )

        llm_result = self.safety.validate(llm_result)

        return {
            "llm_result": llm_result,
            "chunks": chunks,
        }
