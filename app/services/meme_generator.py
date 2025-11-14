"""Meme generation service."""

import io

from PIL import Image

from app.config import (
    DEFAULT_LEFT_ANCHOR,
    DEFAULT_LEFT_PADDING,
    DEFAULT_MAX_HEIGHT,
    DEFAULT_MAX_WIDTH,
    DEFAULT_TOP_ANCHOR,
    DEFAULT_TOP_PADDING,
    TEMPLATE_PATH,
)
from app.services.image_downloader import download_image
from app.utils.image import resize_image, trim_image

# Load the template image
template_image = Image.open(TEMPLATE_PATH)


async def generate_meme(image_url: str) -> bytes:
    """
    Generate a meme by combining the template with a downloaded image.

    Args:
        image_url: URL of the image to use in the meme

    Returns:
        The generated meme as PNG bytes
    """
    left_anchor = DEFAULT_LEFT_ANCHOR
    top_anchor = DEFAULT_TOP_ANCHOR
    max_width = DEFAULT_MAX_WIDTH
    max_height = DEFAULT_MAX_HEIGHT

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
    final_meme = trim_image(
        new_canvas, top_padding=DEFAULT_TOP_PADDING, left_padding=DEFAULT_LEFT_PADDING
    )

    # Convert the image to bytes
    img_byte_arr = io.BytesIO()
    final_meme.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)

    return img_byte_arr.getvalue()
