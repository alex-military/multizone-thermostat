"""Select platform for Multizone Thermostat: Global Preset."""
from __future__ import annotations

import logging

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
    CONF_ZONE_CLIMATE,
    CONF_ZONE_NAME,
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
        climate_id = zone[CONF_ZONE_CLIMATE]
        zone_name = zone.get(CONF_ZONE_NAME, climate_id)
        entities.append(MultizoneZoneSelect(coordinator, entry.entry_id, climate_id, zone_name))
        
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
            name="Multizone Thermostat",
            manufacturer="Custom Integration",
            model="Multizone Thermostat",
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

    def __init__(self, coordinator: MultizoneCoordinator, entry_id: str, climate_entity: str, zone_name: str) -> None:
        """Initialize the zone mode selector."""
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._climate_entity = climate_entity
        self._zone_name = zone_name
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_zone_mode_{climate_entity.replace('.', '_').replace('-', '_')}"
        self._attr_name = f"{zone_name} Mode"
        
        self._attr_options = ZONE_MODES
        self._attr_extra_state_attributes = {
            "climate_entity": climate_entity
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
        if opt == "secondary":
            return "mdi:link-variant"
        if opt == "bypass":
            return "mdi:cancel"
        return "mdi:star-circle-outline"

    @property
    def current_option(self) -> str:
        """Return the current selected option."""
        return self._coordinator.get_zone_mode(self._climate_entity)

    async def async_added_to_hass(self) -> None:
        """Restore previous state."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in self.options:
            self._coordinator.set_zone_mode(self._climate_entity, last_state.state)
        else:
            self._coordinator.set_zone_mode(self._climate_entity, ZONE_MODE_PRIMARY)
            
        self._coordinator.register_select(f"zone_mode_{self._climate_entity}", self)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option not in self.options:
            _LOGGER.warning("Invalid option: %s", option)
            return

        self._coordinator.set_zone_mode(self._climate_entity, option)
        self.async_write_ha_state()
        
        # Turn off climate if bypass, or turn on if primary/secondary and master is on
        climate_state = self.hass.states.get(self._climate_entity)
        if option == "bypass":
            if climate_state and climate_state.state != "off":
                try:
                    await self.hass.services.async_call(
                        "climate",
                        "set_hvac_mode",
                        {"entity_id": self._climate_entity, "hvac_mode": "off"},
                        blocking=False,
                    )
                except Exception as ex:
                    _LOGGER.warning("Could not turn off climate %s: %s", self._climate_entity, ex)
        else:
            if self._coordinator.get_master_state() and climate_state and climate_state.state != "heat":
                try:
                    await self.hass.services.async_call(
                        "climate",
                        "set_hvac_mode",
                        {"entity_id": self._climate_entity, "hvac_mode": "heat"},
                        blocking=False,
                    )
                except Exception as ex:
                    _LOGGER.warning("Could not turn on climate %s: %s", self._climate_entity, ex)
                    
        # Trigger an update of boiler logic (to stop/start boiler)
        # Note: _async_update_boiler is async but we don't need to await it directly if we use create_task
        self.hass.async_create_task(self._coordinator._async_update_boiler())
