"""Multizone Thermostat integration setup."""
from __future__ import annotations

import logging

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_BOILER_SWITCH,
    CONF_ZONES,
    DOMAIN,
)
from .coordinator import MultizoneCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["climate", "switch", "number", "select"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Multizone Thermostat from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    boiler_switch = entry.data[CONF_BOILER_SWITCH]
    zones = entry.data.get(CONF_ZONES, [])

    # Validate boiler switch exists
    boiler_state = hass.states.get(boiler_switch)
    if boiler_state is None:
        _LOGGER.warning(
            "Boiler switch '%s' not found. The integration will load but boiler "
            "control may not work until the entity is available.",
            boiler_switch,
        )

    # Create coordinator
    coordinator = MultizoneCoordinator(
        hass=hass,
        entry_id=entry.entry_id,
        boiler_switch=boiler_switch,
        zones=zones,
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
        "Multizone Thermostat loaded: boiler=%s, zones=%d",
        boiler_switch,
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

    # Reload the entire entry to apply zone additions/removals
    await hass.config_entries.async_reload(entry.entry_id)
