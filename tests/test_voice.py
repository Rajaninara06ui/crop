import io
import pytest


@pytest.mark.asyncio
async def test_transcribe_mock_audio(client):
    fake_wav_bytes = b"RIFF" + b"\x00" * 36 + b"WAVEfmt " + b"\x00" * 20 + b"data" + b"\x00" * 100
    files = {"audio": ("sample.wav", io.BytesIO(fake_wav_bytes), "audio/wav")}
    resp = await client.post("/api/voice/transcribe", files=files, data={"language": "en"})
    assert resp.status_code == 200
    data = resp.json()
    assert "text" in data
    assert data["language"] == "en"
    assert data["confidence"] > 0.8


@pytest.mark.asyncio
async def test_transcribe_invalid_audio_type(client):
    files = {"audio": ("sample.txt", io.BytesIO(b"not audio content"), "text/plain")}
    resp = await client.post("/api/voice/transcribe", files=files)
    assert resp.status_code == 415
