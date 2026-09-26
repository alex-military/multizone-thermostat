"""Diagnostics support for Multizone Thermostat."""
from __future__ import annotations

from typing import Any
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.diagnostics import async_redact_data
import homeassistant.util.dt as dt_util

from .const import DOMAIN, make_zone_entity_id
from .coordinator import MultizoneCoordinator

TO_REDACT = {
    "unique_id",
    "token",
    "password",
    "api_key",
    "latitude",
    "longitude",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: MultizoneCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # 1. Config Entry Data & Options (redacted for privacy)
    entry_dict = {
        "entry_id": entry.entry_id,
        "version": entry.version,
        "domain": entry.domain,
        "title": entry.title,
        "data": async_redact_data(dict(entry.data), TO_REDACT),
        "options": async_redact_data(dict(entry.options), TO_REDACT),
    }

    # 2. Coordinator Overview
    coordinator_info = {
        "boiler_mode": coordinator.boiler_mode,
        "boiler_switch": coordinator.boiler_switch,
        "opentherm_entity": coordinator.opentherm_entity,
        "master_state": coordinator.get_master_state(),
        "boiler_status_reason": getattr(coordinator, "boiler_status_reason", "N/A"),
        "current_global_preset": coordinator.current_global_preset,
        "geofencing_enabled": coordinator.geofencing_enabled,
        "weather_sensor_id": coordinator.weather_sensor_id,
        "calendar_entity_id": coordinator.calendar_entity_id,
        "min_cycle_on_minutes": coordinator._min_cycle_on,
        "min_cycle_off_minutes": coordinator._min_cycle_off,
        "valve_delay_seconds": coordinator._valve_delay,
        "pre_window_state": coordinator._pre_window_state,
        "anti_seize_running": coordinator._anti_seize_running,
        "last_active_time_uptime": round(coordinator._last_active_time, 1),
    }

    # 3. Zones Diagnostic Details
    zones_diag: dict[str, Any] = {}
    for zone in coordinator.zones:
        z_name = zone.get("name", "Unknown")
        climate_id = make_zone_entity_id(z_name)

        # Get climate entity instance if registered
        climate_entity = coordinator._climate_entities.get(climate_id)

        tuner = coordinator.get_autotuner(climate_id)
        thermal = coordinator.get_thermal_model(climate_id)
        pid = coordinator._pids.get(climate_id)

        zone_info: dict[str, Any] = {
            "name": z_name,
            "climate_id": climate_id,
            "mode": coordinator.get_zone_mode(climate_id),
            "demand_percent": coordinator.get_zone_demand(climate_id),
            "is_frost_emergency": coordinator.is_zone_in_frost_emergency(climate_id),
            "climates_configured": zone.get("climates", []),
            "switches_configured": zone.get("switches", []),
            "autotuner": {
                "state": tuner.state if tuner else "N/A",
                "completed_cycles": len(tuner.completed_cycles) if tuner else 0,
                "required_cycles": tuner.required_cycles if tuner else 0,
                "kp": tuner.kp if tuner else 0.0,
                "ki": tuner.ki if tuner else 0.0,
                "kd": tuner.kd if tuner else 0.0,
            } if tuner else None,
            "thermal_model": {
                "heating_rate": thermal.heating_rate if thermal else 0.0,
                "cooling_rate": thermal.cooling_rate if thermal else 0.0,
                "thermal_inertia": thermal.thermal_inertia if thermal else 0.0,
            } if thermal else None,
            "pid_parameters": {
                "kp": getattr(getattr(pid, "_pid", None), "_Kp", 0.0) if pid else 0.0,
                "ki": getattr(getattr(pid, "_pid", None), "_Ki", 0.0) if pid else 0.0,
                "kd": getattr(getattr(pid, "_pid", None), "_Kd", 0.0) if pid else 0.0,
            } if pid else None,
        }

        if climate_entity:
            zone_info["current_temperature"] = climate_entity.current_temperature
            zone_info["target_temperature"] = climate_entity.target_temperature
            zone_info["hvac_mode"] = str(climate_entity.hvac_mode)
            zone_info["hvac_action"] = str(climate_entity.hvac_action)
            zone_info["trv_health"] = climate_entity.get_trv_health()
            zone_info["pending_trv_targets"] = dict(climate_entity._pending_trv_targets)
            zone_info["last_known_trv_targets"] = dict(climate_entity._last_known_trv_targets)

        zones_diag[climate_id] = zone_info

    # 4. Ring Buffer / Trace Timeline (Last 100 events)
    trace_events = getattr(coordinator, "diagnostics_history", [])

    return {
        "timestamp": dt_util.now().isoformat(),
        "config_entry": entry_dict,
        "coordinator": coordinator_info,
        "zones": zones_diag,
        "trace_events": trace_events,
    }
