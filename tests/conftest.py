"""Pytest configuration and fixtures."""

from inline_snapshot import register_format_alias

# Register .png as an alias for .bin format so PNG files are stored as binary
# This needs to happen at module import time
register_format_alias(".png", ".bin")
