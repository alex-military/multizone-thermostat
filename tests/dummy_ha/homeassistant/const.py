"""Constants for dummy Home Assistant."""
from enum import StrEnum

ATTR_ENTITY_ID = "entity_id"
ATTR_TEMPERATURE = "temperature"
ATTR_NAME = "name"
ATTR_FRIENDLY_NAME = "friendly_name"

SERVICE_TURN_ON = "turn_on"
SERVICE_TURN_OFF = "turn_off"
SERVICE_SET_TEMPERATURE = "set_temperature"

STATE_ON = "on"
STATE_OFF = "off"
STATE_UNAVAILABLE = "unavailable"
STATE_UNKNOWN = "unknown"

HVAC_MODE_HEAT = "heat"
HVAC_MODE_OFF = "off"

CONF_NAME = "name"
PERCENTAGE = "%"

class Platform(StrEnum):
    CLIMATE = "climate"
    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"
    SWITCH = "switch"
    SELECT = "select"
    NUMBER = "number"
    TIME = "time"

class UnitOfTemperature(StrEnum):
    CELSIUS = "°C"
    FAHRENHEIT = "°F"
