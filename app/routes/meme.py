"""Meme generation routes."""

import re
from pathlib import PurePath
from urllib.parse import unquote, urlsplit

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.services.github import github_avatar_url
from app.services.logo_api import search_logo
from app.services.meme_generator import generate_meme, generate_text_meme
from app.services.search_filter import is_blocked_search
from app.services.twitter import get_twitter_avatar

router = APIRouter()

MAX_PYTHON_TERM_LENGTH = 80
MAX_PYTHON_TERM_WORD_LENGTH = 24


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


def _stream_meme_bytes(meme_bytes: bytes, filename: str) -> StreamingResponse:
    """Stream generated meme bytes back as a consistently named PNG."""
    download_filename = _meme_filename(filename)
    return StreamingResponse(
        iter([meme_bytes]),
        media_type="image/png",
        headers={"Content-Disposition": f'inline; filename="{download_filename}"'},
    )


async def _stream_meme(image_url: str, filename: str = "meme.png") -> StreamingResponse:
    """Generate a meme from an image URL and stream it back as a PNG."""
    return _stream_meme_bytes(await generate_meme(image_url), filename)


def _filename_from_image_url(image_url: str) -> str:
    """Return a useful default download filename for an arbitrary image URL."""
    parsed = urlsplit(image_url)
    return PurePath(unquote(parsed.path)).name or parsed.netloc or "image"


@router.get("/img/{image_url:path}")
async def generate_image_meme(image_url: str, filename: str | None = None):
    """
    Generate a meme from an arbitrary image URL.

    Args:
        image_url: URL-encoded image URL to use
        filename: Optional filename for the generated meme
    """
    decoded_image_url = unquote(image_url)
    return await _stream_meme(
        decoded_image_url, filename or _filename_from_image_url(decoded_image_url)
    )


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


def _python_term_label(term: str) -> str:
    """Turn a URL-friendly Python term into safe display text."""
    label = " ".join(unquote(term).replace("-", " ").split())

    if (
        not label
        or len(label) > MAX_PYTHON_TERM_LENGTH
        or any(len(word) > MAX_PYTHON_TERM_WORD_LENGTH for word in label.split())
        or not label.isprintable()
    ):
        raise HTTPException(status_code=404, detail="Not a supported Python term")

    return label


@router.get("/py/{term}")
def generate_python_term_meme(term: str):
    """Generate a meme yelling at a literal Python glossary term."""
    label = _python_term_label(term)
    return _stream_meme_bytes(generate_text_meme(label), term)


@router.get("/{search}")
async def generate_logo_meme(search: str):
    """
    Generate a meme from a company logo using Logo.dev.

    Args:
        search: A company domain or brand name (e.g. 'microsoft.com')
    """
    if is_blocked_search(search):
        raise HTTPException(status_code=404, detail="Not a supported meme target")

    logo_url = await search_logo(search)
    return await _stream_meme(logo_url, search)
