"""Select platform for Multizone Thermostat: Global Preset."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    DOMAIN,
    GLOBAL_PRESET_NONE,
    GLOBAL_PRESETS,
)
from .coordinator import MultizoneCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select platform."""
    coordinator: MultizoneCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities([MultizoneGlobalPresetSelect(coordinator, entry.entry_id)])


class MultizoneGlobalPresetSelect(RestoreEntity, SelectEntity):
    """Global preset selector for the entire heating system."""

    _attr_has_entity_name = True
    _attr_translation_key = "global_preset"
    _attr_icon = "mdi:home-thermometer"

    def __init__(self, coordinator: MultizoneCoordinator, entry_id: str) -> None:
        """Initialize the global preset selector."""
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_global_preset"
        
        self._attr_options = GLOBAL_PRESETS
        self._current_option = GLOBAL_PRESET_NONE

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name="Multizone Thermostat",
            manufacturer="alex-military",
            model="Heating Controller",
        )

    @property
    def current_option(self) -> str:
        """Return the current selected option."""
        return self._current_option

    async def async_added_to_hass(self) -> None:
        """Restore previous state."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in self.options:
            self._current_option = last_state.state
        else:
            self._current_option = GLOBAL_PRESET_NONE
            
        self._coordinator.set_global_preset(self._current_option)
        _LOGGER.debug("Global preset restored to: %s", self._current_option)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option not in self.options:
            _LOGGER.warning("Invalid option: %s", option)
            return

        self._current_option = option
        self.async_write_ha_state()
        
        # Notify coordinator to apply the new preset to all zones
        await self._coordinator.async_set_global_preset(option)
