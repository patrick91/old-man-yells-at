import io
import os
import re
from io import BytesIO

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from PIL import Image

try:
    import cairosvg
except Exception:
    print("Unable to import cairosvg")

    HAS_CAIRO = False
else:
    HAS_CAIRO = True

app = FastAPI(title="Meme Generator API")

# Load the template image
TEMPLATE_PATH = os.path.join("assets", "template.png")
template_image = Image.open(TEMPLATE_PATH)

LOGO_API_TOKEN = os.getenv(
    "LOGO_API_TOKEN", "REDACTED_TOKEN"
)  # Get token from environment variable


def is_svg_url(url: str) -> bool:
    """Check if the URL points to an SVG file."""
    return bool(re.search(r"\.svg$", url, re.IGNORECASE))


async def download_image(url: str) -> Image.Image:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        content = response.content

        if is_svg_url(url):
            if HAS_CAIRO:
                # Convert SVG to PNG using cairosvg
                png_data = cairosvg.svg2png(bytestring=content)
                return Image.open(BytesIO(png_data))
            else:
                raise HTTPException(status_code=500, detail="Cairo is not installed")
        else:
            print("opening image")
            return Image.open(BytesIO(content))


def resize_image(
    image: Image.Image, max_width: int = 400, max_height: int = 230
) -> Image.Image:
    """
    Resize an image while maintaining its aspect ratio and respecting maximum dimensions.

    Args:
        image: The input image to resize
        max_width: Maximum width of the resized image
        max_height: Maximum height of the resized image

    Returns:
        The resized image
    """
    # Calculate the aspect ratio
    width, height = image.size
    aspect_ratio = width / height

    # Calculate new dimensions while maintaining aspect ratio
    if width > max_width:
        new_width = max_width
        new_height = int(new_width / aspect_ratio)
    else:
        new_width = width
        new_height = height

    if new_height > max_height:
        new_height = max_height
        new_width = int(new_height * aspect_ratio)

    # Resize the image
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)


def trim_image(
    image: Image.Image, top_padding: int = 0, left_padding: int = 0
) -> Image.Image:
    """
    Trim transparent or white areas from an image and optionally add padding.

    Args:
        image: The input image to trim
        top_padding: Amount of padding to add to the top
        left_padding: Amount of padding to add to the left

    Returns:
        The trimmed image with optional padding
    """
    # Convert to RGBA if not already
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    # Get the alpha channel
    alpha = image.getchannel("A")

    # Find non-transparent pixels
    bbox = alpha.getbbox()
    if bbox is None:
        return image  # Return original if all pixels are transparent

    # Crop the image to the bounding box
    trimmed = image.crop(bbox)

    # Add padding if specified
    if top_padding > 0 or left_padding > 0:
        new_width = trimmed.width + left_padding
        new_height = trimmed.height + top_padding
        padded = Image.new("RGBA", (new_width, new_height), (0, 0, 0, 0))
        padded.paste(trimmed, (left_padding, top_padding))
        return padded

    return trimmed


@app.get("/generate-meme")
async def generate_meme(image_url: str):
    left_anchor = 230
    top_anchor = 230
    max_width = 300
    max_height = 230

    input_image = await download_image(image_url)

    trimmed_image = trim_image(input_image)
    resized_image = resize_image(trimmed_image, max_width, max_height)

    # Calculate if the image will overflow
    x_position = left_anchor - resized_image.width
    y_position = top_anchor - resized_image.height

    # Calculate the required canvas expansion
    left_expansion = max(0, -x_position)
    top_expansion = max(0, -y_position)

    # Create a new canvas with expanded dimensions if needed
    if left_expansion > 0 or top_expansion > 0:
        new_width = template_image.width + left_expansion
        new_height = template_image.height + top_expansion
        new_canvas = Image.new("RGBA", (new_width, new_height), (0, 0, 0, 0))

        # Paste the template at the new position
        new_canvas.paste(template_image, (left_expansion, top_expansion))

        # Adjust the paste position for the resized image
        x_position += left_expansion
        y_position += top_expansion
    else:
        new_canvas = template_image.copy()

    # Paste the resized image onto the canvas
    new_canvas.paste(resized_image, (x_position, y_position))

    # Trim the final meme to remove any transparent or white areas
    final_meme = trim_image(new_canvas, top_padding=30, left_padding=30)

    # Convert the image to bytes
    img_byte_arr = io.BytesIO()
    final_meme.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)

    return StreamingResponse(img_byte_arr, media_type="image/png")


def is_twitter_username(text: str) -> bool:
    """Check if the text looks like a Twitter username."""
    return bool(re.match(r"^@?[A-Za-z0-9_]{1,15}$", text))


async def get_twitter_avatar(username: str) -> str:
    """
    Get profile image URL directly from Twitter/X by scraping the profile page.

    Args:
        username: Username (with or without @)

    Returns:
        Profile image URL from Twitter/X
    """
    # Remove @ if present
    username = username.lstrip("@")

    # Fetch the Twitter profile page with a bot user agent
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(
            f"https://x.com/{username}",
            headers={
                "user-agent": "Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)"
            },
        )
        response.raise_for_status()

        # Extract og:image from the HTML (handle both attribute orders)
        match = re.search(
            r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', response.text
        ) or re.search(
            r'<meta[^>]+content="([^"]+)"[^>]+property="og:image"', response.text
        )
        if not match:
            raise HTTPException(
                status_code=404, detail=f"Could not find avatar for @{username}"
            )

        avatar_url = match.group(1)

        # Upgrade to higher resolution if possible
        if avatar_url.endswith("_200x200.jpg"):
            avatar_url = avatar_url.replace("_200x200.jpg", "_400x400.jpg")

        return avatar_url


@app.get("/{search}")
async def generate_logo_meme(search: str):
    """
    Generate a meme using a company logo from Logo.dev API or profile image from unavatar.io.

    Args:
        search: The company domain (e.g., 'microsoft.com') or username (e.g., '@patrick91')
    """
    # Check if it's a Twitter username
    if is_twitter_username(search):
        # Get profile image directly from Twitter/X
        image_url = await get_twitter_avatar(search)

        return await generate_meme(image_url)

    # Use Logo API for company logos
    if not LOGO_API_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="Logo API token not configured. Please set LOGO_API_TOKEN environment variable.",
        )

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.logo.dev/search",
            params={"q": search},
            headers={"Authorization": f"Bearer: {LOGO_API_TOKEN}"},
        )
        response.raise_for_status()
        logos = response.json()

        if not logos:
            raise HTTPException(
                status_code=404, detail="No logos found for the given search query"
            )

        logo_url = logos[0]["logo_url"] + "&format=png"

    # Use the existing generate_meme function with the logo URL
    return await generate_meme(logo_url)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
