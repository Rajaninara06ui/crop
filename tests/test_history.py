import pytest


@pytest.mark.asyncio
async def test_history_flow(client):
    # 1. Ask a question to generate history
    query_resp = await client.post(
        "/api/query",
        json={"question": "When should I water my paddy crop?", "language": "en"},
    )
    assert query_resp.status_code == 200
    conv_id = query_resp.json().get("conversation_id")
    assert conv_id is not None

    # 2. List history
    list_resp = await client.get("/api/history")
    assert list_resp.status_code == 200
    data = list_resp.json()
    items = data if isinstance(data, list) else data.get("items", [])
    assert len(items) >= 1

    # 3. Get conversation detail
    detail_resp = await client.get(f"/api/history/{conv_id}")
    assert detail_resp.status_code == 200

    # 4. Delete conversation
    del_resp = await client.delete(f"/api/history/{conv_id}")
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_chat_endpoint_frontend_compatibility(client):
    chat_payload = {
        "message": "My tomato leaves are turning yellow",
        "language": "en",
        "farmer_id": "farmer-01",
        "conversation_id": None,
    }
    resp = await client.post("/api/chat", json=chat_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "conversation_id" in data
    assert "data" in data
    assert isinstance(data["data"]["sources"], list)
    assert data["data"]["possible_issue"] is not None
