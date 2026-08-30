from __future__ import annotations
from typing import Any, Dict, List, Optional
from app.core.logging import get_logger
from app.data.languages import TRANSLATE_TO_EN_FOR_RETRIEVAL
from app.services.rag_service import RAGService
from app.services.translation_service import get_translation_service
from app.schemas.query import SourceSchema

logger = get_logger(__name__)


class AdvisoryService:
    def __init__(self) -> None:
        self.rag = RAGService()
        self.translator = get_translation_service()

    async def process(
        self,
        question: str,
        language: str,
        crop: Optional[str] = None,
        location: Optional[str] = None,
    ) -> Dict[str, Any]:
        logger.info("Advisory pipeline: lang=%s crop=%s q='%s'", language, crop, question[:60])

        retrieval_question = question.strip()

        # Step 1: For vector retrieval, if needed translate query to EN
        if language in TRANSLATE_TO_EN_FOR_RETRIEVAL:
            try:
                retrieval_question = await self.translator.translate(
                    retrieval_question, source_lang=language, target_lang="en"
                )
                logger.info("Translated question to EN for retrieval: '%s'", retrieval_question[:80])
            except Exception as exc:
                logger.warning("Translation to EN failed: %s. Using original.", exc)

        # Step 2: Query RAG & LLM with the target language
        rag_output = await self.rag.answer(
            question=retrieval_question,
            language=language,
            crop=crop,
            location=location,
        )
        llm_result: Dict[str, Any] = rag_output["llm_result"]
        chunks = rag_output["chunks"]

        explanation = llm_result.get("explanation", "")
        possible_issue = llm_result.get("possible_issue", "")
        actions: List[str] = llm_result.get("recommended_actions", [])
        precautions: List[str] = llm_result.get("precautions", [])
        expert_note = llm_result.get("when_to_contact_expert", "")

        # Step 3: Check if LLM output needs translation (if returned in English when Telugu was asked)
        # If the explanation is in English and user asked Telugu, translate it
        if language != "en" and explanation and any(ord(c) < 128 for c in explanation[:20]):
            # If explanation doesn't contain non-ASCII Indic characters, translate it
            has_indic = any(ord(c) > 128 for c in explanation[:100])
            if not has_indic:
                try:
                    explanation = await self.translator.translate(explanation, "en", language)
                    if possible_issue:
                        possible_issue = await self.translator.translate(possible_issue, "en", language)
                    if expert_note:
                        expert_note = await self.translator.translate(expert_note, "en", language)
                    actions = [
                        await self.translator.translate(a, "en", language) for a in actions
                    ]
                    precautions = [
                        await self.translator.translate(p, "en", language) for p in precautions
                    ]
                except Exception as exc:
                    logger.warning("Translation to %s failed: %s.", language, exc)

        sources = [
            SourceSchema(
                title=c.title,
                content=c.content[:200],
                source=c.source,
                page=c.page,
                relevance_score=c.relevance_score,
            )
            for c in chunks
        ]

        confidence = float(llm_result.get("confidence", 0.90))

        return {
            "answer": explanation,
            "language": language,
            "sources": sources,
            "confidence": confidence,
            "possible_issue": possible_issue or None,
            "explanation": explanation,
            "recommended_actions": actions,
            "precautions": precautions,
            "expert_advice": expert_note or None,
            "when_to_contact_expert": expert_note or None,
        }
