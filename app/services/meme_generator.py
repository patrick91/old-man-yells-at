"""Meme generation service."""

import io

from PIL import Image, ImageDraw, ImageFont

from app.config import (
    DEFAULT_LEFT_ANCHOR,
    DEFAULT_LEFT_PADDING,
    DEFAULT_MAX_HEIGHT,
    DEFAULT_MAX_WIDTH,
    DEFAULT_TOP_ANCHOR,
    DEFAULT_TOP_PADDING,
    TEMPLATE_PATH,
    TEXT_FONT_PATH,
)
from app.services.image_downloader import download_image
from app.utils.image import resize_image, trim_image

# Load the template image
template_image = Image.open(TEMPLATE_PATH)

TEXT_CARD_WIDTH = 215
TEXT_MAX_HEIGHT = 150
TEXT_HORIZONTAL_PADDING = 16
TEXT_VERTICAL_PADDING = 16
TEXT_MAX_FONT_SIZE = 48
TEXT_MIN_FONT_SIZE = 18
TEXT_LINE_SPACING_RATIO = 7
TEXT_CARD_RADIUS = 14
TEXT_CARD_BORDER_WIDTH = 5
TEXT_CARD_SHADOW_OFFSET = 5

PYTHON_YELLOW = (255, 212, 59, 255)
PYTHON_BLUE = (48, 105, 152, 255)
PYTHON_TEXT = (36, 61, 84, 255)
TEXT_CARD_SHADOW = (15, 37, 57, 70)


async def generate_meme(image_url: str) -> bytes:
    """
    Generate a meme by combining the template with a downloaded image.

    Args:
        image_url: URL of the image to use in the meme

    Returns:
        The generated meme as PNG bytes
    """
    input_image = await download_image(image_url)
    return compose_meme(input_image)


def _load_text_font(size: int) -> ImageFont.FreeTypeFont:
    """Load the bundled display font at its semibold variation."""
    font = ImageFont.truetype(TEXT_FONT_PATH, size=size)
    font.set_variation_by_name("SemiBold")
    return font


def _line_width(
    draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont
) -> int:
    """Measure a single line of rendered text."""
    left, _, right, _ = _text_box(draw, text, font)
    return right - left


def _text_box(
    draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont
) -> tuple[int, int, int, int]:
    """Return Pillow text bounds normalized to integer pixel coordinates."""
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    return round(left), round(top), round(right), round(bottom)


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    """Wrap text greedily without splitting individual words."""
    lines: list[str] = []
    current = ""

    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and _line_width(draw, candidate, font) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate

    if current:
        lines.append(current)

    return lines


def render_text_target(text: str) -> Image.Image:
    """Render a Python-colored term card for use as a meme target."""
    label = text.upper()
    measure = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    max_width = TEXT_CARD_WIDTH - (TEXT_HORIZONTAL_PADDING * 2)

    for font_size in range(TEXT_MAX_FONT_SIZE, TEXT_MIN_FONT_SIZE - 1, -1):
        font = _load_text_font(font_size)
        lines = _wrap_text(measure, label, font, max_width)
        spacing = max(4, font_size // TEXT_LINE_SPACING_RATIO)
        boxes = [_text_box(measure, line, font) for line in lines]
        text_width = max(box[2] - box[0] for box in boxes)
        text_height = sum(box[3] - box[1] for box in boxes)
        text_height += spacing * (len(lines) - 1)

        if text_width <= max_width and text_height <= TEXT_MAX_HEIGHT:
            break
    else:
        raise ValueError("Text is too long to render")

    card_height = text_height + (TEXT_VERTICAL_PADDING * 2)
    image = Image.new(
        "RGBA",
        (
            TEXT_CARD_WIDTH + TEXT_CARD_SHADOW_OFFSET,
            card_height + TEXT_CARD_SHADOW_OFFSET,
        ),
        (0, 0, 0, 0),
    )
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle(
        (
            TEXT_CARD_SHADOW_OFFSET,
            TEXT_CARD_SHADOW_OFFSET,
            TEXT_CARD_WIDTH + 1,
            card_height + 1,
        ),
        radius=TEXT_CARD_RADIUS,
        fill=TEXT_CARD_SHADOW,
    )
    draw.rounded_rectangle(
        (0, 0, TEXT_CARD_WIDTH - 1, card_height - 1),
        radius=TEXT_CARD_RADIUS,
        fill=PYTHON_YELLOW,
        outline=PYTHON_BLUE,
        width=TEXT_CARD_BORDER_WIDTH,
    )

    y_position = TEXT_VERTICAL_PADDING
    for line, box in zip(lines, boxes, strict=True):
        width = box[2] - box[0]
        height = box[3] - box[1]
        x_position = (TEXT_CARD_WIDTH - width) // 2
        draw.text(
            (x_position, y_position - box[1]),
            line,
            font=font,
            fill=PYTHON_TEXT,
        )
        y_position += height + spacing

    return image


def generate_text_meme(text: str) -> bytes:
    """Generate a meme yelling at a rendered text target."""
    return compose_meme(render_text_target(text))


def compose_meme(input_image: Image.Image) -> bytes:
    """
    Combine the template with an already-loaded image and return PNG bytes.

    Args:
        input_image: The image to place into the old man's line of fire

    Returns:
        The generated meme as PNG bytes
    """
    left_anchor = DEFAULT_LEFT_ANCHOR
    top_anchor = DEFAULT_TOP_ANCHOR
    max_width = DEFAULT_MAX_WIDTH
    max_height = DEFAULT_MAX_HEIGHT

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
