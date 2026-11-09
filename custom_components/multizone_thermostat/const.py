"""Constants for Multizone Thermostat integration."""
from __future__ import annotations
from typing import Any

try:
    from homeassistant.util import slugify
except ImportError:
    slugify = None  # type: ignore[assignment]

DOMAIN = "multizone_thermostat"

# Config keys
CONF_BOILER_MODE = "boiler_mode"
MODE_RELAY = "relay"
MODE_OPENTHERM = "opentherm"
CONF_BOILER_SWITCH = "boiler_switch"
CONF_OPENTHERM_ENTITY = "opentherm_entity"
CONF_OPENTHERM_MIN_TEMP = "opentherm_min_temp"
CONF_OPENTHERM_MAX_TEMP = "opentherm_max_temp"
CONF_OPENTHERM_CH_SWITCH = "opentherm_ch_switch"

CONF_ZONES = "zones"
CONF_ZONE_NAME = "name"
CONF_ZONE_CLIMATES = "climate_entities"
CONF_ZONE_SWITCHES = "switch_entities"
CONF_ZONE_TEMP_SENSOR = "temp_sensor"
CONF_ZONE_TARGET_TEMP = "target_temperature"
CONF_ZONE_TRV_SYNC = "trv_preset_sync"
CONF_ZONE_WINDOW_SENSOR = "window_sensor"
CONF_ZONE_ANTI_SEIZE = "anti_seize_zone_enable"
CONF_ZONE_CALIBRATIONS = "calibrations"
CONF_ZONE_VALVES = "valve_entities"
CONF_VALVE_SCALE = "valve_scale"
VALVE_SCALE_PERCENT = "percent"
VALVE_SCALE_VOLT = "volt"
DEFAULT_VALVE_SCALE = VALVE_SCALE_PERCENT
CONF_ZONE_ALLOW_PASSIVE_HEAT = "allow_passive_heat"
CONF_ZONE_SENSOR_TIMEOUT = "sensor_timeout_min"
DEFAULT_SENSOR_TIMEOUT_MIN = 240
CONF_ZONE_WEIGHT = "weight"
DEFAULT_ZONE_WEIGHT = 1.0
CONF_ZONE_AUTHORITATIVE_SYNC = "authoritative_climate_sync"
DEFAULT_AUTHORITATIVE_SYNC = False
KEY_DEMAND_STRATEGY = "demand_strategy"
CONF_GLOBAL_CALENDAR = "global_calendar"

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

# Phase 11 — Heating Plant & Multi-Generator Selection
CONF_ENABLE_GAS_HEATER = "enable_gas_heater"
CONF_ENABLE_HEAT_PUMP = "enable_heat_pump"

CONF_HEAT_PUMP_TYPE = "heat_pump_type"
HP_TYPE_CLIMATE = "climate"
HP_TYPE_SWITCH = "switch"
HP_TYPE_OPENTHERM = "opentherm"

CONF_HEAT_PUMP_ENTITY = "heat_pump_entity"
CONF_HEAT_PUMP_CH_SWITCH = "heat_pump_ch_switch"
CONF_HEAT_PUMP_MIN_TEMP = "heat_pump_min_temp"
CONF_HEAT_PUMP_MAX_TEMP = "heat_pump_max_temp"
CONF_HEAT_PUMP_COOL_MIN_TEMP = "hp_cool_min_temp"
CONF_HEAT_PUMP_COOL_MAX_TEMP = "hp_cool_max_temp"
DEFAULT_HP_COOL_MIN_TEMP = 7.0
DEFAULT_HP_COOL_MAX_TEMP = 18.0

# Phase 11 — Zone Split Climate Actuators
CONF_ZONE_SPLIT_CLIMATE = "split_climate_entity"
CONF_ZONE_SPLIT_ROLE = "split_role"
SPLIT_ROLE_HEATING_ONLY = "heating_only"
SPLIT_ROLE_COOLING_ONLY = "cooling_only"
SPLIT_ROLE_HEAT_COOL = "heat_cool"
DEFAULT_SPLIT_ROLE = SPLIT_ROLE_HEAT_COOL

