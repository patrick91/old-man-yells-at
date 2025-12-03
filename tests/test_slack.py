"""Tests for Slack slash command integration."""

import hashlib
import hmac
import time
import urllib.parse
from io import BytesIO
from unittest.mock import patch

import httpx
import respx
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

client = TestClient(app)


def create_test_image(width: int = 100, height: int = 100, color=(255, 0, 0)) -> bytes:
    """Helper to create a test image as bytes."""
    img = Image.new("RGB", (width, height), color)
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    return img_bytes.getvalue()


def create_slack_signature(data: dict, timestamp: str, secret: str) -> str:
    """Create a valid Slack signature for testing."""
    # URL-encode the data just like FastAPI/Starlette does
    body = urllib.parse.urlencode(data)
    sig_basestring = f"v0:{timestamp}:{body}"
    signature = (
        "v0="
        + hmac.new(
            secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256,
        ).hexdigest()
    )
    return signature


def test_slack_command_without_text():
    """Test slash command without any text argument."""
    timestamp = str(int(time.time()))
    data = {
        "text": "",
        "response_url": "https://hooks.slack.com/commands/123",
    }
    secret = "test-secret"
    signature = create_slack_signature(data, timestamp, secret)

    with patch("app.config.SLACK_SIGNING_SECRET", secret):
        response = client.post(
            "/slack/commands/old-man-yells-at",
            data=data,
            headers={
                "X-Slack-Request-Timestamp": timestamp,
                "X-Slack-Signature": signature,
            },
        )

    assert response.status_code == 200
    assert "Please provide a username or domain" in response.json()["text"]
    assert response.json()["response_type"] == "ephemeral"


@respx.mock
def test_slack_command_with_twitter_username():
    """Test slash command with a Twitter username."""
    # Mock Twitter profile page
    html_content = """
    <html>
    <head>
        <meta property="og:image" content="https://pbs.twimg.com/profile_images/123/avatar_200x200.jpg" />
    </head>
    </html>
    """

    respx.get("https://x.com/patrick91").mock(
        return_value=httpx.Response(200, text=html_content)
    )

    # Mock avatar download
    test_img = create_test_image(400, 400)
    respx.get("https://pbs.twimg.com/profile_images/123/avatar_400x400.jpg").mock(
        return_value=httpx.Response(200, content=test_img)
    )

    # Mock Slack response_url webhook
    respx.post("https://hooks.slack.com/commands/123").mock(
        return_value=httpx.Response(200, text="ok")
    )

    timestamp = str(int(time.time()))
    data = {
        "text": "@patrick91",
        "response_url": "https://hooks.slack.com/commands/123",
    }
    secret = "test-secret"
    signature = create_slack_signature(data, timestamp, secret)

    with patch("app.config.SLACK_SIGNING_SECRET", secret):
        response = client.post(
            "/slack/commands/old-man-yells-at",
            data=data,
            headers={
                "X-Slack-Request-Timestamp": timestamp,
                "X-Slack-Signature": signature,
            },
        )

    assert response.status_code == 200
    json_response = response.json()
    assert "Yelling at @patrick91" in json_response["text"]
    assert json_response["response_type"] == "ephemeral"


@respx.mock
def test_slack_command_with_company_domain():
    """Test slash command with a company domain."""
    # Mock Logo API response
    logo_api_response = [
        {
            "name": "Python",
            "domain": "python.org",
            "logo_url": "https://logo.dev/python",
        }
    ]

    respx.get("https://api.logo.dev/search").mock(
        return_value=httpx.Response(200, json=logo_api_response)
    )

    # Mock logo download
    test_logo = create_test_image(300, 300)
    respx.get("https://logo.dev/python&format=png").mock(
        return_value=httpx.Response(200, content=test_logo)
    )

    # Mock Slack response_url webhook
    respx.post("https://hooks.slack.com/commands/123").mock(
        return_value=httpx.Response(200, text="ok")
    )

    timestamp = str(int(time.time()))
    data = {
        "text": "python.org",
        "response_url": "https://hooks.slack.com/commands/123",
    }
    secret = "test-secret"
    signature = create_slack_signature(data, timestamp, secret)

    with patch("app.config.SLACK_SIGNING_SECRET", secret):
        response = client.post(
            "/slack/commands/old-man-yells-at",
            data=data,
            headers={
                "X-Slack-Request-Timestamp": timestamp,
                "X-Slack-Signature": signature,
            },
        )

    assert response.status_code == 200
    json_response = response.json()
    assert "python.org" in json_response["text"]


def test_slack_command_invalid_signature():
    """Test that requests with invalid signatures are rejected."""
    timestamp = str(int(time.time()))
    invalid_signature = "v0=invalid_signature"

    with patch("app.config.SLACK_SIGNING_SECRET", "test-secret"):
        response = client.post(
            "/slack/commands/old-man-yells-at",
            data={
                "text": "@patrick91",
                "response_url": "https://hooks.slack.com/commands/123",
            },
            headers={
                "X-Slack-Request-Timestamp": timestamp,
                "X-Slack-Signature": invalid_signature,
            },
        )

    assert response.status_code == 403
    assert "Invalid request signature" in response.json()["detail"]


def test_slack_command_old_timestamp():
    """Test that requests with old timestamps are rejected."""
    # Create a timestamp from 10 minutes ago
    old_timestamp = str(int(time.time()) - 600)
    data = {
        "text": "@patrick91",
        "response_url": "https://hooks.slack.com/commands/123",
    }
    secret = "test-secret"
    signature = create_slack_signature(data, old_timestamp, secret)

    with patch("app.config.SLACK_SIGNING_SECRET", secret):
        response = client.post(
            "/slack/commands/old-man-yells-at",
            data=data,
            headers={
                "X-Slack-Request-Timestamp": old_timestamp,
                "X-Slack-Signature": signature,
            },
        )

    assert response.status_code == 403
