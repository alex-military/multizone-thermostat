"""Multizone Thermostat integration setup."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_BOILER_SWITCH,
    CONF_ZONES,
    DOMAIN,
)
from .coordinator import MultizoneCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["switch"]


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

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
    }

    # Set up state listeners
    coordinator.async_setup_listeners()

    # Set up platforms (switch)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

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
