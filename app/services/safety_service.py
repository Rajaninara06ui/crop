from __future__ import annotations
import re
from typing import Any, Dict
from app.core.logging import get_logger

logger = get_logger(__name__)

_DANGEROUS_KEYWORDS = [
    "spray .{0,20} litre", r"\d+\s*ml\/acre", "chlorpyrifos", "monocrotophos",
    "endosulfan", "dichlorvos", "methyl bromide", "paraquat",
]

_UNCERTAINTY_PHRASES = [
    "consult", "expert", "extension officer", "agricultural expert",
    "contact", "professional", "krishi vigyan", "kvk",
]

_EXPERT_ESCALATION = "For serious crop damage or disease outbreaks, please consult a qualified agricultural expert or your local Krishi Vigyan Kendra (KVK)."


class SafetyService:
    LOW_CONFIDENCE_THRESHOLD = 0.65

    def validate(self, result: Dict[str, Any]) -> Dict[str, Any]:
        explanation = result.get("explanation", "")
        confidence = float(result.get("confidence", 0.5))
        actions = result.get("recommended_actions", [])

        full_text = explanation + " " + " ".join(actions)
        for pattern in _DANGEROUS_KEYWORDS:
            if re.search(pattern, full_text, re.IGNORECASE):
                logger.warning("Safety: detected potentially unsafe chemical mention.")
                if not result.get("precautions"):
                    result["precautions"] = []
                result["precautions"].insert(
                    0,
                    "SAFETY: Always follow official label instructions for any chemical. "
                    "Wear protective equipment. Observe pre-harvest intervals.",
                )
                break

        if confidence < self.LOW_CONFIDENCE_THRESHOLD:
            logger.info("Safety: low confidence (%.2f), adding uncertainty notice.", confidence)
            result["explanation"] = (
                "[Note: AI confidence is low for this response. Please verify with local experts.] " + explanation
            )
            result["confidence"] = confidence

        expert_ref = result.get("when_to_contact_expert", "")
        if not expert_ref or not any(phrase in expert_ref.lower() for phrase in _UNCERTAINTY_PHRASES):
            result["when_to_contact_expert"] = _EXPERT_ESCALATION

        return result

    def is_agriculture_related(self, question: str) -> bool:
        ag_keywords = [
            "crop", "plant", "soil", "water", "leaf", "leaves", "pest",
            "disease", "fertilizer", "harvest", "seed", "farm", "paddy",
            "tomato", "chilli", "cotton", "wheat", "rice", "maize", "mango",
            "banana", "irrigation", "insect", "fungus", "blight", "wilt",
            "yellow", "brown", "spot", "rot", "spray", "growth", "yield",
            "టమోటా", "ఆకులు", "పసుపు", "పంట", "రైతు", "విత్తనాలు",
        ]
        q_lower = question.lower()
        return any(kw in q_lower for kw in ag_keywords)
