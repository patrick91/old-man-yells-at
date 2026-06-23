"""FastAPI meme generator application."""

import io
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response
from PIL import Image

from app.routes.meme import router as meme_router
from app.routes.slack import router as slack_router
from app.services.image_downloader import download_image
from app.services.meme_generator import compose_meme
from app.utils.image import trim_image

app = FastAPI(title="Meme Generator API")

STATIC_DIR = Path(__file__).parent / "static"
ASSETS_DIR = Path(__file__).parent.parent / "assets"

# Google (Noto) emoji, rendered by emojicdn — openly licensed, unlike Apple's set.
# The old man yells at the visitor's flag, or at the whole world when we can't tell.
EMOJI_CDN = "https://emojicdn.elk.sh/{emoji}?style=google"
WORLD_EMOJI = "🌍"

# Cache the generated favicon per country code (plus "world").
_favicon_cache: dict[str, bytes] = {}


def _build_favicon() -> bytes:
    """Render a tight favicon from the old-man template, trimming transparent margins."""
    image = trim_image(Image.open(ASSETS_DIR / "template.png"))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


FAVICON_BYTES = _build_favicon()


def _visitor_country(request: Request) -> str | None:
    """Read the visitor's ISO country code from Cloudflare's geo header.

    Cloudflare sets CF-IPCountry on every request; "XX" (unknown) and "T1" (Tor)
    have no flag, so they fall through to the world favicon.
    """
    code = (request.headers.get("cf-ipcountry") or "").strip().upper()
    if len(code) == 2 and code.isalpha() and code != "XX":
        return code
    return None


def _flag_emoji(country: str) -> str:
    """Turn an ISO country code into its flag emoji (regional indicator symbols)."""
    return "".join(chr(0x1F1E6 + ord(char) - ord("A")) for char in country)


async def _yell_at_emoji(emoji: str) -> bytes:
    """Build the old-man meme yelling at an emoji, scaled up to fill the frame."""
    image = trim_image(await download_image(EMOJI_CDN.format(emoji=emoji)))
    # Emoji art is small (~160px); scale it up so it fills the frame like a flag.
    if image.width < 300:
        ratio = 300 / image.width
        image = image.resize(
            (300, max(1, round(image.height * ratio))), Image.Resampling.LANCZOS
        )
    return compose_meme(image)


async def _favicon_for(country: str | None) -> bytes:
    """Generate (and cache) the old man yelling at a national flag, or the world."""
    key = country or "world"
    if key not in _favicon_cache:
        emoji = _flag_emoji(country) if country else WORLD_EMOJI
        _favicon_cache[key] = await _yell_at_emoji(emoji)
    return _favicon_cache[key]


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    """Serve the landing page."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/logo.png", include_in_schema=False)
async def logo() -> Response:
    """Serve the plain old-man logo used in the page header and footer."""
    return Response(content=FAVICON_BYTES, media_type="image/png")


@app.get("/favicon.png", include_in_schema=False)
async def favicon(request: Request) -> Response:
    """Old man yells at the favicon — at the visitor's flag, or the whole world."""
    try:
        body = await _favicon_for(_visitor_country(request))
    except Exception:
        # Any flag/meme failure falls back to the plain old man.
        body = FAVICON_BYTES

    return Response(
        content=body,
        media_type="image/png",
        # Per-visitor: keep shared caches from serving one country's flag to everyone.
        headers={"Cache-Control": "private, max-age=86400"},
    )


# Include routers
app.include_router(meme_router)
app.include_router(slack_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
