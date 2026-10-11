"""Loader for dummy Home Assistant."""
from unittest.mock import AsyncMock, MagicMock

async def async_get_integration(hass, domain):
    integration = MagicMock()
    integration.version = "5.0.0"
    return integration
