from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional
import httpx
from app.core.config import settings
from app.core.logging import get_logger
from app.data.languages import SUPPORTED_LANGUAGES

logger = get_logger(__name__)


class TranslationService(ABC):
    @abstractmethod
    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        pass


class GoogleTranslationService(TranslationService):
    BASE_URL = "https://translation.googleapis.com/language/translate/v2"

    def __init__(self) -> None:
        self.api_key = settings.TRANSLATION_API_KEY

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if source_lang == target_lang or not text:
            return text
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                self.BASE_URL,
                params={"key": self.api_key},
                json={"q": text, "source": source_lang, "target": target_lang, "format": "text"},
            )
            resp.raise_for_status()
            data = resp.json()
        return data["data"]["translations"][0]["translatedText"]


class DeepLTranslationService(TranslationService):
    BASE_URL = "https://api-free.deepl.com/v2/translate"

    _DEEPL_LANG_MAP = {
        "en": "EN", "hi": "HI",
    }

    def __init__(self) -> None:
        self.api_key = settings.TRANSLATION_API_KEY

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if source_lang == target_lang or not text:
            return text
        src = self._DEEPL_LANG_MAP.get(source_lang, source_lang.upper())
        tgt = self._DEEPL_LANG_MAP.get(target_lang, target_lang.upper())
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                self.BASE_URL,
                headers={"Authorization": f"DeepL-Auth-Key {self.api_key}"},
                data={"text": text, "source_lang": src, "target_lang": tgt},
            )
            resp.raise_for_status()
        return resp.json()["translations"][0]["text"]


class MockTranslationService(TranslationService):
    _MOCK_TRANSLATIONS: dict = {
        ("en", "te"): {
            "My tomato leaves are turning yellow": "మీ టమోటా మొక్కల ఆకులు పసుపు రంగులోకి మారడానికి కారణాలు...",
            "Nutrient deficiency or overwatering": "పోషకాల లోపం లేదా అధిక నీటిపారుదల",
            "Check soil moisture and ensure proper drainage": "నేలలో తేమను తనిఖీ చేసి సరైన పారుదల ఉండేలా చూడండి",
            "Test soil pH (ideal 6.0-6.8 for tomatoes)": "నేల pH విలువను పరీక్షించండి (టమోటాకు 6.0-6.8 ఉత్తమం)",
            "Apply magnesium sulphate (Epsom salt) foliar spray": "మెగ్నీషియం సల్ఫేట్ ద్రావణాన్ని ఆకులపై పిచికారీ చేయండి",
            "Reduce watering frequency if soil feels wet": "నేల తడిగా ఉంటే నీరు పెట్టే వ్యవధిని తగ్గించండి",
            "Inspect undersides of leaves for pest activity": "ఆకుల అడుగుభాగాన పురుగుల ఉనికిని తనిఖీ చేయండి",
            "Avoid excessive fertilizer application": "అధిక మోతాదులో ఎరువులు వాడటం నివారించండి",
            "Do not spray chemicals during peak sunlight hours": "ఎండ తీవ్రత ఉన్న సమయంలో రసాయనాలు పిచికారీ చేయవద్దు",
        },
        ("te", "en"): {
            "నా టమోటా ఆకులు పసుపు రంగులోకి మారుతున్నాయి": "My tomato leaves are turning yellow",
            "మీ టమోటా మొక్కల ఆకులు పసుపు రంగులోకి మారడానికి...": "My tomato leaves are turning yellow",
        },
        ("en", "hi"): {
            "My tomato leaves are turning yellow": "मेरे टमाटर के पत्ते पीले हो रहे हैं",
            "Nutrient deficiency or overwatering": "पोषक तत्वों की कमी या अधिक पानी देना",
        },
        ("hi", "en"): {
            "मेरे टमाटर के पत्ते पीले हो रहे हैं": "My tomato leaves are turning yellow",
        },
        ("en", "ta"): {
            "My tomato leaves are turning yellow": "என் தக்காளி இலைகள் மஞ்சளாக மாறுகின்றன",
        },
        ("ta", "en"): {
            "என் தக்காளி இலைகள் மஞ்சளாக மாறுகின்றன": "My tomato leaves are turning yellow",
        }
    }

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if source_lang == target_lang or not text:
            return text
        lookup = self._MOCK_TRANSLATIONS.get((source_lang, target_lang), {})
        if text in lookup:
            return lookup[text]
        for k, v in lookup.items():
            if k.lower() in text.lower():
                return v
        lang_name = SUPPORTED_LANGUAGES.get(target_lang, target_lang)
        if target_lang == "te":
            return f"మీ వ్యవసాయ సలహా ({lang_name}): {text}"
        elif target_lang == "hi":
            return f"कृषि सलाह ({lang_name}): {text}"
        elif target_lang == "ta":
            return f"விவசாய ஆலோசனை ({lang_name}): {text}"
        return f"[{lang_name}]: {text}"


def get_translation_service() -> TranslationService:
    if settings.MOCK_MODE:
        return MockTranslationService()
    provider = settings.TRANSLATION_PROVIDER.lower()
    if provider == "google":
        return GoogleTranslationService()
    elif provider == "deepl":
        return DeepLTranslationService()
    logger.warning("Unknown translation provider '%s', using mock.", provider)
    return MockTranslationService()
