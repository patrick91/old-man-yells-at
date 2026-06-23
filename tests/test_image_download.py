from io import BytesIO

import httpx
import pytest
import respx
from inline_snapshot import snapshot
from PIL import Image

from app.services.image_downloader import download_image


@pytest.mark.asyncio
@respx.mock
async def test_download_png_image():
    """Test downloading a PNG image."""
    # Create a simple test image
    img = Image.new("RGB", (100, 100), (255, 0, 0))
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    # Mock the HTTP request
    respx.get("https://example.com/test.png").mock(
        return_value=httpx.Response(200, content=img_bytes.read())
    )

    # Download the image
    downloaded = await download_image("https://example.com/test.png")

    assert downloaded.size == snapshot((100, 100))
    assert downloaded.mode == snapshot("RGB")


@pytest.mark.asyncio
@respx.mock
async def test_download_jpeg_image():
    """Test downloading a JPEG image."""
    # Create a test JPEG image
    img = Image.new("RGB", (200, 150), (0, 255, 0))
    img_bytes = BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)

    # Mock the HTTP request
    respx.get("https://example.com/test.jpg").mock(
        return_value=httpx.Response(200, content=img_bytes.read())
    )

    # Download the image
    downloaded = await download_image("https://example.com/test.jpg")

    assert downloaded.size == snapshot((200, 150))
    assert downloaded.mode == snapshot("RGB")


@pytest.mark.asyncio
@respx.mock
async def test_download_image_with_redirect():
    """Test downloading an image that requires following redirects."""
    # Create a test image
    img = Image.new("RGB", (50, 50), (0, 0, 255))
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    # Mock redirect chain
    respx.get("https://example.com/redirect").mock(
        return_value=httpx.Response(
            302, headers={"Location": "https://example.com/final.png"}
        )
    )
    respx.get("https://example.com/final.png").mock(
        return_value=httpx.Response(200, content=img_bytes.read())
    )

    # Download the image (should follow redirects)
    downloaded = await download_image("https://example.com/redirect")

    assert downloaded.size == snapshot((50, 50))


@pytest.mark.asyncio
@respx.mock
async def test_download_image_404():
    """Test handling of 404 errors."""
    # Mock a 404 response
    respx.get("https://example.com/notfound.png").mock(return_value=httpx.Response(404))

    # Should raise an exception
    with pytest.raises(httpx.HTTPStatusError):
        await download_image("https://example.com/notfound.png")
