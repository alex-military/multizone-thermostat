"""Button component for dummy Home Assistant."""
from homeassistant.helpers.entity import Entity

DOMAIN = "button"


class ButtonEntity(Entity):
    """Dummy ButtonEntity."""

    async def async_press(self) -> None:
        """Press the button."""
