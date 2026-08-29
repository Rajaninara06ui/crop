from __future__ import annotations
import json
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import httpx
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

AGRICULTURAL_SYSTEM_PROMPT = """
You are an AI agricultural advisory assistant helping farmers in India.
You ONLY answer questions about agriculture, crops, farming, soil, irrigation, pests, diseases, and related topics.

Rules:
1. Use the provided CONTEXT (retrieved documents) to ground your answer.
2. If the context contains relevant information, use it; do NOT invent sources.
3. If no relevant context is found, clearly state you could not find reliable information and recommend consulting an agricultural expert.
4. Give simple, practical advice in plain language that farmers can understand.
5. Never claim to be a human agricultural expert.
6. Clearly indicate uncertainty when confidence is low.
7. For serious crop damage or disease outbreaks, always recommend consulting a qualified agricultural expert.
8. Never provide unsafe chemical dosage instructions unless they are from the retrieved context.
9. Always answer in the language specified.
10. Format your response as valid JSON matching the specified schema.
"""

RESPONSE_SCHEMA = """
Respond ONLY with this JSON structure (no extra text):
{
  "possible_issue": "<brief issue summary>",
  "explanation": "<detailed explanation in the requested language>",
  "recommended_actions": ["<action 1>", "<action 2>"],
  "precautions": ["<precaution 1>"],
  "when_to_contact_expert": "<when to seek professional help>",
  "confidence": <float 0.0-1.0>
}
"""

def _parse_llm_json(raw: str) -> Dict[str, Any]:
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {
        "possible_issue": "Unable to determine",
        "explanation": raw[:1000],
        "recommended_actions": [],
        "precautions": [],
        "when_to_contact_expert": "Please consult a local agricultural expert.",
        "confidence": 0.5,
    }


class LLMService(ABC):
    @abstractmethod
    async def generate_answer(
        self,
        question: str,
        context: str,
        language: str,
        crop: Optional[str] = None,
        location: Optional[str] = None,
    ) -> Dict[str, Any]:
        pass


class OpenAILLMService(LLMService):
    def __init__(self) -> None:
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL
        self.base_url = "https://api.openai.com/v1"

    async def generate_answer(
        self, question: str, context: str, language: str,
        crop: Optional[str] = None, location: Optional[str] = None,
    ) -> Dict[str, Any]:
        user_msg = (
            f"CONTEXT:\n{context}\n\n"
            f"FARMER QUESTION: {question}\n"
            f"ANSWER LANGUAGE: {language}\n"
            + (f"CROP: {crop}\n" if crop else "")
            + (f"LOCATION: {location}\n" if location else "")
            + f"\n{RESPONSE_SCHEMA}"
        )
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "temperature": settings.LLM_TEMPERATURE,
                    "max_tokens": settings.LLM_MAX_TOKENS,
                    "messages": [
                        {"role": "system", "content": AGRICULTURAL_SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg},
                    ],
                },
            )
            resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"]
        return _parse_llm_json(raw)


class GoogleLLMService(LLMService):
    def __init__(self) -> None:
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL or "gemini-1.5-flash"

    async def generate_answer(
        self, question: str, context: str, language: str,
        crop: Optional[str] = None, location: Optional[str] = None,
    ) -> Dict[str, Any]:
        user_msg = (
            f"CONTEXT:\n{context}\n\n"
            f"FARMER QUESTION: {question}\n"
            f"ANSWER LANGUAGE: {language}\n"
            + (f"CROP: {crop}\n" if crop else "")
            + (f"LOCATION: {location}\n" if location else "")
            + f"\n{RESPONSE_SCHEMA}"
        )
        full_prompt = f"{AGRICULTURAL_SYSTEM_PROMPT}\n\n{user_msg}"
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                url,
                json={
                    "contents": [{"parts": [{"text": full_prompt}]}],
                    "generationConfig": {
                        "temperature": settings.LLM_TEMPERATURE,
                        "maxOutputTokens": settings.LLM_MAX_TOKENS,
                    },
                },
            )
            resp.raise_for_status()
        raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        return _parse_llm_json(raw)


