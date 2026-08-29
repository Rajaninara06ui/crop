from __future__ import annotations
from abc import ABC, abstractmethod
import httpx
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

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
        return "audio/mpeg"


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
        voice = self._LANG_TO_VOICE.get(language, "en-IN-Standard-A")
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
        import base64
        audio_b64 = resp.json().get("audioContent", "")
        return base64.b64decode(audio_b64)


class OpenAITTSService(TTSService):
    def __init__(self) -> None:
        self.api_key = settings.TTS_API_KEY or settings.LLM_API_KEY

    async def synthesize(self, text: str, language: str) -> bytes:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": "tts-1", "input": text[:4096], "voice": "alloy", "response_format": "mp3"},
            )
            resp.raise_for_status()
        return resp.content


class MockTTSService(TTSService):
    async def synthesize(self, text: str, language: str) -> bytes:
        return _SILENT_MP3 * 16


def get_tts_service() -> TTSService:
    if settings.MOCK_MODE:
        return MockTTSService()
    provider = settings.TTS_PROVIDER.lower()
    if provider == "google":
        return GoogleTTSService()
    elif provider == "openai":
        return OpenAITTSService()
    logger.warning("Unknown TTS provider '%s', using mock.", provider)
    return MockTTSService()
