"""Binary sensor component for dummy Home Assistant."""
from homeassistant.helpers.entity import Entity

class BinarySensorDeviceClass:
    PROBLEM = "problem"
    OPENING = "opening"
    OCCUPANCY = "occupancy"

class BinarySensorEntity(Entity):
    pass
