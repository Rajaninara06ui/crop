from __future__ import annotations
import base64
import io
from abc import ABC, abstractmethod
import httpx
from gtts import gTTS
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

GTTS_LANG_MAP = {
    "te": "te",
    "hi": "hi",
    "ta": "ta",
    "kn": "kn",
    "ml": "ml",
    "mr": "mr",
    "bn": "bn",
    "en": "en",
}

SARVAM_LANG_MAP = {
    "en": "en-IN",
    "te": "te-IN",
    "hi": "hi-IN",
    "ta": "ta-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
    "mr": "mr-IN",
    "bn": "bn-IN",
}


class TTSService(ABC):
    @abstractmethod
    async def synthesize(self, text: str, language: str) -> bytes:
        pass

    @property
    def content_type(self) -> str:
        return "audio/mpeg"


class GTTSService(TTSService):
    async def synthesize(self, text: str, language: str) -> bytes:
        lang_code = GTTS_LANG_MAP.get(language.lower().strip(), "te" if language == "te" else "en")
        clean_text = text.strip()[:1200]
        if not clean_text:
            clean_text = "నమస్కారం రైతు సోదరులారా" if lang_code == "te" else "Hello Farmer"

        try:
            tts = gTTS(text=clean_text, lang=lang_code, slow=False)
            buf = io.BytesIO()
            tts.write_to_fp(buf)
            audio_bytes = buf.getvalue()
            logger.info("Synthesized %d bytes of %s voice audio with gTTS.", len(audio_bytes), lang_code)
            return audio_bytes
        except Exception as exc:
            logger.warning("gTTS synthesis notice: %s", exc)
            tts_en = gTTS(text=clean_text, lang="en")
            buf = io.BytesIO()
            tts_en.write_to_fp(buf)
            return buf.getvalue()

    @property
    def content_type(self) -> str:
        return "audio/mpeg"


class SarvamTTSService(TTSService):
    API_URL = "https://api.sarvam.ai/text-to-speech"

    def __init__(self) -> None:
        self.api_key = settings.SARVAM_API_KEY or settings.TTS_API_KEY

    async def synthesize(self, text: str, language: str) -> bytes:
        if not self.api_key:
            return await GTTSService().synthesize(text, language)

        target_lang = SARVAM_LANG_MAP.get(language, "te-IN")
        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": [text[:500]],
            "target_language_code": target_lang,
            "speaker": "meera",
            "pitch": 0,
            "pace": 1.0,
            "loudness": 1.5,
            "speech_sample_rate": 22050,
            "enable_preprocessing": True,
            "model": "bulbul:v1",
        }

        try:
            async with httpx.AsyncClient(timeout=40) as client:
                resp = await client.post(self.API_URL, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()

            audios = data.get("audios", [])
            if audios and len(audios) > 0:
                return base64.b64decode(audios[0])
        except Exception as exc:
            logger.warning("Sarvam TTS API failed: %s. Falling back to gTTS.", exc)

        return await GTTSService().synthesize(text, language)

    @property
    def content_type(self) -> str:
        return "audio/wav"


def get_tts_service() -> TTSService:
    provider = settings.TTS_PROVIDER.lower()
    if provider == "sarvam" and settings.SARVAM_API_KEY:
        return SarvamTTSService()
    return GTTSService()
