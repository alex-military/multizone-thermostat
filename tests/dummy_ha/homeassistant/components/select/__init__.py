"""Select component for dummy Home Assistant."""
from homeassistant.helpers.entity import Entity

DOMAIN = "select"

class SelectEntity(Entity):
    _attr_options: list[str] | None = None

    @property
    def options(self) -> list[str]:
        return self._attr_options or []

