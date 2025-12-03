"""Pytest configuration and fixtures."""

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def mock_logo_api_token():
    """Automatically mock LOGO_API_TOKEN for all tests."""
    with patch("app.services.logo_api.LOGO_API_TOKEN", "test-token"):
        yield
