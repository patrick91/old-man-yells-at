from inline_snapshot import snapshot
from PIL import Image

from app.utils.image import resize_image, trim_image


def test_resize_image_larger_than_max():
    """Test resizing an image that's larger than max dimensions."""
    # Create a large test image
    img = Image.new("RGBA", (800, 600), (255, 0, 0, 255))

    resized = resize_image(img, max_width=400, max_height=230)

    # Should fit within max dimensions while maintaining aspect ratio
    assert resized.width <= 400
    assert resized.height <= 230
    # Check aspect ratio is maintained (800/600 = 4/3)
    assert abs(resized.width / resized.height - 800 / 600) < 0.01
    assert resized.width == snapshot(306)
    assert resized.height == snapshot(230)


def test_resize_image_smaller_than_max():
    """Test that small images aren't upscaled."""
    # Create a small test image
    img = Image.new("RGBA", (100, 80), (0, 255, 0, 255))

    resized = resize_image(img, max_width=400, max_height=230)

    # Should remain the same size
    assert resized.width == snapshot(100)
    assert resized.height == snapshot(80)


def test_resize_image_width_constrained():
    """Test resizing when width is the constraining dimension."""
    # Create an image that's too wide
    img = Image.new("RGBA", (800, 200), (0, 0, 255, 255))

    resized = resize_image(img, max_width=400, max_height=230)

    # Width should be constrained to max_width
    assert resized.width == snapshot(400)
    assert resized.height == snapshot(100)


def test_resize_image_height_constrained():
    """Test resizing when height is the constraining dimension."""
    # Create an image that's too tall
    img = Image.new("RGBA", (100, 500), (255, 255, 0, 255))

    resized = resize_image(img, max_width=400, max_height=230)

    # Height should be constrained to max_height
    assert resized.width == snapshot(46)
    assert resized.height == snapshot(230)


def test_trim_image_with_transparency():
    """Test trimming transparent borders from an image."""
    # Create an image with transparent borders
    img = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    # Add a solid rectangle in the middle
    for x in range(50, 150):
        for y in range(60, 140):
            img.putpixel((x, y), (255, 0, 0, 255))

    trimmed = trim_image(img)

    # Should be trimmed to just the solid rectangle
    assert trimmed.width == snapshot(100)
    assert trimmed.height == snapshot(80)


def test_trim_image_with_padding():
    """Test trimming with added padding."""
    # Create an image with transparent borders
    img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    # Add a solid rectangle
    for x in range(25, 75):
        for y in range(25, 75):
            img.putpixel((x, y), (0, 255, 0, 255))

    trimmed = trim_image(img, top_padding=10, left_padding=20)

    # Should be trimmed + padding
    assert trimmed.width == snapshot(70)  # 50 + 20 left padding
    assert trimmed.height == snapshot(60)  # 50 + 10 top padding


def test_trim_image_converts_to_rgba():
    """Test that RGB images are converted to RGBA before trimming."""
    # Create an RGB image (no alpha channel)
    img = Image.new("RGB", (100, 100), (255, 255, 255))

    trimmed = trim_image(img)

    # Should be converted to RGBA
    assert trimmed.mode == snapshot("RGBA")


def test_trim_image_all_transparent():
    """Test trimming an image that's completely transparent."""
    # Create a completely transparent image
    img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))

    trimmed = trim_image(img)

    # Should return the original image if all pixels are transparent
    assert trimmed.size == snapshot((100, 100))
