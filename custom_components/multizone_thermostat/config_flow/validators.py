"""Validators for Multizone Thermostat config flow."""

def validate_opentherm_temps(min_temp: float, max_temp: float) -> dict[str, str]:
    """Validate OpenTherm temperature ranges."""
    errors = {}
    if min_temp >= max_temp:
        errors["base"] = "invalid_temp_range"
    return errors

def validate_zone_input(
    zone_name: str,
    climates: list[str],
    switches: list[str],
    already_added: list[str],
    valves: list[str] | None = None,
) -> dict[str, str]:
    """Validate user input when adding or editing a zone."""
    errors = {}
    if not zone_name:
        errors["zone_name"] = "zone_name_required"
    elif zone_name in already_added:
        errors["zone_name"] = "zone_name_exists"
    elif not climates and not switches and not (valves or []):
        errors["base"] = "no_actuators_selected"
    return errors

def validate_geofencing(geofencing_enabled: bool, presence_sensor: str | None) -> dict[str, str]:
    """Validate geofencing configuration."""
    errors = {}
    if geofencing_enabled and not presence_sensor:
        errors["presence_sensor"] = "presence_sensor_required"
    return errors
