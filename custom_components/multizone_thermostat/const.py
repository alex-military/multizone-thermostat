"""Constants for Multizone Thermostat integration."""
DOMAIN = "multizone_thermostat"

# ... (все существующие константы без изменений) ...

# Virtual Thermostat keys
CONF_VIRTUAL_THERMOSTATS = "virtual_thermostats"
CONF_VT_TEMP_SENSOR = "temperature_sensor"
CONF_VT_HEATER_SWITCH = "heater_switch"
CONF_VT_NAME = "name"
CONF_VT_TARGET_TEMP = "target_temperature"
CONF_VT_TOLERANCE = "tolerance"
DEFAULT_VT_TARGET_TEMP = 20.0
DEFAULT_VT_TOLERANCE = 0.5

# ===== НОВЫЕ КОНСТАНТЫ ДЛЯ ОХЛАЖДЕНИЯ =====
CONF_VT_COOLER_SWITCH = "cooler_switch"
CONF_VT_COOL_TOLERANCE = "cool_tolerance"
DEFAULT_VT_COOL_TOLERANCE = 0.5

# Режимы работы виртуального термостата (heat/cool/auto)
VT_MODE_HEAT = "heat"
VT_MODE_COOL = "cool"
VT_MODE_AUTO = "auto"
VT_MODES = [VT_MODE_HEAT, VT_MODE_COOL, VT_MODE_AUTO]

# ===== НОВЫЕ КОНСТАНТЫ ДЛЯ ПРЕСЕТОВ =====
CONF_VT_PRESET_TEMPS = "preset_temperatures"
CONF_VT_PRESET_MANUAL = "manual_temp"
CONF_VT_PRESET_ECO = "eco_temp"
CONF_VT_PRESET_COMFORT = "comfort_temp"
CONF_VT_PRESET_SLEEP = "sleep_temp"
CONF_VT_PRESET_AWAY = "away_temp"
DEFAULT_VT_PRESET_TEMPS = {
    "manual": 20.0,
    "eco": 18.0,
    "comfort": 22.0,
    "sleep": 19.0,
    "away": 16.0,
}
