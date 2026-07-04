"""Slack slash command routes."""

import hashlib
import hmac
import json
import time

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app import config
from app.services.meme_generator import generate_meme
from app.services.search_filter import is_blocked_search

router = APIRouter()


def verify_slack_request(
    body: bytes, timestamp: str, signature: str, signing_secret: str
) -> bool:
    """Verify that the request is from Slack using the signing secret."""
    if abs(time.time() - int(timestamp)) > 60 * 5:
        # Request is older than 5 minutes
        return False

    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    my_signature = (
        "v0="
        + hmac.new(
            signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256,
        ).hexdigest()
    )

    return hmac.compare_digest(my_signature, signature)


async def generate_and_send_meme(target: str, response_url: str, base_url: str) -> None:
    """Background task to generate meme and send ephemeral preview with button."""
    try:
        # Import here to avoid circular dependency
        from urllib.parse import quote, urlencode

        from app.services.logo_api import search_logo
        from app.services.twitter import get_twitter_avatar, is_twitter_username

        if is_blocked_search(target):
            raise ValueError("Not a supported meme target")

        # Determine if it's a Twitter username or company domain
        if target.startswith("@") and is_twitter_username(target):
            image_url = await get_twitter_avatar(target)
        else:
            image_url = await search_logo(target)

        # Generate the meme (this validates the image can be generated)
        await generate_meme(image_url)

        # Create URL for the generated meme
        encoded_image_url = quote(image_url, safe="")
        query_string = urlencode({"filename": target.lstrip("@")})
        meme_url = f"{base_url}/img/{encoded_image_url}?{query_string}"

        # Replace the "Yelling at..." message with ephemeral preview and button
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(
                response_url,
                json={
                    "replace_original": True,
                    "blocks": [
                        {
                            "type": "image",
                            "image_url": meme_url,
                            "alt_text": f"Old Man Yells At {target}",
                        },
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {
                                        "type": "plain_text",
                                        "text": "📣 Post to Channel",
                                    },
                                    "style": "primary",
                                    "value": meme_url,
                                    "action_id": "post_meme",
                                }
                            ],
                        },
                    ],
                },
            )

    except Exception as e:
        # Send error message back to Slack
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(
                response_url,
                json={
                    "response_type": "ephemeral",
                    "text": f"❌ Failed to generate meme: {str(e)}",
                },
            )


@router.post("/slack/commands/old-man-yells-at")
async def old_man_yells_at(request: Request, background_tasks: BackgroundTasks):
    """
    Handle the /old-man-yells-at Slack slash command.

    Expected form data:
        text: The argument passed to the slash command (e.g., "@patrick91" or "python.org")
        response_url: URL to send the response to (for delayed responses)
    """
    # Get headers
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    # Verify the request is from Slack (only if signing secret is configured)
    if config.SLACK_SIGNING_SECRET:
        # Read body for signature verification
        body = await request.body()

        if not verify_slack_request(
            body,
            timestamp,
            signature,
            config.SLACK_SIGNING_SECRET,
        ):
            raise HTTPException(status_code=403, detail="Invalid request signature")

    # Parse form data (body is cached, so this works after reading it)
    form_data = await request.form()
    text = str(form_data.get("text", ""))
    response_url = str(form_data.get("response_url", ""))

    # Validate input
    if not text or not text.strip():
        return {
            "response_type": "ephemeral",
            "text": "Please provide a username or domain! Usage: `/old-man-yells-at @username` or `/old-man-yells-at company.com`",
        }

    target = text.strip()

    if is_blocked_search(target):
        return {
            "response_type": "ephemeral",
            "text": "That looks like a web probe path, not a company or handle.",
        }

    # Get base URL from request
    base_url = f"{request.url.scheme}://{request.url.netloc}"

    # Add background task to generate and send meme
    background_tasks.add_task(generate_and_send_meme, target, response_url, base_url)

    # Return immediate response (Slack requires response within 3 seconds)
    return {
        "response_type": "ephemeral",
        "text": f"👴 Yelling at {target}...",
    }


@router.post("/slack/interactivity")
async def handle_interactivity(request: Request):
    """
    Handle Slack interactive components (button clicks, etc.).

    This endpoint receives button click events from Slack.
    """
    # Get headers for signature verification
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    # Verify the request is from Slack (only if signing secret is configured)
    if config.SLACK_SIGNING_SECRET:
        # Read body for signature verification
        body = await request.body()

        if not verify_slack_request(
            body,
            timestamp,
            signature,
            config.SLACK_SIGNING_SECRET,
        ):
            raise HTTPException(status_code=403, detail="Invalid request signature")

    # Parse form data - Slack sends interactivity payloads as form-encoded
    form_data = await request.form()
    payload = json.loads(str(form_data.get("payload", "{}")))

    # Handle button click
    if payload.get("type") == "block_actions":
        action = payload["actions"][0]

        if action["action_id"] == "post_meme":
            meme_url = action["value"]
            response_url = payload["response_url"]

            # Per Slack docs: "If you include a new message payload and delete_original,
            # the source message will be deleted, and your new message published."
            async with httpx.AsyncClient(timeout=30.0) as client:
                await client.post(
                    response_url,
                    json={
                        "delete_original": True,
                        "response_type": "in_channel",
                        "blocks": [
                            {
                                "type": "image",
                                "image_url": meme_url,
                                "alt_text": "Old Man Yells At Cloud",
                            },
                            {
                                "type": "context",
                                "elements": [
                                    {
                                        "type": "mrkdwn",
                                        "text": "Posted using /old-man-yells-at",
                                    }
                                ],
                            },
                        ],
                    },
                )

            return {}

    return {}
