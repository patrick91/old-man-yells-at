"""Meme generation routes."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.services.logo_api import search_logo
from app.services.meme_generator import generate_meme as generate_meme_bytes
from app.services.twitter import get_twitter_avatar, is_twitter_username

router = APIRouter()


@router.get("/generate-meme")
async def generate_meme(image_url: str, filename: str = "meme.png"):
    """
    Generate a meme from an image URL.

    Args:
        image_url: URL of the image to use
        filename: Optional filename for the generated meme

    Returns:
        StreamingResponse with the generated meme
    """
    meme_bytes = await generate_meme_bytes(image_url)

    return StreamingResponse(
        iter([meme_bytes]),
        media_type="image/png",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/{search}")
async def generate_logo_meme(search: str):
    """
    Generate a meme using a company logo from Logo.dev API or profile image from Twitter/X.

    Args:
        search: The company domain (e.g., 'microsoft.com') or username (e.g., '@patrick91')
    """
    # Check if it's a Twitter username
    if is_twitter_username(search):
        # Get profile image directly from Twitter/X
        image_url = await get_twitter_avatar(search)
        # Remove @ if present for filename
        username = search.lstrip("@")
        filename = f"old-man-yells-at-{username}.png"

        meme_bytes = await generate_meme_bytes(image_url)

        return StreamingResponse(
            iter([meme_bytes]),
            media_type="image/png",
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )

    # Use Logo API for company logos
    logo_url = await search_logo(search)

    # Use the existing generate_meme function with the logo URL
    meme_bytes = await generate_meme_bytes(logo_url)

    return StreamingResponse(
        iter([meme_bytes]),
        media_type="image/png",
        headers={"Content-Disposition": 'inline; filename="meme.png"'},
    )
