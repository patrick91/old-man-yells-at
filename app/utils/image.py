"""Image processing utilities."""

from PIL import Image


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
