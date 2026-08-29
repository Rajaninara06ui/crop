import pytest


@pytest.mark.asyncio
async def test_query_english(client):
    payload = {
        "question": "My tomato leaves are turning yellow",
        "language": "en",
        "crop": "tomato",
    }
    resp = await client.post("/api/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert data["language"] == "en"
    assert "sources" in data
    assert isinstance(data["recommended_actions"], list)
    assert data["confidence"] > 0.0


@pytest.mark.asyncio
async def test_query_telugu(client):
    payload = {
        "question": "నా టమోటా ఆకులు పసుపు రంగులోకి మారుతున్నాయి",
        "language": "te",
        "crop": "tomato",
    }
    resp = await client.post("/api/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["language"] == "te"
    assert "answer" in data


@pytest.mark.asyncio
async def test_query_unsupported_language(client):
    payload = {
        "question": "My tomato leaves are yellow",
        "language": "xx_unsupported",
    }
    resp = await client.post("/api/query", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_query_empty_question(client):
    payload = {
        "question": "   ",
        "language": "en",
    }
    resp = await client.post("/api/query", json=payload)
    assert resp.status_code == 422
