"""Visual regression tests for meme generation using pytest-image-snapshot."""

from io import BytesIO

import httpx
import respx
from fastapi.testclient import TestClient
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
def test_generate_meme_snapshot(image_snapshot):
    """Test meme generation with visual snapshot."""
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

    # Compare the generated meme with the snapshot
    # Use a threshold for anti-aliasing tolerance (0.1 = 10% difference allowed)
    image = Image.open(BytesIO(response.content))
    image_snapshot(image, "tests/snapshots/test_generate_meme.png", threshold=0.1)


@respx.mock
def test_twitter_meme_snapshot(image_snapshot):
    """Test Twitter meme generation with visual snapshot."""
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
    assert "old-man-yells-at-patrick91.png" in response.headers["content-disposition"]

    # Verify the generated meme matches the snapshot
    image = Image.open(BytesIO(response.content))
    image_snapshot(image, "tests/snapshots/test_twitter_meme.png", threshold=0.1)


@respx.mock
def test_logo_meme_snapshot(image_snapshot):
    """Test logo meme generation with visual snapshot."""
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

    # Store the generated meme as a visual snapshot
    image = Image.open(BytesIO(response.content))
    image_snapshot(image, "tests/snapshots/test_logo_meme.png", threshold=0.1)


@respx.mock
def test_meme_with_large_image_snapshot(image_snapshot):
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
    image = Image.open(BytesIO(response.content))
    image_snapshot(image, "tests/snapshots/test_large_image_meme.png", threshold=0.1)

    # Verify it's a valid PNG with expected properties
    assert image.format == "PNG"
    assert image.mode == "RGBA"
