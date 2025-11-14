from io import BytesIO

import httpx
import respx
from fastapi.testclient import TestClient
from inline_snapshot import external, register_format_alias, snapshot
from PIL import Image

from main import app

# Register .png as an alias for .bin format so PNG files are stored as binary
register_format_alias(".png", ".bin")

client = TestClient(app)


def create_test_image(width: int = 100, height: int = 100, color=(255, 0, 0)) -> bytes:
    """Helper to create a test image as bytes."""
    img = Image.new("RGB", (width, height), color)
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    return img_bytes.getvalue()


@respx.mock
def test_generate_meme_snapshot():
    """Test meme generation with external PNG snapshot."""
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

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"

    # Use external snapshot to store the generated PNG
    assert response.content == external("uuid:5261deeb-bfc5-41ec-8d2a-422df4d126da.png")


@respx.mock
def test_twitter_meme_snapshot():
    """Test Twitter meme generation with external PNG snapshot."""
    # Mock Twitter profile page
    html_content = """
    <html>
    <head>
        <meta property="og:image" content="https://pbs.twimg.com/profile_images/123/avatar_200x200.jpg" />
    </head>
    </html>
    """

    respx.get("https://x.com/patrick91").mock(
        return_value=httpx.Response(200, text=html_content)
    )

    # Mock avatar download
    test_avatar = create_test_image(400, 400, (100, 150, 200))
    respx.get("https://pbs.twimg.com/profile_images/123/avatar_400x400.jpg").mock(
        return_value=httpx.Response(200, content=test_avatar)
    )

    response = client.get("/@patrick91")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"

    # Verify the generated meme matches the snapshot
    assert response.content == external("uuid:6e6290a7-0654-4cce-8062-f8dd3fc4ca6b.png")

    # Also verify the filename
    assert "old-man-yells-at-patrick91.png" in response.headers["content-disposition"]


@respx.mock
def test_logo_meme_snapshot():
    """Test logo meme generation with external PNG snapshot."""
    # Mock Logo API response
    logo_api_response = [
        {
            "name": "Python",
            "domain": "python.org",
            "logo_url": "https://logo.dev/python",
        }
    ]

    respx.get("https://api.logo.dev/search").mock(
        return_value=httpx.Response(200, json=logo_api_response)
    )

    # Mock the logo image download
    test_logo = create_test_image(300, 300, (50, 100, 200))
    respx.get("https://logo.dev/python&format=png").mock(
        return_value=httpx.Response(200, content=test_logo)
    )

    response = client.get("/python.org")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"

    # Store the generated meme as an external PNG snapshot
    assert response.content == external("uuid:e65f8727-b1d2-4521-9950-3985d02d9a8c.png")


@respx.mock
def test_meme_with_large_image_snapshot():
    """Test meme generation with a large image that gets resized."""
    # Create a large test image
    test_img = create_test_image(800, 600, (255, 100, 50))
    respx.get("https://example.com/large.png").mock(
        return_value=httpx.Response(200, content=test_img)
    )

    response = client.get(
        "/generate-meme", params={"image_url": "https://example.com/large.png"}
    )

    assert response.status_code == 200

    # Verify the resized meme matches the snapshot
    assert response.content == external("uuid:7085fd54-e1d9-4855-9ba9-9c3d71225a25.png")

    # Verify it's a valid PNG with expected properties
    img = Image.open(BytesIO(response.content))
    assert img.format == snapshot("PNG")
    assert img.mode == snapshot("RGBA")
