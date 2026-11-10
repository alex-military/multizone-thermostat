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
    "global_calendar",
    "presence_sensor",
    "weather_sensor",
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
        "opentherm_diagnostics": coordinator.plant_diagnostics.get_opentherm_diagnostics() if hasattr(coordinator, "plant_diagnostics") else None,
        "dhw_active_sensor": getattr(coordinator, "dhw_active_sensor", None),
        "is_dhw_active": coordinator.is_dhw_active,
        "master_state": coordinator.get_master_state(),
        "boiler_status_reason": getattr(coordinator, "boiler_status_reason", "N/A"),
        "current_global_preset": coordinator.zone_manager.current_global_preset,
        "geofencing_configured": bool(entry.data.get("geofencing_enabled", False)),
        "geofencing_enabled": coordinator.get_persistent_data("geofencing_toggle", True),
        "weather_sensor_id": coordinator.weather_sensor_id,
        "calendar_entity_id": getattr(coordinator, "global_calendar_id", None),
        "min_cycle_on_minutes": coordinator._min_cycle_on,
        "min_cycle_off_minutes": coordinator._min_cycle_off,
        "valve_delay_seconds": coordinator._valve_delay,
        "pre_window_state": coordinator._pre_window_state,
        "anti_seize_running": hasattr(coordinator, "anti_seize_manager") and coordinator.anti_seize_manager.is_running,
        "last_active_time_uptime": round(coordinator._last_active_time, 1),
        # Heat Pump parameters & state
        "enable_heat_pump": getattr(coordinator, "enable_heat_pump", False),
        "heat_pump_cooling": getattr(coordinator, "heat_pump_cooling", False),
        "hp_cool_min_temp": getattr(coordinator, "hp_cool_min_temp", getattr(coordinator.heat_pump_backend, "cool_min_temp", 7.0) if getattr(coordinator, "heat_pump_backend", None) else 7.0),
        "hp_cool_max_temp": getattr(coordinator, "hp_cool_max_temp", getattr(coordinator.heat_pump_backend, "cool_max_temp", 18.0) if getattr(coordinator, "heat_pump_backend", None) else 18.0),
        "heat_pump_status_reason": getattr(coordinator.heat_pump_backend, "status_reason", getattr(coordinator, "boiler_status_reason", "N/A")) if getattr(coordinator, "heat_pump_backend", None) else "N/A",
        # Energy Management
        "energy_management_enabled": getattr(coordinator, "energy_management_enabled", False),
    }
    coordinator_info = async_redact_data(
        coordinator_info, {"calendar_entity_id", "weather_sensor_id"}
    )

    # 3. Zones Diagnostic Details
    zones_diag: dict[str, Any] = {}
    for zone in coordinator.zones:
        z_name = zone.get("name", "Unknown")
        climate_id = make_zone_entity_id(z_name)

        # Get climate entity instance if registered
        climate_entity = coordinator._climate_entities.get(climate_id)

        tuner = coordinator.zone_controller.get_autotuner(climate_id)
        tuner_cool = coordinator.zone_controller.get_autotuner(climate_id, mode="cool")
        thermal = coordinator.zone_controller.get_thermal_model(climate_id)
        pid = coordinator._pids.get(climate_id)
        pids_cool = getattr(coordinator, "_pids_cool", {})
        if not pids_cool and hasattr(coordinator, "zone_controller") and hasattr(coordinator.zone_controller, "pids_cool"):
            pids_cool = coordinator.zone_controller.pids_cool()
        pid_cool = pids_cool.get(climate_id) if isinstance(pids_cool, dict) else None

        plant_diag = getattr(coordinator, "plant_diagnostics", None)
        if plant_diag and hasattr(plant_diag, "get_zone_battery_level"):
            battery_level = plant_diag.get_zone_battery_level(climate_id)
        elif plant_diag and zone.get("temp_sensor"):
            battery_level = plant_diag.get_battery_level(zone.get("temp_sensor"))
        else:
            battery_level = None

        zone_info: dict[str, Any] = {
            "name": z_name,
            "climate_id": climate_id,
            "mode": coordinator.get_zone_mode(climate_id),
            "demand_percent": coordinator.get_zone_demand(climate_id),
            "is_frost_emergency": coordinator.is_zone_in_frost_emergency(climate_id),
            "battery_level": battery_level,
            "climates_configured": zone.get("climates") or zone.get("climate_entities", []),
            "switches_configured": zone.get("switches") or zone.get("switch_entities", []),
            "autotuner": {
                "state": tuner.state if tuner else "N/A",
                "completed_cycles": len(tuner.completed_cycles) if tuner else 0,
                "required_cycles": tuner.required_cycles if tuner else 0,
                "kp": tuner.kp if tuner else 0.0,
                "ki": tuner.ki if tuner else 0.0,
                "kd": tuner.kd if tuner else 0.0,
            } if tuner else None,
            "autotuner_cool": {
                "state": tuner_cool.state if tuner_cool else "N/A",
                "completed_cycles": len(tuner_cool.completed_cycles) if tuner_cool else 0,
                "required_cycles": tuner_cool.required_cycles if tuner_cool else 0,
                "kp": tuner_cool.kp if tuner_cool else 0.0,
                "ki": tuner_cool.ki if tuner_cool else 0.0,
                "kd": tuner_cool.kd if tuner_cool else 0.0,
            } if tuner_cool else None,
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
            "pid_parameters_cool": {
                "kp": getattr(getattr(pid_cool, "_pid", None), "_Kp", 0.0) if pid_cool else 0.0,
                "ki": getattr(getattr(pid_cool, "_pid", None), "_Ki", 0.0) if pid_cool else 0.0,
                "kd": getattr(getattr(pid_cool, "_pid", None), "_Kd", 0.0) if pid_cool else 0.0,
            } if pid_cool else None,
            "split": {
                "split_climate_entity": zone.get("split_climate_entity") or zone.get("split_climate"),
                "split_role": zone.get("split_role"),
                "split_solar_priority": zone.get("split_solar_priority"),
                "split_quick_boost": zone.get("split_quick_boost"),
            },
        }

        if climate_entity:
            sync_mgr = getattr(climate_entity, "_sync_manager", None)
            pending_targets = getattr(
                sync_mgr,
                "_pending_trv_targets",
                getattr(climate_entity, "_pending_trv_targets", {}),
            )
            last_known_targets = getattr(
                sync_mgr,
                "_last_known_trv_targets",
                getattr(climate_entity, "_last_known_trv_targets", {}),
            )
            zone_info["current_temperature"] = climate_entity.current_temperature
            zone_info["target_temperature"] = climate_entity.target_temperature
            zone_info["hvac_mode"] = str(climate_entity.hvac_mode)
            zone_info["hvac_action"] = str(climate_entity.hvac_action)
            zone_info["trv_health"] = climate_entity.get_trv_health()
            zone_info["pending_trv_targets"] = dict(pending_targets)
            zone_info["last_known_trv_targets"] = dict(last_known_targets)

        zones_diag[climate_id] = zone_info

    # 4. Ring Buffer / Trace Timeline (Last 100 events)
    trace_events = getattr(coordinator, "diagnostics_history", [])

    # 5. Physical Plant Diagnostics & Building Energy Metrics
    plant_health = {}
    if hasattr(coordinator, "plant_diagnostics"):
        plant_health = coordinator.plant_diagnostics.get_plant_health_summary()

    # 6. Energy Management Telemetry
    energy_telemetry = None
    if hasattr(coordinator, "energy_manager") and coordinator.energy_manager:
        energy_telemetry = coordinator.energy_manager.get_diagnostics()

    return {
        "timestamp": dt_util.now().isoformat(),
        "config_entry": entry_dict,
        "coordinator": coordinator_info,
        "energy_management": energy_telemetry,
        "plant_health": plant_health,
        "zones": zones_diag,
        "trace_events": trace_events,
    }
