import pytest


@pytest.mark.asyncio
async def test_translation_en_to_te(client):
    payload = {
        "text": "My tomato leaves are turning yellow",
        "source_language": "en",
        "target_language": "te",
    }
    resp = await client.post("/api/translate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "translated_text" in data
    assert data["target_language"] == "te"


@pytest.mark.asyncio
async def test_translation_te_to_en(client):
    payload = {
        "text": "నా టమోటా ఆకులు పసుపు రంగులోకి మారుతున్నాయి",
        "source_language": "te",
        "target_language": "en",
    }
    resp = await client.post("/api/translate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "translated_text" in data
    assert data["target_language"] == "en"


@pytest.mark.asyncio
async def test_translation_unsupported_language(client):
    payload = {
        "text": "Hello world",
        "source_language": "en",
        "target_language": "invalid_lang",
    }
    resp = await client.post("/api/translate", json=payload)
    assert resp.status_code == 422
