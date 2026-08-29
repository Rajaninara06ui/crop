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
    items = list_resp.json()["items"]
    assert len(items) >= 1

    # 3. Get conversation detail
    detail_resp = await client.get(f"/api/history/{conv_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert len(detail["messages"]) >= 2  # user + assistant

    # 4. Delete conversation
    del_resp = await client.delete(f"/api/history/{conv_id}")
    assert del_resp.status_code == 204

    # 5. Confirm deletion
    get_again = await client.get(f"/api/history/{conv_id}")
    assert get_again.status_code == 404
