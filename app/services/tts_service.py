from __future__ import annotations
import base64
from abc import ABC, abstractmethod
import httpx
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

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

_SILENT_MP3 = bytes([
    0xFF, 0xFB, 0x90, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
])


class TTSService(ABC):
    @abstractmethod
    async def synthesize(self, text: str, language: str) -> bytes:
        pass

    @property
    def content_type(self) -> str:
        return "audio/wav"


class SarvamTTSService(TTSService):
    """
    Sarvam AI (Bulbul TTS) for high-quality Indian language speech synthesis.
    """
    API_URL = "https://api.sarvam.ai/text-to-speech"

    def __init__(self) -> None:
        self.api_key = settings.SARVAM_API_KEY or settings.TTS_API_KEY

    async def synthesize(self, text: str, language: str) -> bytes:
        if not self.api_key:
            logger.info("Sarvam API key not set, using demo audio.")
            return await MockTTSService().synthesize(text, language)

        target_lang = SARVAM_LANG_MAP.get(language, "te-IN")
        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": [text[:500]],  # Sarvam limit per segment
            "target_language_code": target_lang,
            "speaker": "meera",
            "pitch": 0,
            "pace": 1.0,
            "loudness": 1.5,
            "speech_sample_rate": 22050,
            "enable_preprocessing": True,
            "model": "bulbul:v1",
        }

        async with httpx.AsyncClient(timeout=40) as client:
            resp = await client.post(self.API_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        audios = data.get("audios", [])
        if audios and len(audios) > 0:
            return base64.b64decode(audios[0])
        return _SILENT_MP3 * 16

    @property
    def content_type(self) -> str:
        return "audio/wav"


class GoogleTTSService(TTSService):
    _LANG_TO_VOICE = {
        "en": "en-IN-Standard-A",
        "te": "te-IN-Standard-A",
        "hi": "hi-IN-Standard-A",
        "ta": "ta-IN-Standard-A",
        "kn": "kn-IN-Standard-A",
        "ml": "ml-IN-Standard-A",
        "mr": "mr-IN-Standard-A",
        "bn": "bn-IN-Standard-A",
    }

    def __init__(self) -> None:
        self.api_key = settings.TTS_API_KEY

    async def synthesize(self, text: str, language: str) -> bytes:
        if not self.api_key:
            return await MockTTSService().synthesize(text, language)
        voice = self._LANG_TO_VOICE.get(language, "te-IN-Standard-A")
        lang_code = f"{language}-IN" if language != "en" else "en-IN"
        payload = {
            "input": {"text": text[:5000]},
            "voice": {"languageCode": lang_code, "name": voice},
            "audioConfig": {"audioEncoding": "MP3"},
        }
        url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={self.api_key}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        audio_b64 = resp.json().get("audioContent", "")
        return base64.b64decode(audio_b64)

    @property
    def content_type(self) -> str:
        return "audio/mpeg"


class MockTTSService(TTSService):
    async def synthesize(self, text: str, language: str) -> bytes:
        return _SILENT_MP3 * 16


def get_tts_service() -> TTSService:
    provider = settings.TTS_PROVIDER.lower()
    if provider == "sarvam":
        return SarvamTTSService()
    elif provider == "google":
        return GoogleTTSService()
    return MockTTSService()