class MockLLMService(LLMService):
    _DEMO_RESPONSES = {
        "yellow": {
            "possible_issue": "Nutrient deficiency or overwatering",
            "explanation": (
                "Yellow leaves on tomato plants commonly indicate magnesium or iron deficiency, "
                "or root suffocation from overwatering. Check soil drainage and pH. "
                "If yellowing starts on older leaves with green veins, suspect magnesium deficiency. "
                "If new leaves are yellow, check for iron deficiency or waterlogging."
            ),
            "recommended_actions": [
                "Check soil moisture and ensure proper drainage",
                "Test soil pH (ideal 6.0-6.8 for tomatoes)",
                "Apply magnesium sulphate (Epsom salt) foliar spray",
                "Reduce watering frequency if soil feels wet",
                "Inspect undersides of leaves for pest activity",
            ],
            "precautions": [
                "Avoid excessive fertilizer application",
                "Do not spray chemicals during peak sunlight hours",
            ],
            "when_to_contact_expert": "If yellowing spreads rapidly to 50% of plants within 2-3 days, contact an agricultural expert immediately.",
            "confidence": 0.88,
        },
        "water": {
            "possible_issue": "Irrigation timing query for paddy",
            "explanation": (
                "Paddy (rice) requires consistent moisture. Flood the field to 5-7 cm depth during the "
                "vegetative stage. Use Alternate Wetting and Drying (AWD) to save 30% water. "
                "Drain the field 10 days before harvest. Critical water stages are booting and flowering - "
                "never let the field dry during these periods."
            ),
            "recommended_actions": [
                "Maintain 5-7 cm flood depth during tillering",
                "Practice AWD technique between irrigations",
                "Never let field dry at booting and flowering stages",
                "Drain 10 days before planned harvest",
            ],
            "precautions": [
                "Avoid over-irrigation which promotes blast disease",
                "Monitor field water level daily during critical stages",
            ],
            "when_to_contact_expert": "If crop shows lodging or disease symptoms, contact your local agricultural extension officer.",
            "confidence": 0.92,
        },
        "pest": {
            "possible_issue": "Pest infestation in chilli",
            "explanation": (
                "Chilli plants are susceptible to thrips, mites, and aphids. Thrips cause silvery streaks "
                "and distorted leaves. Use neem oil spray (5 ml/L) as a first response. "
                "For severe infestation, apply imidacloprid 17.8SL at 0.25 ml/L. Introduce predatory mites "
                "for biological control."
            ),
            "recommended_actions": [
                "Spray neem oil (5 ml/L water) every 7 days",
                "Install yellow sticky traps to monitor thrips",
                "Remove severely infested plant parts",
                "Apply recommended pesticide for severe infestations",
            ],
            "precautions": [
                "Wear protective equipment when applying pesticides",
                "Observe pre-harvest intervals for all chemicals",
                "Avoid spraying during flowering to protect pollinators",
            ],
            "when_to_contact_expert": "If more than 30% of plants are affected, seek guidance from a certified agronomist.",
            "confidence": 0.85,
        },
        "fertilizer": {
            "possible_issue": "Fertilizer management in cotton",
            "explanation": (
                "Cotton requires balanced NPK application (120:60:60 kg/ha). Apply nitrogen in split doses: "
                "basal, squaring, and boll development stages. Potassium is essential for boll retention "
                "and fiber quality. Apply zinc sulphate if soil deficiency is observed."
            ),
            "recommended_actions": [
                "Apply 1/3rd nitrogen, full P and K at sowing",
                "Top-dress remaining nitrogen in 2 equal splits",
                "Foliar spray 1% MgSO4 + 1% 19:19:19 at peak flowering",
                "Incorporate organic compost to improve water retention",
            ],
            "precautions": [
                "Avoid excessive nitrogen which causes excessive vegetative growth",
                "Do not apply fertilizer on dry soil; irrigate after application",
            ],
            "when_to_contact_expert": "For severe square dropping or red leaf disease symptoms, consult your extension specialist.",
            "confidence": 0.90,
        }
    }

    async def generate_answer(
        self, question: str, context: str, language: str,
        crop: Optional[str] = None, location: Optional[str] = None,
    ) -> Dict[str, Any]:
        q_lower = question.lower()
        for keyword, response in self._DEMO_RESPONSES.items():
            if keyword in q_lower:
                return dict(response)
        return {
            "possible_issue": "General agricultural query",
            "explanation": (
                "Based on the agricultural knowledge base: "
                + (context[:300] if context else "Please consult your local agricultural extension service for specific advice.")
            ),
            "recommended_actions": [
                "Consult your local Krishi Vigyan Kendra (KVK)",
                "Contact the state agricultural department helpline",
                "Use soil testing services for accurate recommendations",
            ],
            "precautions": ["Always read pesticide labels before use"],
            "when_to_contact_expert": "For serious crop problems, always consult a qualified agricultural expert.",
            "confidence": 0.75,
        }


def get_llm_service() -> LLMService:
    if settings.MOCK_MODE:
        return MockLLMService()
    provider = settings.LLM_PROVIDER.lower()
    if provider == "openai":
        return OpenAILLMService()
    elif provider in ("google", "gemini"):
        return GoogleLLMService()
    logger.warning("Unknown LLM provider '%s', using mock.", provider)
    return MockLLMService()
