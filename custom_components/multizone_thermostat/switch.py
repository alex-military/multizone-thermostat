"""Switch platform for Multizone Thermostat: master switch + per-zone switches."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    CONF_ZONE_CLIMATE,
    CONF_ZONE_NAME,
    CONF_ZONES,
    DOMAIN,
    CONF_GEOFENCING_ENABLED,
    KEY_GEOFENCING_TOGGLE,
    KEY_AUTO_NIGHT_MODE,
    KEY_ANTI_SEIZE_ENABLED,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch entities from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    zones = config_entry.data.get(CONF_ZONES, [])

    entities: list[SwitchEntity] = []

    # Master switch
    master_switch = MultizoneMasterSwitch(coordinator, config_entry.entry_id)
    entities.append(master_switch)

    # (Zone switches are now Select entities in select.py)

    # Auto Night Mode
    entities.append(MultizoneAutoNightModeSwitch(coordinator, config_entry.entry_id))

    # Geofencing (if enabled)
    if config_entry.data.get(CONF_GEOFENCING_ENABLED, True):
        entities.append(MultizoneGeofencingSwitch(coordinator, config_entry.entry_id))

    # Anti-seize Switch
    entities.append(MultizoneAntiSeizeSwitch(coordinator, config_entry.entry_id))

    async_add_entities(entities, True)


def _make_device_info(entry_id: str, device_type: str = "main") -> DeviceInfo:
    """Create a shared device info for all entities of this integration instance."""
    if device_type == "time_geofencing":
        return DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_time_geofencing")},
            name="Time & Geofencing",
            manufacturer="Custom Integration",
            model="Time & Geofencing Settings",
            via_device=(DOMAIN, entry_id),
        )
    elif device_type == "zone_modes":
        return DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_zone_modes")},
            name="Zone Modes",
            manufacturer="Custom Integration",
            model="Zone Modes",
            via_device=(DOMAIN, entry_id),
        )
        
    return DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        name="Multizone Thermostat",
        manufacturer="Custom Integration",
        model="Multizone Thermostat",
    )


class MultizoneMasterSwitch(RestoreEntity, SwitchEntity):
    """Master switch that enables/disables the entire heating system."""

    _attr_has_entity_name = True
    _attr_translation_key = "master"
    _attr_icon = "mdi:home-thermometer"

    def __init__(self, coordinator: Any, entry_id: str) -> None:
        """Initialize master switch."""
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_master"
        self._attr_device_info = _make_device_info(entry_id)
        self._is_on: bool = False

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self._is_on

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "multizone_type": "master",
            "boiler_switch": self._coordinator.boiler_switch,
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn master on."""
        self._is_on = True
        self._coordinator.set_master_state(True)
        self.async_write_ha_state()
        await self._coordinator.async_apply_master_on()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn master off."""
        self._is_on = False
        self._coordinator.set_master_state(False)
        self.async_write_ha_state()
        await self._coordinator.async_apply_master_off()

    async def async_added_to_hass(self) -> None:
        """Restore state on HA restart."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._is_on = last_state.state == "on"
            self._coordinator.set_master_state(self._is_on)
            _LOGGER.debug("Master switch restored to: %s", self._is_on)



class MultizoneAutoNightModeSwitch(SwitchEntity):
    """Switch to enable/disable Auto Night Mode."""

    _attr_has_entity_name = True
    _attr_name = "Auto Night Mode"
    _attr_icon = "mdi:theme-light-dark"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: Any, entry_id: str) -> None:
        """Initialize switch."""
        self._coordinator = coordinator
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_auto_night"
        self._attr_device_info = _make_device_info(entry_id, "time_geofencing")

    @property
    def is_on(self) -> bool:
        """Return true if auto night mode is enabled."""
        return self._coordinator.get_persistent_data(KEY_AUTO_NIGHT_MODE, False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable auto night mode."""
        await self._coordinator.async_set_persistent_data(KEY_AUTO_NIGHT_MODE, True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable auto night mode."""
        await self._coordinator.async_set_persistent_data(KEY_AUTO_NIGHT_MODE, False)
        self.async_write_ha_state()


class MultizoneGeofencingSwitch(SwitchEntity):
    """Switch to dynamically enable/disable Geofencing."""

    _attr_has_entity_name = True
    _attr_name = "Geofencing"
    _attr_icon = "mdi:map-marker-radius"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: Any, entry_id: str) -> None:
        """Initialize switch."""
        self._coordinator = coordinator
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_geofencing"
        self._attr_device_info = _make_device_info(entry_id, "time_geofencing")

    @property
    def is_on(self) -> bool:
        """Return true if geofencing is enabled."""
        return self._coordinator.get_persistent_data(KEY_GEOFENCING_TOGGLE, True)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable geofencing."""
        await self._coordinator.async_set_persistent_data(KEY_GEOFENCING_TOGGLE, True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable geofencing."""
        await self._coordinator.async_set_persistent_data(KEY_GEOFENCING_TOGGLE, False)
        self.async_write_ha_state()

class MultizoneAntiSeizeSwitch(SwitchEntity):
    """Switch to dynamically enable/disable Anti-Seize (Summer Protection)."""

    _attr_has_entity_name = True
    _attr_name = "Anti-seize (Summer Protection)"
    _attr_icon = "mdi:valve-open"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: Any, entry_id: str) -> None:
        """Initialize switch."""
        self._coordinator = coordinator
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_anti_seize"
        self._attr_device_info = _make_device_info(entry_id)

    @property
    def is_on(self) -> bool:
        """Return true if anti-seize is enabled."""
        return self._coordinator.get_persistent_data(KEY_ANTI_SEIZE_ENABLED, False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable anti-seize."""
        await self._coordinator.async_set_persistent_data(KEY_ANTI_SEIZE_ENABLED, True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable anti-seize."""
        await self._coordinator.async_set_persistent_data(KEY_ANTI_SEIZE_ENABLED, False)
        self.async_write_ha_state()

