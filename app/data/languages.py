from __future__ import annotations
from typing import Dict

SUPPORTED_LANGUAGES: Dict[str, str] = {
    "en": "English",
    "te": "Telugu",
    "hi": "Hindi",
    "ta": "Tamil",
    "kn": "Kannada",
    "ml": "Malayalam",
    "mr": "Marathi",
    "bn": "Bengali",
}

LANGUAGE_SCRIPTS: Dict[str, str] = {
    "en": "Latin",
    "te": "Telugu",
    "hi": "Devanagari",
    "ta": "Tamil",
    "kn": "Kannada",
    "ml": "Malayalam",
    "mr": "Devanagari",
    "bn": "Bengali",
}

TRANSLATE_TO_EN_FOR_RETRIEVAL: list[str] = ["te", "hi", "ta", "kn", "ml", "mr", "bn"]


def is_supported(code: str) -> bool:
    return code in SUPPORTED_LANGUAGES


def language_name(code: str) -> str:
    return SUPPORTED_LANGUAGES.get(code, "Unknown")
