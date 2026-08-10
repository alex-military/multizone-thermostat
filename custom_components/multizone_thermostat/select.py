"""Select platform for Multizone Thermostat: Global Preset."""
from __future__ import annotations

import logging

from homeassistant.components.climate import HVACMode
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    DOMAIN,
    GLOBAL_PRESET_MANUAL,
    GLOBAL_PRESETS,
    ZONE_MODES,
    ZONE_MODE_PRIMARY,
    ZONE_MODE_SECONDARY,
    ZONE_MODE_BYPASS,
    CONF_ZONE_NAME,
    make_zone_entity_id,
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

    entities: list[SelectEntity] = [MultizoneGlobalPresetSelect(coordinator, entry.entry_id)]
    
    for zone in coordinator.zones:
        zone_name = zone[CONF_ZONE_NAME]
        entities.append(MultizoneZoneSelect(coordinator, entry.entry_id, zone_name))
        
    async_add_entities(entities)


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

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name="Master Control",
            manufacturer="Custom Integration",
            model="Master Control",
        )

    @property
    def current_option(self) -> str:
        """Return the current selected option."""
        return self._coordinator.current_global_preset

    async def async_added_to_hass(self) -> None:
        """Restore previous state."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in self.options:
            self._coordinator.set_global_preset(last_state.state)
        else:
            self._coordinator.set_global_preset(GLOBAL_PRESET_MANUAL)
            
        self._coordinator.register_select("global_preset", self)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option not in self.options:
            _LOGGER.warning("Invalid option: %s", option)
            return

        # Notify coordinator to apply the new preset to all zones
        await self._coordinator.async_set_global_preset(option)


class MultizoneZoneSelect(RestoreEntity, SelectEntity):
    """Zone mode selector for each zone."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: MultizoneCoordinator, entry_id: str, zone_name: str) -> None:
        """Initialize the zone mode selector."""
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._zone_name = zone_name
        self._climate_id = make_zone_entity_id(zone_name)
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_zone_mode_{self._climate_id.replace('.', '_')}"
        self._attr_name = f"{zone_name} Mode"
        
        self._attr_options = ZONE_MODES
        self._attr_extra_state_attributes = {
            "zone_name": zone_name,
            "climate_entity": self._climate_id
        }

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._entry_id}_zone_modes")},
            name="Zone Modes",
            manufacturer="Custom Integration",
            model="Zone Modes",
            via_device=(DOMAIN, self._entry_id),
        )

    @property
    def icon(self) -> str:
        """Return the icon based on the current option."""
        opt = self.current_option
        if opt == ZONE_MODE_SECONDARY:
            return "mdi:link-variant"
        if opt == ZONE_MODE_BYPASS:
            return "mdi:cancel"
        return "mdi:star-circle-outline"

    @property
    def current_option(self) -> str:
        """Return the current selected option."""
        return self._coordinator.get_zone_mode(self._climate_id)

    async def async_added_to_hass(self) -> None:
        """Restore previous state."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in self.options:
            self._coordinator.set_zone_mode(self._climate_id, last_state.state)
        else:
            self._coordinator.set_zone_mode(self._climate_id, ZONE_MODE_PRIMARY)
            
        self._coordinator.register_select(f"zone_mode_{self._climate_id}", self)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option not in self.options:
            _LOGGER.warning("Invalid option: %s", option)
            return

        # Notify coordinator
        self._coordinator.set_zone_mode(self._climate_id, option)
        self.async_write_ha_state()
        
        # Turn off climate if bypass, or turn on if primary/secondary and master is on
        climate_state = self.hass.states.get(self._climate_id)
        if option == ZONE_MODE_BYPASS:
            if climate_state and climate_state.state != HVACMode.OFF:
                try:
                    await self.hass.services.async_call(
                        "climate",
                        "set_hvac_mode",
                        {"entity_id": self._climate_id, "hvac_mode": HVACMode.OFF},
                        blocking=False,
                    )
                except Exception as ex:
                    _LOGGER.warning("Could not turn off climate %s: %s", self._climate_id, ex)
        else:
            if self._coordinator.get_master_state() and climate_state and climate_state.state != HVACMode.HEAT:
                try:
                    await self.hass.services.async_call(
                        "climate",
                        "set_hvac_mode",
                        {"entity_id": self._climate_id, "hvac_mode": HVACMode.HEAT},
                        blocking=False,
                    )
                except Exception as ex:
                    _LOGGER.warning("Could not turn on climate %s: %s", self._climate_id, ex)
                    
