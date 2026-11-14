"""Number component for dummy Home Assistant."""
from homeassistant.helpers.entity import Entity

DOMAIN = "number"

class NumberMode:
    AUTO = "auto"
    BOX = "box"
    SLIDER = "slider"

class NumberEntity(Entity):
    pass


class RestoreNumber(NumberEntity):
    async def async_get_last_number_data(self):
        return None

