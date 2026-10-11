"""Number component for dummy Home Assistant."""
from homeassistant.helpers.entity import Entity

DOMAIN = "number"

class NumberMode:
    AUTO = "auto"
    BOX = "box"
    SLIDER = "slider"

class NumberEntity(Entity):
    pass

