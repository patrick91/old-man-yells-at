"""Image downloading service."""

from io import BytesIO

import httpx
from PIL import Image


async def download_image(url: str) -> Image.Image:
    """
    Download an image from a URL.

    Args:
        url: The URL to download the image from

    Returns:
        The downloaded image as a PIL Image
    """
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))
