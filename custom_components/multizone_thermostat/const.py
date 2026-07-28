"""Constants for Multizone Thermostat integration."""

DOMAIN = "multizone_thermostat"

# Config keys
CONF_BOILER_SWITCH = "boiler_switch"
CONF_ZONES = "zones"
CONF_ZONE_NAME = "name"
CONF_ZONE_CLIMATE = "climate_entity"
CONF_ZONE_TRV_SYNC = "trv_preset_sync"
CONF_ZONE_WINDOW_SENSOR = "window_sensor"
CONF_ZONE_ANTI_SEIZE = "anti_seize_zone_enable"

# Geofencing keys
CONF_GEOFENCING_ENABLED = "geofencing_enabled"
CONF_PRESENCE_SENSOR = "presence_sensor"

# Protection keys
CONF_MIN_CYCLE_ON = "min_cycle_on"
CONF_MIN_CYCLE_OFF = "min_cycle_off"
CONF_VALVE_DELAY = "valve_opening_delay"

# Anti-seize configuration constants
CONF_ANTI_SEIZE_ENABLED = "anti_seize_enabled"
CONF_ANTI_SEIZE_IDLE_DAYS = "anti_seize_idle_days"
CONF_ANTI_SEIZE_DURATION = "anti_seize_duration_mins"
CONF_ANTI_SEIZE_BOILER = "anti_seize_boiler_enable"

# Weather Compensation
CONF_WEATHER_SENSOR = "weather_sensor"
KEY_WEATHER_CURVE = "weather_curve"


# HVAC
HVAC_MODE_HEAT = "heat"
HVAC_MODE_OFF = "off"
HVAC_ACTION_HEATING = "heating"
HVAC_ACTION_IDLE = "idle"

# Preset modes (for TRV sync)
PRESET_MANUAL = "manual"
PRESET_OFF = "off"

# Global Presets
GLOBAL_PRESET_MANUAL = "manual"
GLOBAL_PRESET_ECO = "eco"
GLOBAL_PRESET_COMFORT = "comfort"
GLOBAL_PRESET_SLEEP = "sleep"
GLOBAL_PRESET_AWAY = "away"

GLOBAL_PRESETS = [
    GLOBAL_PRESET_MANUAL,
    GLOBAL_PRESET_ECO,
    GLOBAL_PRESET_COMFORT,
    GLOBAL_PRESET_SLEEP,
    GLOBAL_PRESET_AWAY,
]

# Persistent State Keys (Geofencing)
KEY_NIGHT_TIME = "night_time"
KEY_MORNING_TIME = "morning_time"
KEY_PRE_NIGHT_PRESET = "pre_night_preset"

# Mode Selectors for Zones
ZONE_MODE_PRIMARY = "primary"
ZONE_MODE_SECONDARY = "secondary"
ZONE_MODE_BYPASS = "bypass"
ZONE_MODES = [ZONE_MODE_PRIMARY, ZONE_MODE_SECONDARY, ZONE_MODE_BYPASS]
KEY_AUTO_NIGHT_MODE = "auto_night_mode"
KEY_GEOFENCING_TOGGLE = "geofencing_toggle"
KEY_PRE_AWAY_PRESET = "pre_away_preset"

# Persistent State Keys (Anti-seize)
KEY_ANTI_SEIZE_ENABLED = "anti_seize_enabled"
KEY_ANTI_SEIZE_IDLE_DAYS = "anti_seize_idle_days"
KEY_ANTI_SEIZE_DURATION = "anti_seize_duration"

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