CONF_ZONE_SPLIT_SOLAR_PRIORITY = "split_solar_priority"
DEFAULT_SPLIT_SOLAR_PRIORITY = True
CONF_ZONE_SPLIT_QUICK_BOOST = "split_quick_boost"
DEFAULT_SPLIT_QUICK_BOOST = False
CONF_ZONE_SPLIT_BOOST_DELTA = "split_boost_delta"
DEFAULT_SPLIT_BOOST_DELTA = 1.5
CONF_ZONE_SPLIT_SENSOR_INJECTION = "split_sensor_injection"
DEFAULT_SPLIT_SENSOR_INJECTION = True

# Phase 11 — Solar Self-Consumption & Energy Management
CONF_ENERGY_MANAGEMENT_ENABLED = "energy_management_enabled"
DEFAULT_ENERGY_MANAGEMENT_ENABLED = False
CONF_SOLAR_POWER_SENSOR = "solar_power_sensor"
CONF_GRID_EXPORT_SENSOR = "grid_export_sensor"
CONF_BATTERY_SOC_SENSOR = "battery_soc_sensor"
CONF_BATTERY_POWER_SENSOR = "battery_power_sensor"
CONF_EXTERNAL_SOLAR_OVERRIDE_ENTITY = "external_solar_override_entity"
CONF_SOLAR_EXPORT_THRESHOLD = "solar_export_threshold"
DEFAULT_SOLAR_EXPORT_THRESHOLD = 500.0
CONF_BATTERY_MIN_RESERVE_SOC = "battery_min_reserve_soc"
DEFAULT_BATTERY_MIN_RESERVE_SOC = 20.0
CONF_SOLAR_MIN_RUN_TIME = "solar_min_run_time"
DEFAULT_SOLAR_MIN_RUN_TIME = 10
CONF_SOLAR_OVERHEAT_OFFSET = "solar_overheat_offset"
DEFAULT_SOLAR_OVERHEAT_OFFSET = 0.0
CONF_SOLAR_FORECAST_SENSOR = "solar_forecast_sensor"
CONF_SOLAR_IRRADIANCE_SENSOR = "solar_irradiance_sensor"
CONF_BATTERY_MAX_DISCHARGE_TIME = "battery_max_discharge_time"
DEFAULT_BATTERY_MAX_DISCHARGE_TIME = 5
CONF_BATTERY_POWER_INVERTED = "battery_power_inverted"
DEFAULT_BATTERY_POWER_INVERTED = False

# Phase 11 — Runtime Master Keys & Priority
KEY_ALLOW_SPLIT_HEATING = "allow_split_heating"
KEY_ALLOW_SPLIT_COOLING = "allow_split_cooling"
KEY_HEAT_SOURCE_PRIORITY = "heat_source_priority"
SOURCE_PRIORITY_AUTO = "auto"
SOURCE_PRIORITY_HYBRID = "hybrid"
SOURCE_PRIORITY_COMBINED = "combined"
SOURCE_PRIORITY_GAS_ONLY = "gas_only"
SOURCE_PRIORITY_ELECTRIC_ONLY = "electric_only"
SOURCE_PRIORITY_GAS = "gas_priority"
SOURCE_PRIORITY_ELECTRIC = "electric_priority"
HEAT_SOURCE_PRIORITIES = (
    SOURCE_PRIORITY_AUTO,
    SOURCE_PRIORITY_HYBRID,
    SOURCE_PRIORITY_COMBINED,
    SOURCE_PRIORITY_GAS_ONLY,
    SOURCE_PRIORITY_ELECTRIC_ONLY,
)
DEFAULT_HEAT_SOURCE_PRIORITY = SOURCE_PRIORITY_AUTO

CONF_MASTER_HVAC_MODE = "master_hvac_mode"
CONF_MASTER_OPERATION_MODE = "master_operation_mode"
SEASON_MODE_WINTER = "winter"
SEASON_MODE_SUMMER = "summer"
CONF_HEAT_PUMP_COOLING = "heat_pump_cooling"
DEFAULT_HEAT_PUMP_COOLING = True
MASTER_OPERATION_MODES = ["heat", "cool"]
DEFAULT_MASTER_OPERATION_MODE = "heat"


