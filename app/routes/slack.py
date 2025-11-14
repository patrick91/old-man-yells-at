"""Slack slash command routes."""

import hashlib
import hmac
import json
import time

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app import config
from app.services.meme_generator import generate_meme

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


async def generate_and_send_meme(target: str, response_url: str, base_url: str):
    """Background task to generate meme and send ephemeral preview with button."""
    try:
        # Import here to avoid circular dependency
        from urllib.parse import quote

        from app.services.logo_api import search_logo
        from app.services.twitter import get_twitter_avatar, is_twitter_username

        # Determine if it's a Twitter username or company domain
        if is_twitter_username(target):
            image_url = await get_twitter_avatar(target)
        else:
            image_url = await search_logo(target)

        # Generate the meme (this validates the image can be generated)
        await generate_meme(image_url)

        # Create URL for the generated meme
        meme_url = f"{base_url}/generate-meme?image_url={quote(image_url)}"

        # Send ephemeral preview with "Post to Channel" button
        async with httpx.AsyncClient() as client:
            await client.post(
                response_url,
                json={
                    "response_type": "ephemeral",
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
        async with httpx.AsyncClient() as client:
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

    # Get base URL from request
    base_url = f"{request.url.scheme}://{request.url.netloc}"

    # Add background task to generate and send meme
    background_tasks.add_task(generate_and_send_meme, target, response_url, base_url)

    # Return immediate response (Slack requires response within 3 seconds)
    return {
        "response_type": "ephemeral",
        "text": f"🎨 Generating meme for {target}...",
    }


@router.post("/slack/interactivity")
async def handle_interactivity(request: Request):
    """
    Handle Slack interactive components (button clicks, etc.).

    This endpoint receives button click events from Slack.
    """
    try:
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

        print(f"Received interactivity payload: {payload.get('type')}")

        # Handle button click
        if payload.get("type") == "block_actions":
            action = payload["actions"][0]

            if action["action_id"] == "post_meme":
                meme_url = action["value"]

                # Post the meme to the channel using response_url
                response_url = payload["response_url"]

                print(f"Posting meme to channel: {meme_url}")

                async with httpx.AsyncClient() as client:
                    # Post to channel (replace original message with public post)
                    resp = await client.post(
                        response_url,
                        json={
                            "replace_original": True,
                            "response_type": "in_channel",
                            "blocks": [
                                {
                                    "type": "image",
                                    "image_url": meme_url,
                                    "alt_text": "Old Man Yells At Cloud",
                                }
                            ],
                        },
                    )
                    print(f"Slack response: {resp.status_code} - {resp.text}")

                # Return empty response to acknowledge
                return {}

        return {}

    except Exception as e:
        print(f"Error in interactivity handler: {e}")
        import traceback

        traceback.print_exc()
        return {"error": str(e)}
