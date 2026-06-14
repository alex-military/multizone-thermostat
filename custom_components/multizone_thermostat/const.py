"""Constants for Multizone Thermostat integration."""

DOMAIN = "multizone_thermostat"

# Config keys
CONF_BOILER_SWITCH = "boiler_switch"
CONF_ZONES = "zones"
CONF_ZONE_NAME = "name"
CONF_ZONE_CLIMATE = "climate_entity"
CONF_ZONE_TRV_SYNC = "trv_preset_sync"
CONF_ZONE_WINDOW_SENSOR = "window_sensor"

# Protection keys
CONF_MIN_CYCLE_ON = "min_cycle_on"
CONF_MIN_CYCLE_OFF = "min_cycle_off"
CONF_VALVE_DELAY = "valve_opening_delay"


# HVAC
HVAC_MODE_HEAT = "heat"
HVAC_MODE_OFF = "off"
HVAC_ACTION_HEATING = "heating"
HVAC_ACTION_IDLE = "idle"

# Preset modes (for TRV sync)
PRESET_MANUAL = "manual"
PRESET_OFF = "off"

# Entity prefixes
SWITCH_MASTER_SUFFIX = "master"
SWITCH_ZONE_PREFIX = "zone"

# Default values
DEFAULT_TRV_SYNC = False
DEFAULT_MIN_CYCLE_ON = 5
DEFAULT_MIN_CYCLE_OFF = 5
DEFAULT_VALVE_DELAY = 0

# Virtual Thermostat keys
CONF_VIRTUAL_THERMOSTATS = "virtual_thermostats"
CONF_VT_TEMP_SENSOR = "temperature_sensor"
CONF_VT_HEATER_SWITCH = "heater_switch"
CONF_VT_NAME = "name"
CONF_VT_TARGET_TEMP = "target_temperature"
CONF_VT_TOLERANCE = "tolerance"
DEFAULT_VT_TARGET_TEMP = 20.0
DEFAULT_VT_TOLERANCE = 0.5


def make_vt_entity_id(name: str) -> str:
    """Generate a predictable entity_id for a virtual thermostat."""
    safe = name.lower().replace(" ", "_").replace("-", "_")
    safe = "".join(c for c in safe if c.isalnum() or c == "_")
    return f"climate.{DOMAIN}_vt_{safe}"
