"""Image downloading service."""

import re
from io import BytesIO

import httpx
from fastapi import HTTPException
from PIL import Image

try:
    import cairosvg  # type: ignore[import-not-found]
except Exception:
    print("Unable to import cairosvg")
    cairosvg = None  # type: ignore[assignment]

HAS_CAIRO = cairosvg is not None


def is_svg_url(url: str) -> bool:
    """Check if the URL points to an SVG file."""
    return bool(re.search(r"\.svg$", url, re.IGNORECASE))


async def download_image(url: str) -> Image.Image:
    """
    Download an image from a URL.

    Args:
        url: The URL to download the image from

    Returns:
        The downloaded image as a PIL Image

    Raises:
        HTTPException: If the download fails or Cairo is not installed for SVG
    """
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        content = response.content

        if is_svg_url(url):
            if HAS_CAIRO and cairosvg is not None:
                # Convert SVG to PNG using cairosvg
                png_data = cairosvg.svg2png(bytestring=content)
                if png_data is None:
                    raise HTTPException(
                        status_code=500, detail="Failed to convert SVG to PNG"
                    )
                return Image.open(BytesIO(png_data))
            else:
                raise HTTPException(status_code=500, detail="Cairo is not installed")
        else:
            print("opening image")
            return Image.open(BytesIO(content))
