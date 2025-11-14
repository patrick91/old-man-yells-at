"""Logo API integration service."""

import httpx
from fastapi import HTTPException

from app.config import LOGO_API_TOKEN


async def search_logo(query: str) -> str:
    """
    Search for a company logo using the Logo API.

    Args:
        query: The search query (e.g., company domain)

    Returns:
        The URL of the logo image

    Raises:
        HTTPException: If no logo is found or the API token is not configured
    """
    if not LOGO_API_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="Logo API token not configured. Please set LOGO_API_TOKEN environment variable.",
        )

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.logo.dev/search",
            params={"q": query},
            headers={"Authorization": f"Bearer: {LOGO_API_TOKEN}"},
        )
        response.raise_for_status()
        logos = response.json()

        if not logos:
            raise HTTPException(
                status_code=404, detail="No logos found for the given search query"
            )

        logo_url = logos[0]["logo_url"] + "&format=png"
        return logo_url
