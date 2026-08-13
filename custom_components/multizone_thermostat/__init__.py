"""Multizone Thermostat integration setup."""
from __future__ import annotations

import logging

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

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

PLATFORMS = ["climate", "switch", "number", "select", "time", "sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Multizone Thermostat from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    boiler_mode = entry.data.get(CONF_BOILER_MODE, MODE_RELAY)
    boiler_switch = entry.data.get(CONF_BOILER_SWITCH)
    opentherm_entity = entry.data.get(CONF_OPENTHERM_ENTITY)
    zones = [dict(z) for z in list(entry.data.get(CONF_ZONES, []))]

    # Validate primary entity exists
    if boiler_mode == MODE_RELAY and boiler_switch:
        boiler_state = hass.states.get(boiler_switch)
        if boiler_state is None:
            _LOGGER.warning(
                "Boiler switch '%s' not found. The integration will load but boiler "
                "control may not work until the entity is available.",
                boiler_switch,
            )
    elif boiler_mode == MODE_OPENTHERM and opentherm_entity:
        ot_state = hass.states.get(opentherm_entity)
        if ot_state is None:
            _LOGGER.warning(
                "OpenTherm entity '%s' not found. The integration will load but modulating "
                "control may not work until the entity is available.",
                opentherm_entity,
            )

    # Migrate old config format to new Hybrid Zones format
    migrated = False
    new_data = dict(entry.data)
    
    # 1. Migrate old virtual thermostats to new zones
    old_vts = new_data.pop("virtual_thermostats", [])
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
    if CONF_BOILER_MODE not in new_data:
        new_data[CONF_BOILER_MODE] = MODE_RELAY
        migrated = True

    if migrated:
        _LOGGER.info("Migrating Multizone Thermostat config to new Hybrid Zones format.")
        new_data["zones"] = zones
        hass.config_entries.async_update_entry(entry, data=new_data)

    # Create coordinator
    coordinator = MultizoneCoordinator(
        hass=hass,
        entry=entry,
    )

    # Load persistent data
    await coordinator.async_load_storage()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
    }

    # Set up state listeners
    coordinator.async_setup_listeners()

    # Set up platforms (switch)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register static path for Lovelace custom card
    await hass.http.async_register_static_paths([
        StaticPathConfig(
            url_path="/multizone_thermostat_card",
            path=hass.config.path("custom_components/multizone_thermostat/www"),
            cache_headers=False,
        )
    ])

    # Register Lovelace custom card resource automatically
    try:
        if "lovelace" in hass.data:
            resources = hass.data["lovelace"].resources
            if hasattr(resources, "async_get_info"):
                await resources.async_get_info()
                
                from homeassistant.loader import async_get_integration
                integration = await async_get_integration(hass, DOMAIN)
                version = integration.version if integration else "unknown"
                
                base_url = "/multizone_thermostat_card/multizone-thermostat-card.js"
                url = f"{base_url}?v={version}"
                
                existing_item = None
                for item in resources.async_items():
                    if item.get("url", "").startswith(base_url):
                        existing_item = item
                        break
                        
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

    _LOGGER.info(
        "Multizone Thermostat loaded: mode=%s, entity=%s, zones=%d",
        boiler_mode,
        boiler_switch or opentherm_entity,
        len(zones),
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator: MultizoneCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        coordinator.async_teardown_listeners()
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.info("Multizone Thermostat unloaded.")

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update (e.g., zones changed via Options Flow)."""
    coordinator: MultizoneCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    new_boiler = entry.data.get(CONF_BOILER_SWITCH, coordinator.boiler_switch)
    new_zones = entry.data.get(CONF_ZONES, coordinator.zones)

    _LOGGER.debug(
        "Options updated: boiler=%s, zones=%d", new_boiler, len(new_zones)
    )
