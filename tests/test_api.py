from io import BytesIO
from urllib.parse import quote

import httpx
import respx
from fastapi.testclient import TestClient
from inline_snapshot import snapshot
from PIL import Image

from app.main import app

client = TestClient(app)


def create_test_image(width: int = 100, height: int = 100, color=(255, 0, 0)) -> bytes:
    """Helper to create a test image as bytes."""
    img = Image.new("RGB", (width, height), color)
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    return img_bytes.getvalue()


@respx.mock
def test_generate_image_meme_endpoint():
    """Test the /img/{image_url} endpoint."""
    # Mock image download
    test_img = create_test_image(200, 200, (0, 255, 0))
    image_url = "https://example.com/test-logo.png?token=abc&format=png"
    respx.get(image_url).mock(return_value=httpx.Response(200, content=test_img))

    response = client.get(
        f"/img/{quote(image_url, safe='')}",
        params={
            "filename": "test-meme.png",
        },
    )

    assert response.status_code == snapshot(200)
    assert response.headers["content-type"] == snapshot("image/png")
    assert "old-man-yells-at-test-meme.png" in response.headers["content-disposition"]

    # Verify it's a valid PNG
    img = Image.open(BytesIO(response.content))
    assert img.format == snapshot("PNG")
    assert img.mode == snapshot("RGBA")


@respx.mock
def test_generate_logo_meme_uses_logo_dev_for_bare_search():
    """Test the /{search} endpoint treats bare words as logo searches."""
    logo_api_response = [
        {
            "name": "FastAPI",
            "domain": "fastapi.tiangolo.com",
            "logo_url": "https://logo.dev/fastapi",
        }
    ]
    test_logo = create_test_image(300, 300, (0, 150, 120))

    respx.get("https://api.logo.dev/search").mock(
        return_value=httpx.Response(200, json=logo_api_response)
    )
    respx.get("https://logo.dev/fastapi?format=png").mock(
        return_value=httpx.Response(200, content=test_logo)
    )

    response = client.get("/fastapi")

    assert response.status_code == snapshot(200)
    assert response.headers["content-type"] == snapshot("image/png")
    assert "old-man-yells-at-fastapi.png" in response.headers["content-disposition"]


@respx.mock
def test_probe_paths_do_not_call_logo_dev():
    """Test common scanner/probe paths are rejected before Logo.dev lookup."""
    logo_api_route = respx.get("https://api.logo.dev/search").mock(
        return_value=httpx.Response(200, json=[])
    )

    for path in (
        "/admin",
        "/api",
        "/wp-admin",
        "/wp-login.php",
        "/wplogin.php",
        "/xmlrpc.php",
        "/.env",
        "/favicon.ico",
        "/robots.txt",
        "/server-status",
    ):
        response = client.get(path)
        assert response.status_code == 404

    assert not logo_api_route.called


@respx.mock
def test_generate_x_meme():
    """Test the /x/{handle} endpoint pulls an X profile photo."""
    avatar = create_test_image(200, 200, (29, 161, 242))

    respx.get("https://x.com/elonmusk").mock(
        return_value=httpx.Response(
            200,
            text=(
                '<meta property="og:image" '
                'content="https://pbs.twimg.com/profile_images/elon_400x400.jpg">'
            ),
        )
    )
    respx.get("https://pbs.twimg.com/profile_images/elon_400x400.jpg").mock(
        return_value=httpx.Response(200, content=avatar)
    )

    response = client.get("/x/elonmusk")

    assert response.status_code == snapshot(200)
    assert response.headers["content-type"] == snapshot("image/png")
    assert "old-man-yells-at-elonmusk.png" in response.headers["content-disposition"]


@respx.mock
def test_generate_github_meme():
    """Test the /gh/{handle} endpoint pulls a GitHub avatar."""
    avatar = create_test_image(200, 200, (20, 20, 20))

    respx.get("https://github.com/torvalds.png?size=460").mock(
        return_value=httpx.Response(200, content=avatar)
    )

    response = client.get("/gh/torvalds")

    assert response.status_code == snapshot(200)
    assert response.headers["content-type"] == snapshot("image/png")
    assert "old-man-yells-at-torvalds.png" in response.headers["content-disposition"]


@respx.mock
def test_generate_logo_meme_filename():
    """Test the /{search} endpoint uses the standard save filename."""
    logo_api_response = [
        {
            "name": "Python",
            "domain": "python.org",
            "logo_url": "https://logo.dev/python",
        }
    ]
    test_logo = create_test_image(300, 300, (50, 100, 200))

    respx.get("https://api.logo.dev/search").mock(
        return_value=httpx.Response(200, json=logo_api_response)
    )
    respx.get("https://logo.dev/python?format=png").mock(
        return_value=httpx.Response(200, content=test_logo)
    )

    response = client.get("/python.org")

    assert response.status_code == snapshot(200)
    assert response.headers["content-type"] == snapshot("image/png")
    assert "old-man-yells-at-python.org.png" in response.headers["content-disposition"]


@respx.mock
def test_generate_logo_meme_invalid_search():
    """Test Logo API with special characters."""
    logo_api_response = []

    respx.get("https://api.logo.dev/search").mock(
        return_value=httpx.Response(200, json=logo_api_response)
    )

    response = client.get("/invalid!@#$%.com")

    assert response.status_code == snapshot(404)
