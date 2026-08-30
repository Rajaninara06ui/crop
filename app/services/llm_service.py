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
    _TELUGU_RESPONSES = {
        "yellow": {
            "possible_issue": "టమోటాలో పోషకాల లోపం లేదా అధిక నీటిపారుదల (ఆకుల పసుపు రంగు)",
            "explanation": (
                "టమోటా మొక్కల ఆకులు పసుపు రంగులోకి మారడానికి ప్రధానంగా మెగ్నీషియం లోపం లేదా అధిక నీటిపారుదల వల్ల వేర్లకు గాలి అందకపోవడం కారణం. "
                "పాత ఆకులలో ఈనెలు ఆకుపచ్చగా ఉండి మధ్య భాగం పసుపుగా మారితే అది మెగ్నీషియం లోపం. "
                "నేలలో సరైన మురుగునీటి పారుదల సౌకర్యం ఉండేలా చూసుకోండి."
            ),
            "recommended_actions": [
                "నేలలో తేమను పరిశీలించి అధిక నీటిపారుదలను వెంటనే నియంత్రించండి.",
                "లీటరు నీటికి 5 గ్రాముల మెగ్నీషియం సల్ఫేట్ (ఎప్సమ్ సాల్ట్) కలిపి ఆకులపై పిచికారీ చేయండి.",
                "నేల pH విలువను 6.0 నుండి 6.8 మధ్య ఉండేలా సరిచూసుకోండి.",
                "రసం పీల్చే పురుగుల ఉనికి కోసం ఆకుల అడుగుభాగాన్ని క్రమం తప్పకుండా పరిశీలించండి.",
            ],
            "precautions": [
                "ఎండ తీవ్రత ఎక్కువగా ఉన్న సమయాల్లో ఎరువులు లేదా రసాయనాలు పిచికారీ చేయవద్దు.",
                "రసాయనిక ఎరువులను మోతాదుకు మించి అధికంగా వాడకండి.",
            ],
            "when_to_contact_expert": "పంటలో 30% కంటే ఎక్కువ మొక్కలకు పసుపు రంగు వ్యాపిస్తే వెంటనే సమీప రైతు భరోసా కేంద్రం లేదా వ్యవసాయాధికారిని సంప్రదించండి.",
            "confidence": 0.92,
        },
        "water": {
            "possible_issue": "వరి పంటలో నీటి యాజమాన్యం మరియు తడుల నిర్వహణ",
            "explanation": (
                "వరి పంటకు పిలకలు తొడిగే దశలో 5 నుండి 7 సెం.మీ మేర పలుచటి నీరు నిలపాలి. "
                "ఆల్టర్నేట్ వెట్టింగ్ అండ్ డ్రైయింగ్ (AWD) పద్ధతిని పాటిస్తే 30% వరకు నీరు ఆదా అవుతుంది. "
                "చిరుపొట్ట మరియు పూత దశలలో చేనులో తేమ ఆరిపోకుండా తగిన జాగ్రత్తలు తీసుకోవాలి. "
                "కోతకు 10 రోజుల ముందు చేనులోని నీటిని పూర్తిగా తీసివేయాలి."
            ),
            "recommended_actions": [
                "దుబ్బు చేసే దశలో పొలంలో 3-5 సెం.మీ మేర నీరు నిలపండి.",
                "పూత మరియు గింజ పాలుపోసుకునే దశలలో పొలం ఎండిపోకుండా నిరంతరం తేమను కాపాడండి.",
                "పొలంలో నీరు ఎక్కువగా నిలవకుండా మురుగు కాలువలు ఏర్పాటు చేయండి.",
                "వరి కోతకు 10 రోజుల ముందే నీటి సరఫరా నిలిపివేయండి.",
            ],
            "precautions": [
                "అధిక నీరు నిలవడం వల్ల అగ్గి తెగులు (బ్లాస్ట్) వచ్చే అవకాశం ఉంది.",
                "రాత్రి వేళల్లో మాత్రమే మురుగునీటి పారుదల చేయండి.",
            ],
            "when_to_contact_expert": "ఆకులపై నూలుకండె ఆకారపు మచ్చలు లేదా ఎండిపోవడం గమనిస్తే వ్యవసాయ శాస్త్రవేత్తలను సంప్రదించండి.",
            "confidence": 0.94,
        },
        "pest": {
            "possible_issue": "మిర్చి పంటలో తామర పురుగులు, పేనుబంక మరియు నల్లి నివారణ",
            "explanation": (
                "మిర్చి పంటలో ఆకులు ముడుచుకుపోవడం తామర పురుగులు (థ్రిప్స్) లేదా నల్లి ఉధృతి వల్ల జరుగుతుంది. "
                "ఆకులు పైకి ముడుచుకుంటే తామర పురుగులు, కిందకు ముడుచుకుంటే నల్లి ఆశించినట్లు గుర్తించాలి. "
                "మొదటి దశలో వేప నూనె పిచికారీ చేయడం ఉత్తమం. ఉధృతి తీవ్రంగా ఉంటే సిఫార్సు చేసిన పురుగుమందులను వాడాలి."
            ),
            "recommended_actions": [
                "ఎకరానికి 15-20 పసుపు, నీలి రంగు జిగురు అట్టలను అమర్చండి.",
                "లీటరు నీటికి 5 మి.లీ వేప నూనె (10,000 ppm) కలిపి పిచికారీ చేయండి.",
                "ఉధృతి తీవ్రంగా ఉంటే లీటరు నీటికి ఫిప్రోనిల్ 2 మి.లీ లేదా డయాఫెంథియురాన్ 1.25 గ్రాములు పిచికారీ చేయండి.",
                "పొలం గట్లపై కలుపు మొక్కలను పూర్తిగా తొలగించండి.",
            ],
            "precautions": [
                "పురుగుమందులు పిచికారీ చేసేటప్పుడు రక్షణ దుస్తులు మరియు మాస్క్ ధరించండి.",
                "మిత్ర పురుగులు నాశనం కాకుండా మోతాదుకు మించి మందులు కలపవద్దు.",
            ],
            "when_to_contact_expert": "ఆకు ముడత తీవ్రమై పూత రాలిపోతుంటే ఉద్యానవన శాఖ అధికారిని సంప్రదించండి.",
            "confidence": 0.89,
        },
        "fertilizer": {
            "possible_issue": "పత్తి పంటలో సమగ్ర ఎరువుల యాజమాన్యం మరియు పోషక లోపాలు",
            "explanation": (
                "పత్తి పంటకు నత్రజని, భాస్వరం, పొటాష్ ఎరువులను 120:60:60 కిలోలు/హెక్టారుకు సమతుల్యంగా వేయాలి. "
                "నత్రజనిని మూడు విడతలుగా (విత్తేటప్పుడు, పూత దశలో, కాయ దశలో) అందించాలి. "
                "పొటాష్ ఎరువు కాయ నాణ్యతకు, బరువుకు అత్యంత కీలకం. ఆకులు ఎర్రబారితే మెగ్నీషియం సల్ఫేట్ పిచికారీ చేయాలి."
            ),
            "recommended_actions": [
                "నత్రజని ఎరువులను మూడు సమాన భాగాలుగా విభజించి చేనులో తగిన తేమ ఉన్నప్పుడు వేయండి.",
                "పూత మరియు కాయ దశలలో 1% మెగ్నీషియం సల్ఫేట్ + 1% 19:19:19 ద్రావణాన్ని పిచికారీ చేయండి.",
                "ఎకరానికి 10 కిలోల జింక్ సల్ఫేట్ దుక్కిలో వేయండి.",
                "కాయలు రాలకుండా లీటరు నీటికి 0.25 మి.లీ ప్లానోఫిక్స్ పిచికారీ చేయండి.",
            ],
            "precautions": [
                "ఎండిన నేలపై ఎరువులు వేయరాదు; ఎరువులు వేసిన వెంటనే తేలికపాటి తడి ఇవ్వండి.",
                "అధిక నత్రజని వాడకం వల్ల శాఖీయ పెరుగుదల పెరిగి పురుగుల ఉధృతి పెరుగుతుంది.",
            ],
            "when_to_contact_expert": "కాయలు అధికంగా రాలిపోతుంటే సమీప కృషి విజ్ఞాన కేంద్రాన్ని సంప్రదించండి.",
            "confidence": 0.91,
        }
    }

    _ENGLISH_RESPONSES = {
        "yellow": {
            "possible_issue": "Nutrient deficiency or overwatering in tomato",
            "explanation": (
                "Yellow leaves on tomato plants commonly indicate magnesium or iron deficiency, "
                "or root suffocation from overwatering. Check soil drainage and pH. "
                "If yellowing starts on older leaves with green veins, suspect magnesium deficiency."
            ),
            "recommended_actions": [
                "Check soil moisture and ensure proper drainage",
                "Test soil pH (ideal 6.0-6.8 for tomatoes)",
                "Apply magnesium sulphate (Epsom salt) foliar spray",
                "Inspect undersides of leaves for pest activity",
            ],
            "precautions": [
                "Avoid excessive fertilizer application",
                "Do not spray chemicals during peak sunlight hours",
            ],
            "when_to_contact_expert": "If yellowing spreads rapidly to 50% of plants within 2-3 days, contact an agricultural expert immediately.",
            "confidence": 0.90,
        },
        "water": {
            "possible_issue": "Irrigation timing and water management for paddy",
            "explanation": (
                "Paddy (rice) requires shallow standing water (5-7 cm) during tillering. "
                "Use Alternate Wetting and Drying (AWD) to save 30% water. "
                "Never let the field dry out during booting and flowering stages. Drain 10 days before harvest."
            ),
            "recommended_actions": [
                "Maintain 5-7 cm flood depth during tillering",
                "Practice AWD technique between irrigations",
                "Keep field moist at booting and flowering stages",
                "Drain completely 10 days before harvest",
            ],
            "precautions": [
                "Avoid over-irrigation which promotes blast disease",
                "Monitor water levels daily during critical growth stages",
            ],
            "when_to_contact_expert": "If crop shows lodging or disease symptoms, contact your local extension officer.",
            "confidence": 0.92,
        },
        "pest": {
            "possible_issue": "Pest management in chilli",
            "explanation": (
                "Chilli plants are susceptible to thrips, mites, and aphids. Use neem oil spray (5 ml/L) as a first response. "
                "For severe infestation, apply imidacloprid 17.8SL at 0.25 ml/L or fipronil 2 ml/L."
            ),
            "recommended_actions": [
                "Spray neem oil (5 ml/L water) every 7 days",
                "Install yellow and blue sticky traps (15-20/acre)",
                "Remove and destroy severely infested plant parts",
                "Apply recommended pesticide for severe infestations",
            ],
            "precautions": [
                "Wear protective mask and gloves when applying pesticides",
                "Observe pre-harvest intervals for all chemicals",
            ],
            "when_to_contact_expert": "If more than 30% of plants are affected, seek guidance from a certified agronomist.",
            "confidence": 0.88,
        },
        "fertilizer": {
            "possible_issue": "Fertilizer management in cotton",
            "explanation": (
                "Cotton requires balanced NPK application (120:60:60 kg/ha). Apply nitrogen in split doses: "
                "basal, squaring, and boll development stages. Potassium is essential for boll retention and quality."
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
            "when_to_contact_expert": "For severe square dropping or red leaf symptoms, consult your extension specialist.",
            "confidence": 0.90,
        }
    }

    async def generate_answer(
        self, question: str, context: str, language: str,
        crop: Optional[str] = None, location: Optional[str] = None,
    ) -> Dict[str, Any]:
        q_lower = question.lower()
        
        # Determine topic key
        key = "yellow"
        if any(w in q_lower for w in ["water", "irrigat", "paddy", "వరి", "నీరు", "తడి"]):
            key = "water"
        elif any(w in q_lower for w in ["pest", "insect", "chilli", "mirchi", "మిర్చి", "పురుగు", "ముడత"]):
            key = "pest"
        elif any(w in q_lower for w in ["fertiliz", "cotton", "nutrient", "పత్తి", "ఎరువు"]):
            key = "fertilizer"

        if language == "te":
            return dict(self._TELUGU_RESPONSES.get(key, self._TELUGU_RESPONSES["yellow"]))

        return dict(self._ENGLISH_RESPONSES.get(key, self._ENGLISH_RESPONSES["yellow"]))


def get_llm_service() -> LLMService:
    if settings.MOCK_MODE:
        return MockLLMService()
    provider = settings.LLM_PROVIDER.lower()
    if provider == "openai":
        return OpenAILLMService()
    elif provider in ("google", "gemini"):
        return GoogleLLMService()
    return MockLLMService()
