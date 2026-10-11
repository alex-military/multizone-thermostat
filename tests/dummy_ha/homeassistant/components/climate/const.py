"""Climate constants for dummy Home Assistant."""
from enum import StrEnum

DOMAIN = "climate"

class HVACMode(StrEnum):
    OFF = "off"
    HEAT = "heat"
    COOL = "cool"
    HEAT_COOL = "heat_cool"
    AUTO = "auto"
    DRY = "dry"
    FAN_ONLY = "fan_only"

class HVACAction(StrEnum):
    OFF = "off"
    HEATING = "heating"
    COOLING = "cooling"
    IDLE = "idle"
    FAN = "fan"
    DEFROSTING = "defrosting"

class ClimateEntityFeature:
    TARGET_TEMPERATURE = 1
    TARGET_TEMPERATURE_RANGE = 2
    TARGET_HUMIDITY = 4
    FAN_MODE = 8
    PRESET_MODE = 16
    SWING_MODE = 32
    TURN_OFF = 128
    TURN_ON = 256

ATTR_HVAC_MODE = "hvac_mode"
ATTR_CURRENT_TEMPERATURE = "current_temperature"
ATTR_TEMPERATURE = "temperature"
ATTR_PRESET_MODE = "preset_mode"

SERVICE_SET_HVAC_MODE = "set_hvac_mode"
SERVICE_SET_TEMPERATURE = "set_temperature"
SERVICE_SET_PRESET_MODE = "set_preset_mode"

PRESET_NONE = "none"
PRESET_AWAY = "away"
PRESET_ECO = "eco"
PRESET_COMFORT = "comfort"
PRESET_BOOST = "boost"
PRESET_SLEEP = "sleep"
PRESET_ACTIVITY = "activity"
