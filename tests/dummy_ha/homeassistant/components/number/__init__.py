"""Number component for dummy Home Assistant."""
from homeassistant.helpers.entity import Entity

class NumberMode:
    AUTO = "auto"
    BOX = "box"
    SLIDER = "slider"

class NumberEntity(Entity):
    pass
