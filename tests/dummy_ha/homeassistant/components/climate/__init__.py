"""Climate component for dummy Home Assistant."""
from .const import (
    DOMAIN,
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
    ATTR_HVAC_MODE,
    ATTR_CURRENT_TEMPERATURE,
    ATTR_TEMPERATURE,
    ATTR_PRESET_MODE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
    SERVICE_SET_PRESET_MODE,
    PRESET_NONE,
    PRESET_AWAY,
    PRESET_ECO,
    PRESET_COMFORT,
    PRESET_BOOST,
    PRESET_SLEEP,
    PRESET_ACTIVITY,
)
from homeassistant.helpers.entity import Entity

class ClimateEntity(Entity):
    pass
