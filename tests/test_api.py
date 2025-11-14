from io import BytesIO

import httpx
import respx
from fastapi.testclient import TestClient
from inline_snapshot import snapshot
from PIL import Image

from main import app

client = TestClient(app)


def create_test_image(width: int = 100, height: int = 100, color=(255, 0, 0)) -> bytes:
    """Helper to create a test image as bytes."""
    img = Image.new("RGB", (width, height), color)
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    return img_bytes.getvalue()


@respx.mock
def test_generate_meme_endpoint():
    """Test the /generate-meme endpoint."""
    # Mock image download
    test_img = create_test_image(200, 200, (0, 255, 0))
    respx.get("https://example.com/test-logo.png").mock(
        return_value=httpx.Response(200, content=test_img)
    )

    response = client.get(
        "/generate-meme",
        params={
            "image_url": "https://example.com/test-logo.png",
            "filename": "test-meme.png",
        },
    )

    assert response.status_code == snapshot(200)
    assert response.headers["content-type"] == snapshot("image/png")
    assert "test-meme.png" in response.headers["content-disposition"]

    # Verify it's a valid PNG
    img = Image.open(BytesIO(response.content))
    assert img.format == snapshot("PNG")
    assert img.mode == snapshot("RGBA")


@respx.mock
def test_generate_logo_meme_invalid_search():
    """Test Logo API with special characters."""
    logo_api_response = []

    respx.get("https://api.logo.dev/search").mock(
        return_value=httpx.Response(200, json=logo_api_response)
    )

    response = client.get("/invalid!@#$%.com")

    assert response.status_code == snapshot(404)
