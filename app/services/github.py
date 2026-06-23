"""GitHub integration service."""


def github_avatar_url(username: str) -> str:
    """
    Build the avatar image URL for a GitHub username.

    GitHub serves a user's avatar at ``https://github.com/<username>.png``,
    which redirects to the underlying avatar image with no auth required.

    Args:
        username: GitHub username, with or without a leading @

    Returns:
        The URL of the user's avatar image
    """
    username = username.lstrip("@")
    return f"https://github.com/{username}.png?size=460"
