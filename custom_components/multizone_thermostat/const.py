"""Constants for Multizone Thermostat integration."""

DOMAIN = "multizone_thermostat"

# Config keys
CONF_BOILER_SWITCH = "boiler_switch"
CONF_ZONES = "zones"
CONF_ZONE_NAME = "name"
CONF_ZONE_CLIMATE = "climate_entity"
CONF_ZONE_TRV_SYNC = "trv_preset_sync"
CONF_ZONE_ENABLED = "enabled"

# Storage keys
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.zone_states"

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
