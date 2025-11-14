from io import BytesIO

import httpx
import pytest
import respx
from inline_snapshot import snapshot
from PIL import Image

from app.services.image_downloader import HAS_CAIRO, download_image, is_svg_url


def test_is_svg_url():
    """Test SVG URL detection."""
    assert is_svg_url("https://example.com/logo.svg") == snapshot(True)
    assert is_svg_url("https://example.com/logo.SVG") == snapshot(True)
    assert is_svg_url("https://example.com/logo.png") == snapshot(False)
    assert is_svg_url("https://example.com/image.jpg") == snapshot(False)


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
@pytest.mark.skipif(not HAS_CAIRO, reason="Cairo not installed")
async def test_download_svg_image():
    """Test downloading and converting an SVG image."""
    # Simple SVG content
    svg_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
  <rect width="100" height="100" fill="blue"/>
</svg>"""

    # Mock the HTTP request
    respx.get("https://example.com/test.svg").mock(
        return_value=httpx.Response(200, content=svg_content)
    )

    # Download and convert the SVG
    downloaded = await download_image("https://example.com/test.svg")

    # Should be converted to PNG
    assert downloaded.mode in ["RGB", "RGBA"]
    assert downloaded.width > 0
    assert downloaded.height > 0


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


@pytest.mark.asyncio
@respx.mock
@pytest.mark.skipif(HAS_CAIRO, reason="Test only when Cairo is not installed")
async def test_download_svg_without_cairo():
    """Test that SVG download fails gracefully without Cairo."""
    from fastapi import HTTPException

    svg_content = b'<svg width="100" height="100"></svg>'

    respx.get("https://example.com/test.svg").mock(
        return_value=httpx.Response(200, content=svg_content)
    )

    # Should raise HTTPException when Cairo is not available
    with pytest.raises(HTTPException) as exc_info:
        await download_image("https://example.com/test.svg")

    assert exc_info.value.status_code == snapshot(500)
    assert "Cairo" in exc_info.value.detail
