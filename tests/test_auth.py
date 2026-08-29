import pytest


@pytest.mark.asyncio
async def test_register_success(client):
    payload = {
        "name": "Ramesh Kumar",
        "email": "ramesh@example.com",
        "password": "password123",
        "preferred_language": "te",
        "location": "Guntur, Andhra Pradesh",
    }
    resp = await client.post("/api/auth/register", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    payload = {
        "name": "Ramesh Kumar",
        "email": "duplicate@example.com",
        "password": "password123",
    }
    resp1 = await client.post("/api/auth/register", json=payload)
    assert resp1.status_code == 201

    resp2 = await client.post("/api/auth/register", json=payload)
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client):
    # Register first
    await client.post(
        "/api/auth/register",
        json={"name": "Suresh", "email": "suresh@example.com", "password": "securepass123"},
    )
    # Login
    resp = await client.post(
        "/api/auth/login",
        json={"email": "suresh@example.com", "password": "securepass123"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    resp = await client.post(
        "/api/auth/login",
        json={"email": "wrong@example.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_me(client):
    reg_resp = await client.post(
        "/api/auth/register",
        json={"name": "Anita", "email": "anita@example.com", "password": "password123"},
    )
    token = reg_resp.json()["access_token"]
    resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "anita@example.com"
