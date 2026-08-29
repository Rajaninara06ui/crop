import io
import pytest
from PIL import Image


def _create_test_image_bytes():
    img = Image.new("RGB", (100, 100), color="green")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_disease_detection_valid_image(client):
    img_bytes = _create_test_image_bytes()
    files = {"image": ("leaf.jpg", io.BytesIO(img_bytes), "image/jpeg")}
    resp = await client.post("/api/disease/detect", files=files, data={"crop": "tomato"})
    assert resp.status_code == 200
    data = resp.json()
    assert "possible_disease" in data
    assert "confidence" in data
    assert "recommended_treatment" in data
    assert "prevention" in data
    assert data["confidence"] >= 0.70


@pytest.mark.asyncio
async def test_disease_detection_invalid_format(client):
    files = {"image": ("test.pdf", io.BytesIO(b"%PDF-1.4 mock"), "application/pdf")}
    resp = await client.post("/api/disease/detect", files=files)
    assert resp.status_code == 415
