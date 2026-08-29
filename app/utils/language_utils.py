from __future__ import annotations
from typing import Optional
from app.data.languages import SUPPORTED_LANGUAGES, is_supported
from app.core.logging import get_logger

logger = get_logger(__name__)


def validate_language_code(code: str) -> str:
    code = code.lower().strip()
    if not is_supported(code):
        supported = ", ".join(SUPPORTED_LANGUAGES.keys())
        raise ValueError(f"Unsupported language ''{code}''. Supported codes: {supported}")
    return code


def detect_language_from_text(text: str) -> Optional[str]:
    if not text:
        return "en"
    counts: dict[str, int] = {}
    for char in text:
        cp = ord(char)
        if 0x0C00 <= cp <= 0x0C7F:
            counts["te"] = counts.get("te", 0) + 1
        elif 0x0900 <= cp <= 0x097F:
            counts["hi"] = counts.get("hi", 0) + 1
        elif 0x0B80 <= cp <= 0x0BFF:
            counts["ta"] = counts.get("ta", 0) + 1
        elif 0x0C80 <= cp <= 0x0CFF:
            counts["kn"] = counts.get("kn", 0) + 1
        elif 0x0D00 <= cp <= 0x0D7F:
            counts["ml"] = counts.get("ml", 0) + 1
        elif 0x0980 <= cp <= 0x09FF:
            counts["bn"] = counts.get("bn", 0) + 1
    if not counts:
        return "en"
    detected = max(counts, key=lambda k: counts[k])
    logger.debug("Detected language '%%s' from script analysis", detected)
    return detected


def needs_translation(source_lang: str, target_lang: str) -> bool:
    return source_lang.lower() != target_lang.lower()
