from io import BytesIO

import httpx
import respx
from fastapi.testclient import TestClient
from inline_snapshot import snapshot
from PIL import Image

from app.main import app

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
def test_generate_x_meme():
    """Test the /x/{handle} endpoint pulls an X profile photo."""
    avatar = create_test_image(200, 200, (29, 161, 242))

    respx.get("https://x.com/elonmusk").mock(
        return_value=httpx.Response(
            200,
            text=(
                '<meta property="og:image" '
                'content="https://pbs.twimg.com/profile_images/elon_400x400.jpg">'
            ),
        )
    )
    respx.get("https://pbs.twimg.com/profile_images/elon_400x400.jpg").mock(
        return_value=httpx.Response(200, content=avatar)
    )

    response = client.get("/x/elonmusk")

    assert response.status_code == snapshot(200)
    assert response.headers["content-type"] == snapshot("image/png")
    assert "old-man-yells-at-elonmusk.png" in response.headers["content-disposition"]


@respx.mock
def test_generate_github_meme():
    """Test the /gh/{handle} endpoint pulls a GitHub avatar."""
    avatar = create_test_image(200, 200, (20, 20, 20))

    respx.get("https://github.com/torvalds.png?size=460").mock(
        return_value=httpx.Response(200, content=avatar)
    )

    response = client.get("/gh/torvalds")

    assert response.status_code == snapshot(200)
    assert response.headers["content-type"] == snapshot("image/png")
    assert "old-man-yells-at-torvalds.png" in response.headers["content-disposition"]


@respx.mock
def test_generate_logo_meme_invalid_search():
    """Test Logo API with special characters."""
    logo_api_response = []

    respx.get("https://api.logo.dev/search").mock(
        return_value=httpx.Response(200, json=logo_api_response)
    )

    response = client.get("/invalid!@#$%.com")

    assert response.status_code == snapshot(404)
