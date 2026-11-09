"""Validators for Multizone Thermostat config flow."""

def validate_opentherm_temps(min_temp: float, max_temp: float) -> dict[str, str]:
    """Validate OpenTherm temperature ranges."""
    errors = {}
    if min_temp >= max_temp:
        errors["base"] = "invalid_temp_range"
    return errors

def validate_plants_selection(enable_gas: bool, enable_hp: bool) -> dict[str, str]:
    """Validate that at least one central plant generator is selected."""
    errors = {}
    if not enable_gas and not enable_hp:
        errors["base"] = "no_plants_selected"
    return errors

def validate_heat_pump_temps(min_temp: float, max_temp: float) -> dict[str, str]:
    """Validate Heat Pump temperature ranges for OpenTherm mode."""
    errors = {}
    if min_temp >= max_temp:
        errors["base"] = "invalid_temp_range"
    return errors

def validate_heat_pump_cool_temps(min_temp: float, max_temp: float) -> dict[str, str]:
    """Validate Heat Pump cooling temperature ranges."""
    errors = {}
    if min_temp >= max_temp:
        errors["base"] = "hp_temps_invalid"
    return errors

from ..const import CONF_ZONE_NAME

def validate_zone_input(
    zone_name: str,
    climates: list[str],
    switches: list[str],
    already_added: list[str],
    valves: list[str] | None = None,
    split_climate: str | None = None,
) -> dict[str, str]:
    """Validate user input when adding or editing a zone."""
    errors = {}
    if not zone_name:
        errors[CONF_ZONE_NAME] = "zone_name_required"
    elif zone_name in already_added:
        errors[CONF_ZONE_NAME] = "zone_name_exists"
    elif not climates and not switches and not (valves or []) and not split_climate:
        errors["base"] = "no_actuators_selected"
    return errors

def validate_geofencing(geofencing_enabled: bool, presence_sensor: str | None) -> dict[str, str]:
    """Validate geofencing configuration."""
    errors = {}
    if geofencing_enabled and not presence_sensor:
        errors["presence_sensor"] = "presence_sensor_required"
    return errors
