from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import httpx
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Sarvam language code mapping
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


class SpeechTranscriptionResult:
    def __init__(self, text: str, language: str, confidence: float) -> None:
        self.text = text
        self.language = language
        self.confidence = confidence


class SpeechService(ABC):
    @abstractmethod
    async def transcribe(self, audio_path: Path, language_hint: Optional[str] = None) -> SpeechTranscriptionResult:
        pass


class SarvamSpeechService(SpeechService):
    """
    Sarvam AI (Saaras STT) for 22 Indian Languages.
    """
    API_URL = "https://api.sarvam.ai/speech-to-text"

    def __init__(self) -> None:
        self.api_key = settings.SARVAM_API_KEY or settings.STT_API_KEY

    async def transcribe(self, audio_path: Path, language_hint: Optional[str] = None) -> SpeechTranscriptionResult:
        if not self.api_key:
            logger.info("Sarvam API key not set, using demo transcription.")
            return await MockSpeechService().transcribe(audio_path, language_hint)

        lang_code = SARVAM_LANG_MAP.get(language_hint or "en", "unknown")
        headers = {"api-subscription-key": self.api_key}

        async with httpx.AsyncClient(timeout=60) as client:
            with open(audio_path, "rb") as f:
                files = {"file": (audio_path.name, f, "audio/wav")}
                data = {
                    "model": "saaras:v2",
                    "language_code": lang_code if lang_code != "unknown" else "te-IN",
                    "with_diarization": "false",
                }
                resp = await client.post(self.API_URL, headers=headers, files=files, data=data)
                resp.raise_for_status()
                res_data = resp.json()

        transcript = res_data.get("transcript", "")
        detected_lang = res_data.get("language_code", language_hint or "te")
        # normalise language code (e.g. te-IN -> te)
        norm_lang = detected_lang.split("-")[0] if "-" in detected_lang else detected_lang
        return SpeechTranscriptionResult(
            text=transcript,
            language=norm_lang,
            confidence=0.96,
        )


class OpenAIWhisperService(SpeechService):
    def __init__(self) -> None:
        self.api_key = settings.STT_API_KEY or settings.LLM_API_KEY

    async def transcribe(self, audio_path: Path, language_hint: Optional[str] = None) -> SpeechTranscriptionResult:
        if not self.api_key:
            return await MockSpeechService().transcribe(audio_path, language_hint)
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


class MockSpeechService(SpeechService):
    async def transcribe(self, audio_path: Path, language_hint: Optional[str] = None) -> SpeechTranscriptionResult:
        lang = language_hint or "en"
        demo_texts = {
            "en": "My tomato plants have yellow leaves and I want to know what to do.",
            "te": "నా టమోటా ఆకులు పసుపు రంగులోకి మారుతున్నాయి, ఏం చేయాలో చెప్పండి.",
            "hi": "मेरे टमाटर के पौधों की पत्तियां पीली हो रही हैं, मुझे क्या करना चाहिए?",
            "ta": "என் தக்காளி செடிகளுக்கு மஞ்சள் இலைகள் வருகின்றன, என்ன செய்வது?",
            "kn": "ನನ್ನ ಟೊಮೆಟೊ ಗಿಡದ ಎಲೆಗಳು ಹಳದಿಯಾಗುತ್ತಿವೆ, ಏನು ಮಾಡಬೇಕು?",
            "ml": "എന്റെ തക്കാളി ചെടിയുടെ ഇലകൾ മഞ്ഞനിറമാകുന്നു, എന്തുചെയ്യണം?",
            "mr": "माझ्या टोमॅटोची पाने पिवळी पडत आहेत, काय करावे?",
            "bn": "আমার টমেটো গাছের পাতা হলুদ হয়ে যাচ্ছে, কী করা উচিত?",
        }
        text = demo_texts.get(lang, demo_texts["en"])
        return SpeechTranscriptionResult(text=text, language=lang, confidence=0.94)


def get_speech_service() -> SpeechService:
    provider = settings.STT_PROVIDER.lower()
    if provider == "sarvam":
        return SarvamSpeechService()
    elif provider == "openai":
        return OpenAIWhisperService()
    return MockSpeechService()
