"""Twitter/X integration service."""

import re

import httpx
from fastapi import HTTPException


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

    Raises:
        HTTPException: If the avatar cannot be found
    """
    # Remove @ if present
    username = username.lstrip("@")

    # Fetch the Twitter profile page with a bot user agent
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
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
