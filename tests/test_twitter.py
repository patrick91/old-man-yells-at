import httpx
import pytest
import respx
from inline_snapshot import snapshot

from app.services.twitter import get_twitter_avatar, is_twitter_username


def test_is_twitter_username():
    """Test Twitter username validation."""
    # Valid usernames
    assert is_twitter_username("patrick91") == snapshot(True)
    assert is_twitter_username("@patrick91") == snapshot(True)
    assert is_twitter_username("user_name") == snapshot(True)
    assert is_twitter_username("@User_123") == snapshot(True)
    assert is_twitter_username("a") == snapshot(True)

    # Invalid usernames
    assert is_twitter_username("user-name") == snapshot(False)  # Hyphens not allowed
    assert is_twitter_username("this_is_way_too_long_username") == snapshot(
        False
    )  # Too long
    assert is_twitter_username("user name") == snapshot(False)  # Spaces not allowed
    assert is_twitter_username("") == snapshot(False)  # Empty


@pytest.mark.asyncio
@respx.mock
async def test_get_twitter_avatar_success():
    """Test successfully fetching a Twitter avatar."""
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

    avatar_url = await get_twitter_avatar("patrick91")

    # Should upgrade to higher resolution
    assert avatar_url == snapshot(
        "https://pbs.twimg.com/profile_images/123/avatar_400x400.jpg"
    )


@pytest.mark.asyncio
@respx.mock
async def test_get_twitter_avatar_with_at_symbol():
    """Test fetching avatar when username has @ prefix."""
    html_content = """
    <html>
    <head>
        <meta property="og:image" content="https://pbs.twimg.com/profile_images/456/photo_200x200.jpg" />
    </head>
    </html>
    """

    respx.get("https://x.com/testuser").mock(
        return_value=httpx.Response(200, text=html_content)
    )

    # Pass username with @ symbol
    avatar_url = await get_twitter_avatar("@testuser")

    assert avatar_url == snapshot(
        "https://pbs.twimg.com/profile_images/456/photo_400x400.jpg"
    )


@pytest.mark.asyncio
@respx.mock
async def test_get_twitter_avatar_alternate_meta_order():
    """Test parsing og:image with alternate attribute order."""
    html_content = """
    <html>
    <head>
        <meta content="https://pbs.twimg.com/profile_images/789/img_200x200.jpg" property="og:image" />
    </head>
    </html>
    """

    respx.get("https://x.com/user123").mock(
        return_value=httpx.Response(200, text=html_content)
    )

    avatar_url = await get_twitter_avatar("user123")

    assert avatar_url == snapshot(
        "https://pbs.twimg.com/profile_images/789/img_400x400.jpg"
    )


@pytest.mark.asyncio
@respx.mock
async def test_get_twitter_avatar_no_upgrade():
    """Test avatar URL that doesn't need resolution upgrade."""
    html_content = """
    <html>
    <head>
        <meta property="og:image" content="https://pbs.twimg.com/profile_images/999/avatar.jpg" />
    </head>
    </html>
    """

    respx.get("https://x.com/someuser").mock(
        return_value=httpx.Response(200, text=html_content)
    )

    avatar_url = await get_twitter_avatar("someuser")

    # Should return as-is since it doesn't end with _200x200.jpg
    assert avatar_url == snapshot("https://pbs.twimg.com/profile_images/999/avatar.jpg")


@pytest.mark.asyncio
@respx.mock
async def test_get_twitter_avatar_not_found():
    """Test handling of non-existent user."""
    html_content = "<html><head></head><body>User not found</body></html>"

    respx.get("https://x.com/nonexistentuser").mock(
        return_value=httpx.Response(200, text=html_content)
    )

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await get_twitter_avatar("nonexistentuser")

    assert exc_info.value.status_code == snapshot(404)
    assert "nonexistentuser" in exc_info.value.detail


@pytest.mark.asyncio
@respx.mock
async def test_get_twitter_avatar_http_error():
    """Test handling of HTTP errors."""
    respx.get("https://x.com/erroruser").mock(return_value=httpx.Response(500))

    with pytest.raises(httpx.HTTPStatusError):
        await get_twitter_avatar("erroruser")


@pytest.mark.asyncio
@respx.mock
async def test_get_twitter_avatar_with_redirect():
    """Test following redirects to get avatar."""
    html_content = """
    <html>
    <head>
        <meta property="og:image" content="https://pbs.twimg.com/profile_images/redirect/avatar_200x200.jpg" />
    </head>
    </html>
    """

    respx.get("https://x.com/redirectuser").mock(
        return_value=httpx.Response(
            302, headers={"Location": "https://x.com/redirectuser"}
        )
    )
    respx.get("https://x.com/redirectuser").mock(
        return_value=httpx.Response(200, text=html_content)
    )

    avatar_url = await get_twitter_avatar("redirectuser")

    assert "https://pbs.twimg.com" in avatar_url
