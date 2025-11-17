"""Application configuration and constants."""

import os

# Logo API configuration
LOGO_API_TOKEN = os.getenv("LOGO_API_TOKEN", "REDACTED_TOKEN")

# Slack configuration
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")

# Template configuration
TEMPLATE_PATH = os.path.join("assets", "template.png")

# Meme generation configuration
DEFAULT_LEFT_ANCHOR = 230
DEFAULT_TOP_ANCHOR = 230
DEFAULT_MAX_WIDTH = 300
DEFAULT_MAX_HEIGHT = 230
DEFAULT_TOP_PADDING = 30
DEFAULT_LEFT_PADDING = 30
