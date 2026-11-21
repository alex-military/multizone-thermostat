"""Multizone Thermostat integration setup."""
from __future__ import annotations

from collections.abc import Mapping
import inspect
import logging
import math
from typing import Any

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

try:
    from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
except ImportError:
    EVENT_HOMEASSISTANT_STARTED = "homeassistant_started"

from .const import (
    CONF_BOILER_SWITCH,
    CONF_BOILER_MODE,
    CONF_OPENTHERM_ENTITY,
    CONF_ZONE_NAME,
    MODE_RELAY,
    MODE_OPENTHERM,
    CONF_ZONES,
    CONF_ZONE_ANTI_SEIZE,
    DOMAIN,
    make_zone_entity_id,
)
from .coordinator import MultizoneCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["climate", "switch", "number", "select", "time", "sensor", "binary_sensor", "button"]


def _migrate_config_data(
    data: Mapping[str, Any], options: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    """Normalize legacy config entry schemas and populate new release defaults."""
    migrated = False
    new_data = dict(data)
    new_options = dict(options) if options else {}
    config = {**new_data, **new_options}
    zones = [dict(z) for z in list(config.get(CONF_ZONES, []))]

    # 1. Migrate old virtual thermostats to new zones
    old_vts = new_data.pop("virtual_thermostats", [])
    if not old_vts and "virtual_thermostats" in new_options:
        old_vts = new_options.pop("virtual_thermostats", [])
    if old_vts:
        migrated = True
        for vt in old_vts:
            vt_zone = {
                "name": vt.get("name", "Unknown VT"),
                "climate_entities": [],
                "switch_entities": [vt.get("heater_switch")] if vt.get("heater_switch") else [],
                "temp_sensor": vt.get("temperature_sensor"),
                "target_temperature": vt.get("target_temperature", 20.0),
                "trv_preset_sync": False,
                CONF_ZONE_ANTI_SEIZE: True,
            }
            zones.append(vt_zone)

    # 2. Migrate old zones and populate per-zone defaults
    for zone in zones:
        if "climate_entity" in zone:
            migrated = True
            climate = zone.pop("climate_entity")
            zone["climate_entities"] = [climate] if isinstance(climate, str) and climate else []
            zone["switch_entities"] = []
            zone["target_temperature"] = 20.0
        if CONF_ZONE_ANTI_SEIZE not in zone:
            zone[CONF_ZONE_ANTI_SEIZE] = True
            migrated = True

    # 3. Migrate boiler mode for pre-OpenTherm installations
    if CONF_BOILER_MODE not in new_data and CONF_BOILER_MODE not in new_options:
        new_data[CONF_BOILER_MODE] = MODE_RELAY
        migrated = True

    if migrated:
        new_data[CONF_ZONES] = zones
        if CONF_ZONES in new_options:
            new_options[CONF_ZONES] = zones

    return new_data, new_options, migrated


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config entries to version 2."""
    version = getattr(config_entry, "version", 1)
    if isinstance(version, int) and version >= 2:
        return True
    _LOGGER.info("Migrating Multizone Thermostat config entry from version %s to 2", version)
    new_data, new_options, _ = _migrate_config_data(config_entry.data, config_entry.options or {})
    try:
        hass.config_entries.async_update_entry(
            config_entry, data=new_data, options=new_options, version=2
        )
    except TypeError:
        config_entry.version = 2
        hass.config_entries.async_update_entry(
            config_entry, data=new_data, options=new_options
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Multizone Thermostat from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    config = {**entry.data, **entry.options}
    boiler_mode = config.get(CONF_BOILER_MODE, MODE_RELAY)
    boiler_switch = config.get(CONF_BOILER_SWITCH)
    opentherm_entity = config.get(CONF_OPENTHERM_ENTITY)
    zones = [dict(z) for z in list(config.get(CONF_ZONES, []))]

    # Validate primary entity exists
    if boiler_mode == MODE_RELAY and boiler_switch:
        boiler_state = hass.states.get(boiler_switch)
        if boiler_state is None:
            if getattr(hass, "is_running", True):
                _LOGGER.warning(
                    "Boiler switch '%s' not found. The integration will load but boiler "
                    "control may not work until the entity is available.",
                    boiler_switch,
                )
            else:
                _LOGGER.debug(
                    "Boiler switch '%s' not yet available during Home Assistant startup; "
                    "will recheck once Home Assistant starts.",
                    boiler_switch,
                )
                if hasattr(hass, "bus") and hasattr(hass.bus, "async_listen_once"):
                    async def _check_boiler_started(_event) -> None:
                        if hass.states.get(boiler_switch) is None:
                            _LOGGER.warning(
                                "Boiler switch '%s' not found. The integration will load but boiler "
                                "control may not work until the entity is available.",
                                boiler_switch,
                            )
                    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _check_boiler_started)
    elif boiler_mode == MODE_OPENTHERM and opentherm_entity:
        ot_state = hass.states.get(opentherm_entity)
        if ot_state is None:
            if getattr(hass, "is_running", True):
                _LOGGER.warning(
                    "OpenTherm entity '%s' not found. The integration will load but modulating "
                    "control may not work until the entity is available.",
                    opentherm_entity,
                )
            else:
                _LOGGER.debug(
                    "OpenTherm entity '%s' not yet available during Home Assistant startup; "
                    "will recheck once Home Assistant starts.",
                    opentherm_entity,
                )
                if hasattr(hass, "bus") and hasattr(hass.bus, "async_listen_once"):
                    async def _check_ot_started(_event) -> None:
                        if hass.states.get(opentherm_entity) is None:
                            _LOGGER.warning(
                                "OpenTherm entity '%s' not found. The integration will load but modulating "
                                "control may not work until the entity is available.",
                                opentherm_entity,
                            )
                    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _check_ot_started)

    # Migrate old config format to new Hybrid Zones format
    new_data, new_options, migrated = _migrate_config_data(entry.data, entry.options or {})
    if migrated:
        _LOGGER.info("Migrating Multizone Thermostat config to new Hybrid Zones format.")
        if CONF_ZONES in new_options:
            hass.config_entries.async_update_entry(entry, data=new_data, options=new_options)
        else:
            hass.config_entries.async_update_entry(entry, data=new_data)


    from homeassistant.helpers import device_registry as dr
    device_registry = dr.async_get(hass)
    master_device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name="Master Control",
        manufacturer="Custom Integration",
        model="Master Control",
    )

    # Create coordinator
    coordinator = MultizoneCoordinator(
        hass=hass,
        entry=entry,
    )
    coordinator.master_device_id = master_device.id

    # Load persistent data
    await coordinator.async_load_storage()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
    }

    # Set up platforms first so entities are registered before listeners/calendar fire
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Set up state listeners
    coordinator.async_setup_listeners()

    # Seed initial zone demands so Master Demand and demand sensors don't stall at 0% on startup
    orch = getattr(coordinator, "plant_orchestrator", None)
    if orch and inspect.iscoroutinefunction(getattr(orch, "_async_update_boiler", None)):
        await orch._async_update_boiler()

    # Register static path for Lovelace custom card once per HA instance
    import os
    www_path = hass.config.path("custom_components/multizone_thermostat/www")
    if not hass.data[DOMAIN].get("_static_path_registered") and await hass.async_add_executor_job(os.path.isdir, www_path):
        await hass.http.async_register_static_paths([
            StaticPathConfig(
                url_path="/multizone_thermostat_card",
                path=www_path,
                cache_headers=False,
            )
        ])
        hass.data[DOMAIN]["_static_path_registered"] = True

    # Register Lovelace custom card resource automatically
    try:
        if "lovelace" in hass.data:
            resources = hass.data["lovelace"].resources
            if hasattr(resources, "async_get_info") and hasattr(resources, "async_create_item"):
                await resources.async_get_info()
                
                from homeassistant.loader import async_get_integration
                integration = await async_get_integration(hass, DOMAIN)
                version = integration.version if integration else "unknown"
                
                js_path = os.path.join(www_path, "multizone-thermostat-card-v24.js")
                mtime = int(os.path.getmtime(js_path)) if os.path.exists(js_path) else 0
                base_url = "/multizone_thermostat_card/multizone-thermostat-card-v24.js"
                url = f"{base_url}?v={version}.{mtime}"
                
                existing_item = None
                for item in list(resources.async_items()):
                    item_url = item.get("url", "")
                    if "multizone-thermostat-card" in item_url:
                        if existing_item is None and item_url.startswith(base_url):
                            existing_item = item
                        else:
                            # Remove duplicate or legacy resources
                            if hasattr(resources, "async_delete_item"):
                                await resources.async_delete_item(item.get("id"))
                        
                if not existing_item:
                    await resources.async_create_item({
                        "res_type": "module",
                        "url": url,
                    })
                elif existing_item.get("url") != url:
                    await resources.async_update_item(existing_item.get("id"), {
                        "url": url,
                    })
    except Exception as err:
        _LOGGER.warning("Could not register or update Lovelace resource: %s", err)

    # Register update listener for options changes
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    # Register integration services
    await _async_register_services(hass)

    _LOGGER.info(
        "Multizone Thermostat loaded: mode=%s, entity=%s, zones=%d",
        boiler_mode,
        boiler_switch or opentherm_entity,
        len(zones),
    )
    return True


def _get_active_coordinators(hass: HomeAssistant) -> list[MultizoneCoordinator]:
    """Retrieve all active Multizone coordinator instances."""
    domain_data = hass.data.get(DOMAIN, {})
    coordinators: list[MultizoneCoordinator] = []
    if isinstance(domain_data, dict):
        for val in domain_data.values():
            if isinstance(val, dict) and "coordinator" in val:
                coordinators.append(val["coordinator"])
    return coordinators


async def _async_register_services(hass: HomeAssistant) -> None:
    """Register all Phase 6 schedule and profile services."""
    if hass.data[DOMAIN].get("_services_registered"):
        return

    from homeassistant.core import ServiceCall

    async def handle_save_schedule_profile(call: ServiceCall) -> None:
        profile_id = call.data["profile_id"]
        profile_data = {
            "name": call.data.get("name", profile_id.capitalize()),
            "baseline_preset": call.data.get("baseline_preset", "eco"),
            "days": call.data.get("days", {}),
        }
        for coord in _get_active_coordinators(hass):
            if hasattr(coord, "schedule_manager"):
                await coord.schedule_manager.async_save_profile(profile_id, profile_data)

    async def handle_activate_schedule_profile(call: ServiceCall) -> None:
        profile_id = call.data["profile_id"]
        expires_at = call.data.get("expires_at")
        fallback_profile = call.data.get("fallback_profile", "standard")
        for coord in _get_active_coordinators(hass):
            if hasattr(coord, "schedule_manager"):
                await coord.schedule_manager.async_activate_profile(
                    profile_id=profile_id,
                    expires_at=expires_at,
                    fallback_profile=fallback_profile,
                )

    async def handle_duplicate_schedule_profile(call: ServiceCall) -> None:
        source_id = call.data["source_profile_id"]
        target_id = call.data["target_profile_id"]
        target_name = call.data.get("target_name")
        for coord in _get_active_coordinators(hass):
            if hasattr(coord, "schedule_manager"):
                await coord.schedule_manager.async_duplicate_profile(
                    source_id=source_id,
                    target_id=target_id,
                    target_name=target_name,
                )

    async def handle_set_smart_return(call: ServiceCall) -> None:
        arrival_time = call.data["arrival_time"]
        preset = call.data.get("preset", "comfort")
        zones = call.data.get("zones")
        for coord in _get_active_coordinators(hass):
            if hasattr(coord, "schedule_manager"):
                await coord.schedule_manager.async_set_smart_return(
                    arrival_time=arrival_time,
                    preset=preset,
                    zones=zones,
                )

    async def handle_cancel_smart_return(call: ServiceCall) -> None:
        for coord in _get_active_coordinators(hass):
            if hasattr(coord, "schedule_manager"):
                await coord.schedule_manager.async_cancel_smart_return()

    async def handle_clear_zone_override(call: ServiceCall) -> None:
        entity_id = call.data.get("entity_id")
        for coord in _get_active_coordinators(hass):
            if hasattr(coord, "schedule_manager"):
                await coord.schedule_manager.async_clear_manual_override(entity_id)

    async def handle_set_preset_temperature(call: ServiceCall) -> None:
        preset = call.data["preset"]
        entity_id = call.data["entity_id"]
        temperature = float(call.data["temperature"])
        for coord in _get_active_coordinators(hass):
            if hasattr(coord, "zone_manager"):
                coord.zone_manager.update_preset_temperature(preset, entity_id, temperature)
            if hasattr(coord, "schedule_manager"):
                await coord.schedule_manager.async_evaluate_schedule()

    def _find_zone_name_for_entity(coord: MultizoneCoordinator, climate_entity: str) -> str | None:
        canon = coord.resolve_zone_id(climate_entity) if hasattr(coord, "resolve_zone_id") else climate_entity
        for zone in getattr(coord, "zones", []) or []:
            zname = zone.get(CONF_ZONE_NAME) if isinstance(zone, dict) else None
            if zname and make_zone_entity_id(zname) == canon:
                return zname
        return None

    async def handle_set_pid_parameters(call: ServiceCall) -> None:
        climate_entity = call.data.get("climate_entity") or call.data.get("entity_id")
        if not climate_entity:
            return

        def _parse_pid_val(raw: Any, name: str, min_v: float, max_v: float) -> float | None:
            if raw is None:
                return None
            val = float(raw)
            if not math.isfinite(val) or not (min_v <= val <= max_v):
                raise ValueError(f"Parameter '{name}' must be finite between {min_v} and {max_v}, got {raw!r}")
            return val

        kp = _parse_pid_val(call.data.get("kp"), "kp", 0.1, 500.0)
        ki = _parse_pid_val(call.data.get("ki"), "ki", 0.0, 10.0)
        kd = _parse_pid_val(call.data.get("kd"), "kd", 0.0, 50000.0)
        lock_param = call.data.get("lock_parameter")
        unlock_arg = call.data.get("unlock")
        seed_autotuner = bool(call.data.get("seed_autotuner", False))

        for coord in _get_active_coordinators(hass):
            zc = getattr(coord, "zone_controller", None)
            if not zc or not hasattr(zc, "async_set_zone_pid"):
                continue
            zname = _find_zone_name_for_entity(coord, climate_entity)
            if not seed_autotuner and unlock_arg is not None and zname and hasattr(coord, "async_set_pid_manual_unlock"):
                await coord.async_set_pid_manual_unlock(zname, bool(unlock_arg))
            updated = await zc.async_set_zone_pid(
                climate_entity,
                kp=kp,
                ki=ki,
                kd=kd,
                lock_param=lock_param,
                seed_autotuner=seed_autotuner,
            )
            if updated:
                if seed_autotuner and zname and hasattr(coord, "async_set_pid_manual_unlock"):
                    tuner = zc.get_autotuner(climate_entity) if hasattr(zc, "get_autotuner") else None
                    if not getattr(tuner, "manual_overrides", None):
                        await coord.async_set_pid_manual_unlock(zname, False)
                if hasattr(coord, "async_notify_pid_entities"):
                    coord.async_notify_pid_entities()
                orch = getattr(coord, "plant_orchestrator", None)
                if orch and inspect.iscoroutinefunction(getattr(orch, "_async_update_boiler", None)):
                    await orch._async_update_boiler()

    async def handle_reset_autotune(call: ServiceCall) -> None:
        climate_entity = call.data.get("climate_entity") or call.data.get("entity_id")
        if not climate_entity:
            return
        keep_manual = bool(call.data.get("keep_manual_overrides", False))
        for coord in _get_active_coordinators(hass):
            zc = getattr(coord, "zone_controller", None)
            if not zc or not hasattr(zc, "async_reset_zone_autotuner"):
                continue
            ok = await zc.async_reset_zone_autotuner(
                climate_entity,
                keep_manual_overrides=keep_manual,
            )
            if ok:
                zname = _find_zone_name_for_entity(coord, climate_entity)
                if not keep_manual and zname and hasattr(coord, "async_set_pid_manual_unlock"):
                    await coord.async_set_pid_manual_unlock(zname, False)
                if hasattr(coord, "async_notify_pid_entities"):
                    coord.async_notify_pid_entities()
                orch = getattr(coord, "plant_orchestrator", None)
                if orch and inspect.iscoroutinefunction(getattr(orch, "_async_update_boiler", None)):
                    await orch._async_update_boiler()

    async def handle_restore_autotune(call: ServiceCall) -> None:
        climate_entity = call.data.get("climate_entity") or call.data.get("entity_id")
        if not climate_entity:
            return
        keep_manual = bool(call.data.get("keep_manual_overrides", False))
        for coord in _get_active_coordinators(hass):
            zc = getattr(coord, "zone_controller", None)
            if not zc or not hasattr(zc, "async_restore_zone_autotuner"):
                continue
            ok = await zc.async_restore_zone_autotuner(
                climate_entity,
                keep_manual_overrides=keep_manual,
            )
            if ok:
                zname = _find_zone_name_for_entity(coord, climate_entity)
                if not keep_manual and zname and hasattr(coord, "async_set_pid_manual_unlock"):
                    await coord.async_set_pid_manual_unlock(zname, False)
                if hasattr(coord, "async_notify_pid_entities"):
                    coord.async_notify_pid_entities()
                orch = getattr(coord, "plant_orchestrator", None)
                if orch and inspect.iscoroutinefunction(getattr(orch, "_async_update_boiler", None)):
                    await orch._async_update_boiler()

    services = {
        "save_schedule_profile": handle_save_schedule_profile,
        "activate_schedule_profile": handle_activate_schedule_profile,
        "duplicate_schedule_profile": handle_duplicate_schedule_profile,
        "set_smart_return": handle_set_smart_return,
        "cancel_smart_return": handle_cancel_smart_return,
        "clear_zone_override": handle_clear_zone_override,
        "set_preset_temperature": handle_set_preset_temperature,
        "set_pid_parameters": handle_set_pid_parameters,
        "reset_autotune": handle_reset_autotune,
        "restore_autotune": handle_restore_autotune,
    }

    if hasattr(hass, "services") and hasattr(hass.services, "async_register"):
        for svc_name, handler in services.items():
            hass.services.async_register(DOMAIN, svc_name, handler)

    hass.data[DOMAIN]["_services_registered"] = True



async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator: MultizoneCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        try:
            await coordinator.async_save_storage()
        except Exception as err:
            _LOGGER.warning("Could not save storage on unload: %s", err)
        try:
            if hasattr(coordinator, "boiler_backend") and coordinator.boiler_backend:
                await coordinator.boiler_backend.async_emergency_off()
        except Exception as err:
            _LOGGER.warning("Could not turn off boiler on unload: %s", err)
        coordinator.async_teardown_listeners()
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.info("Multizone Thermostat unloaded.")

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update — config_flow already triggers reload via async_reload,
    but this listener acts as a safety net to ensure any direct option changes are applied."""
    _LOGGER.info("Options updated for Multizone Thermostat, reloading integration...")
    await hass.config_entries.async_reload(entry.entry_id)