# HVAC
HVAC_MODE_HEAT = "heat"
HVAC_MODE_COOL = "cool"
HVAC_MODE_OFF = "off"
HVAC_ACTION_HEATING = "heating"
HVAC_ACTION_COOLING = "cooling"
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

# Persistent State Keys (Anti-Frost)
KEY_ANTI_FROST_ENABLED = "anti_frost_enabled"
KEY_FROST_PROTECTION_TEMP = "frost_protection_temp"
DEFAULT_FROST_PROTECTION_TEMP = 12.0
DEFAULT_ANTI_FROST_ENABLED = True

# Persistent State Keys (Physical Sync Switch per Zone)
KEY_PHYSICAL_SYNC_PREFIX = "physical_sync_"

# Persistent State Keys (Passive Heat Switch per Zone)
KEY_PASSIVE_HEAT_PREFIX = "passive_heat_"

# Scheduler Multi-Profile (Phase 6)
KEY_SCHEDULER_ENABLED = "scheduler_enabled"
KEY_ACTIVE_PROFILE = "active_schedule_profile"
KEY_PROFILE_EXPIRES_AT = "schedule_profile_expires_at"
KEY_FALLBACK_PROFILE = "schedule_fallback_profile"
KEY_SCHEDULE_PROFILES = "schedule_profiles"
KEY_MANUAL_OVERRIDES = "schedule_manual_overrides"
DEFAULT_BASELINE_PRESET = "eco"
DEFAULT_SCHEDULE_PROFILE = "standard"
SCHEDULE_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DEFAULT_PRESET_TEMPS = {"comfort": 20.5, "eco": 18.0, "sleep": 17.5, "away": 16.0}
DEFAULT_COOLING_PRESET_TEMPS = {"comfort": 24.5, "eco": 26.5, "sleep": 25.5, "away": 28.0}
KEY_SMART_RETURN = "smart_return_state"
DEFAULT_SMART_START_HEATING_RATE = 1.5
MAX_SMART_START_HOURS = 6.0


def make_zone_entity_id(name: str) -> str:
    """Generate a predictable entity_id for a zone master thermostat."""
    safe = ""
    if slugify is not None:
        try:
            safe = slugify(name or "")
        except Exception:
            safe = ""
    if not safe:
        # Fallback if slugify fails, is unavailable, or returns empty string
        raw = (name or "").lower().replace(" ", "_").replace("-", "_")
        safe = "".join(c for c in raw if (c.isalnum() and c.isascii()) or c == "_").strip("_")
        if not safe:
            safe = "zone"
    return f"climate.{DOMAIN}_{safe}"


def make_via_device_kwargs(entry_id: str, master_device_id: str | None = None) -> dict[str, Any]:
    """Return backward- and forward-compatible DeviceInfo via_device kwargs."""
    try:
        from homeassistant.helpers.device_registry import DeviceInfo as HADeviceInfo
        if hasattr(HADeviceInfo, "__annotations__") and "via_device_id" in HADeviceInfo.__annotations__ and master_device_id:
            return {"via_device_id": master_device_id}
    except Exception:
        pass
    return {"via_device": (DOMAIN, entry_id)}


def make_zone_device_info(entry_id: str, zone_name: str, master_device_id: str | None = None) -> Any:
    """Return DeviceInfo for a specific heating/cooling zone."""
    from homeassistant.helpers.entity import DeviceInfo
    safe_slug = ""
    if slugify is not None:
        try:
            safe_slug = slugify(zone_name or "")
        except Exception:
            safe_slug = ""
    if not safe_slug:
        raw = (zone_name or "").lower().replace(" ", "_").replace("-", "_")
        safe_slug = "".join(c for c in raw if (c.isalnum() and c.isascii()) or c == "_").strip("_")
        if not safe_slug:
            safe_slug = "zone"
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry_id}_zone_{safe_slug}")},
        name=f"Zona {zone_name}",
        manufacturer="Multizone Thermostat",
        model="Zone Controller",
        **make_via_device_kwargs(entry_id, master_device_id),
    )
