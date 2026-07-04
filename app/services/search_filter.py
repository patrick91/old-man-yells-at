"""Filtering for user-provided logo search targets."""

from urllib.parse import unquote

_BLOCKED_SEARCH_EXACT = {
    "admin",
    "administrator",
    "api",
    "apple-touch-icon-precomposed.png",
    "apple-touch-icon.png",
    "cgi-bin",
    "config",
    "dashboard",
    "debug",
    "env",
    "favicon.ico",
    "health",
    "healthz",
    "live",
    "livez",
    "login",
    "metrics",
    "mysql",
    "phpmyadmin",
    "pma",
    "ready",
    "readyz",
    "robots.txt",
    "server-info",
    "server-status",
    "sitemap.xml",
    "wp-admin",
    "wp-content",
    "wp-includes",
    "wp-json",
    "wp-login.php",
    "xmlrpc.php",
}

_BLOCKED_SEARCH_EXTENSIONS = (
    ".7z",
    ".asp",
    ".aspx",
    ".bak",
    ".cgi",
    ".conf",
    ".config",
    ".css",
    ".env",
    ".gif",
    ".gz",
    ".ico",
    ".ini",
    ".jpeg",
    ".jpg",
    ".json",
    ".jsp",
    ".log",
    ".map",
    ".old",
    ".php",
    ".pl",
    ".png",
    ".rar",
    ".sql",
    ".svg",
    ".tar",
    ".tgz",
    ".txt",
    ".webp",
    ".xml",
    ".zip",
)

_BLOCKED_SEARCH_PREFIXES = (
    ".",
    "admin-",
    "wp-",
)

_BLOCKED_SEARCH_MARKERS = (
    "..",
    "\\",
    "<",
    ">",
)


def is_blocked_search(search: str) -> bool:
    """Return whether the catch-all search looks like a bot/probe path."""
    normalized = unquote(search).strip().strip("/").lower()

    if not normalized:
        return True

    if normalized in _BLOCKED_SEARCH_EXACT:
        return True

    if normalized.startswith(_BLOCKED_SEARCH_PREFIXES):
        return True

    if normalized.endswith(_BLOCKED_SEARCH_EXTENSIONS):
        return True

    return any(marker in normalized for marker in _BLOCKED_SEARCH_MARKERS)
