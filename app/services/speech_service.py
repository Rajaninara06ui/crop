from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import httpx
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class SpeechTranscriptionResult:
    def __init__(self, text: str, language: str, confidence: float) -> None:
        self.text = text
        self.language = language
        self.confidence = confidence


class SpeechService(ABC):
    @abstractmethod
    async def transcribe(self, audio_path: Path, language_hint: Optional[str] = None) -> SpeechTranscriptionResult:
        pass


class OpenAIWhisperService(SpeechService):
    def __init__(self) -> None:
        self.api_key = settings.STT_API_KEY or settings.LLM_API_KEY

    async def transcribe(self, audio_path: Path, language_hint: Optional[str] = None) -> SpeechTranscriptionResult:
        async with httpx.AsyncClient(timeout=120) as client:
            with open(audio_path, "rb") as f:
                files = {"file": (audio_path.name, f, "audio/mpeg")}
                data = {"model": "whisper-1"}
                if language_hint and language_hint != "en":
                    data["language"] = language_hint
                resp = await client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files=files,
                    data=data,
                )
                resp.raise_for_status()
        result = resp.json()
        return SpeechTranscriptionResult(
            text=result.get("text", ""),
            language=result.get("language", language_hint or "en"),
            confidence=0.95,
        )


class LocalWhisperService(SpeechService):
    def __init__(self) -> None:
        self._model = None

    def _load(self):
        if self._model is None:
            import whisper
            self._model = whisper.load_model("base")
            logger.info("Loaded local Whisper model")
        return self._model

    async def transcribe(self, audio_path: Path, language_hint: Optional[str] = None) -> SpeechTranscriptionResult:
        import asyncio
        model = self._load()
        loop = asyncio.get_event_loop()
        opts = {}
        if language_hint and language_hint != "en":
            opts["language"] = language_hint
        result = await loop.run_in_executor(None, lambda: model.transcribe(str(audio_path), **opts))
        return SpeechTranscriptionResult(
            text=result["text"].strip(),
            language=result.get("language", language_hint or "en"),
            confidence=0.90,
        )


class MockSpeechService(SpeechService):
    async def transcribe(self, audio_path: Path, language_hint: Optional[str] = None) -> SpeechTranscriptionResult:
        lang = language_hint or "en"
        demo_texts = {
            "en": "My tomato plants have yellow leaves",
            "te": "నా టమోటా ఆకులు పసుపు రంగులోకి మారుతున్నాయి",
            "hi": "मेरे टमाटर के पत्ते पीले हो रहे हैं",
            "ta": "என் தக்காளி இலைகள் மஞ்சளாக மாறுகின்றன",
            "kn": "ನನ್ನ ಟೊಮೆಟೊ ಎಲೆಗಳು ಹಳದಿಯಾಗುತ್ತಿವೆ",
            "ml": "എന്റെ തക്കാളി ഇലകൾ മഞ്ഞനിറമാകുന്നു",
            "mr": "माझ्या टोमॅटोची पाने पिवळी पडत आहेत",
            "bn": "আমার টমেটো পাতা হলুদ হয়ে যাচ্ছে",
        }
        text = demo_texts.get(lang, demo_texts["en"])
        return SpeechTranscriptionResult(text=text, language=lang, confidence=0.94)


def get_speech_service() -> SpeechService:
    if settings.MOCK_MODE:
        return MockSpeechService()
    provider = settings.STT_PROVIDER.lower()
    if provider == "openai":
        return OpenAIWhisperService()
    elif provider == "whisper_local":
        return LocalWhisperService()
    logger.warning("Unknown STT provider '%s', using mock.", provider)
    return MockSpeechService()
