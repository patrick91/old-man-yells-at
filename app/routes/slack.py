"""Slack slash command routes."""

import hashlib
import hmac
import time

from fastapi import APIRouter, HTTPException, Request
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

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


@router.post("/slack/commands/old-man-yells-at")
async def old_man_yells_at(request: Request):
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
    channel_id = str(form_data.get("channel_id", ""))

    # Validate input
    if not text or not text.strip():
        return {
            "response_type": "ephemeral",
            "text": "Please provide a username or domain! Usage: `/old-man-yells-at @username` or `/old-man-yells-at company.com`",
        }

    target = text.strip()

    try:
        # Import here to avoid circular dependency
        from app.services.logo_api import search_logo
        from app.services.twitter import get_twitter_avatar, is_twitter_username

        # Determine if it's a Twitter username or company domain
        if is_twitter_username(target):
            image_url = await get_twitter_avatar(target)
        else:
            image_url = await search_logo(target)

        # Generate the meme
        meme_bytes = await generate_meme(image_url)

        # Upload to Slack if we have a bot token
        if config.SLACK_BOT_TOKEN and channel_id:
            client = WebClient(token=config.SLACK_BOT_TOKEN)

            # Upload the file to the channel where the command was invoked
            client.files_upload_v2(
                channel=channel_id,
                file=meme_bytes,
                filename=f"old-man-yells-at-{target.replace('@', '')}.png",
                title=f"Old Man Yells At {target}",
            )

            # Return empty response - the file upload will show the image
            return {"text": ""}
        else:
            # If no bot token, just return a message
            return {
                "response_type": "ephemeral",
                "text": f"✅ Meme generated for {target}! (Configure SLACK_BOT_TOKEN to upload images)",
            }

    except SlackApiError as e:
        return {
            "response_type": "ephemeral",
            "text": f"Failed to upload to Slack: {e.response['error']}",
        }
    except HTTPException as e:
        return {
            "response_type": "ephemeral",
            "text": f"Error: {e.detail}",
        }
    except Exception as e:
        return {
            "response_type": "ephemeral",
            "text": f"An unexpected error occurred: {str(e)}",
        }
