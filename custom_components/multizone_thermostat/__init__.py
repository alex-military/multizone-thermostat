"""Multizone Thermostat integration setup."""
from __future__ import annotations

import logging

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
    MODE_RELAY,
    MODE_OPENTHERM,
    CONF_ZONES,
    DOMAIN,
)
from .coordinator import MultizoneCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["climate", "switch", "number", "select", "time", "sensor", "binary_sensor"]


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
    migrated = False
    new_data = dict(entry.data)
    new_options = dict(entry.options) if entry.options else {}
    
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
                "anti_seize_zone_enable": True,
            }
            zones.append(vt_zone)
            
    # 2. Migrate old zones
    for zone in zones:
        if "climate_entity" in zone:
            migrated = True
            climate = zone.pop("climate_entity")
            zone["climate_entities"] = [climate] if isinstance(climate, str) and climate else []
            zone["switch_entities"] = []
            zone["target_temperature"] = 20.0
            
    # Migrate boiler mode for pre-OpenTherm installations
    if CONF_BOILER_MODE not in new_data and CONF_BOILER_MODE not in new_options:
        new_data[CONF_BOILER_MODE] = MODE_RELAY
        migrated = True

    if migrated:
        _LOGGER.info("Migrating Multizone Thermostat config to new Hybrid Zones format.")
        new_data[CONF_ZONES] = zones
        if CONF_ZONES in new_options:
            new_options[CONF_ZONES] = zones
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

    services = {
        "save_schedule_profile": handle_save_schedule_profile,
        "activate_schedule_profile": handle_activate_schedule_profile,
        "duplicate_schedule_profile": handle_duplicate_schedule_profile,
        "set_smart_return": handle_set_smart_return,
        "cancel_smart_return": handle_cancel_smart_return,
        "clear_zone_override": handle_clear_zone_override,
        "set_preset_temperature": handle_set_preset_temperature,
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
