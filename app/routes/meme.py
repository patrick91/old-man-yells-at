"""Meme generation routes."""

import re
from pathlib import PurePath

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.services.github import github_avatar_url
from app.services.logo_api import search_logo
from app.services.meme_generator import generate_meme as generate_meme_bytes
from app.services.twitter import get_twitter_avatar, is_twitter_username

router = APIRouter()


def _meme_filename(name: str | None = None) -> str:
    """Return the download filename used by all meme routes."""
    filename = PurePath(name or "meme").name.strip() or "meme"
    if filename.lower().endswith(".png"):
        filename = filename[:-4]

    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", filename).strip(".-_") or "meme"
    prefix = "old-man-yells-at-"

    if stem.startswith(prefix):
        return f"{stem}.png"

    return f"{prefix}{stem}.png"


async def _stream_meme(image_url: str, filename: str = "meme.png") -> StreamingResponse:
    """Generate a meme from an image URL and stream it back as a PNG."""
    meme_bytes = await generate_meme_bytes(image_url)
    download_filename = _meme_filename(filename)
    return StreamingResponse(
        iter([meme_bytes]),
        media_type="image/png",
        headers={"Content-Disposition": f'inline; filename="{download_filename}"'},
    )


@router.get("/generate-meme")
async def generate_meme(image_url: str, filename: str = "meme.png"):
    """
    Generate a meme from an arbitrary image URL.

    Args:
        image_url: URL of the image to use
        filename: Optional filename for the generated meme
    """
    return await _stream_meme(image_url, filename)


@router.get("/x/{handle}")
async def generate_x_meme(handle: str):
    """
    Generate a meme yelling at an X (Twitter) user's profile photo.

    Args:
        handle: X username, with or without a leading @
    """
    username = handle.lstrip("@")
    image_url = await get_twitter_avatar(username)
    return await _stream_meme(image_url, username)


@router.get("/gh/{handle}")
async def generate_github_meme(handle: str):
    """
    Generate a meme yelling at a GitHub user's avatar.

    Args:
        handle: GitHub username, with or without a leading @
    """
    username = handle.lstrip("@")
    image_url = github_avatar_url(username)
    return await _stream_meme(image_url, username)


@router.get("/{search}")
async def generate_logo_meme(search: str):
    """
    Generate a meme from a company logo (Logo.dev) or an X/Twitter profile photo.

    Args:
        search: A company domain (e.g. 'microsoft.com') or username (e.g. '@patrick91')
    """
    # Check if it's a Twitter/X username
    if is_twitter_username(search):
        username = search.lstrip("@")
        image_url = await get_twitter_avatar(username)
        return await _stream_meme(image_url, username)

    # Otherwise treat it as a company domain and use the Logo API
    logo_url = await search_logo(search)
    return await _stream_meme(logo_url, search)
