"""Time platform for Multizone Thermostat."""
from __future__ import annotations

import datetime
import logging

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, KEY_NIGHT_TIME, KEY_MORNING_TIME

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the time entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([
        MultizoneNightTimeEntity(coordinator, entry.entry_id),
        MultizoneMorningTimeEntity(coordinator, entry.entry_id),
    ])


class MultizoneNightTimeEntity(TimeEntity):
    """Representation of the Night Time setting."""

    _attr_has_entity_name = True
    _attr_name = "Night Time"
    _attr_icon = "mdi:clock-time-ten-outline"

    def __init__(self, coordinator, entry_id: str) -> None:
        """Initialize the time entity."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_night_time"
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry_id}_time_geofencing")},
            "name": "Time & Geofencing",
            "manufacturer": "Custom Integration",
            "model": "Time & Geofencing Settings",
            "via_device": (DOMAIN, entry_id),
        }

    @property
    def native_value(self) -> datetime.time | None:
        """Return the value of the time entity."""
        # Read from coordinator persistent data
        time_str = self.coordinator.get_persistent_data(KEY_NIGHT_TIME, "22:30")
        try:
            hour, minute = map(int, time_str.split(":"))
            return datetime.time(hour=hour, minute=minute)
        except (ValueError, AttributeError):
            return datetime.time(22, 30)

    async def async_set_value(self, value: datetime.time) -> None:
        """Update the time."""
        time_str = f"{value.hour:02d}:{value.minute:02d}"
        await self.coordinator.async_set_persistent_data(KEY_NIGHT_TIME, time_str)
        self.async_write_ha_state()


class MultizoneMorningTimeEntity(TimeEntity):
    """Representation of the Morning Time setting."""

    _attr_has_entity_name = True
    _attr_name = "Morning Time"
    _attr_icon = "mdi:clock-time-seven-outline"

    def __init__(self, coordinator, entry_id: str) -> None:
        """Initialize the time entity."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_morning_time"
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry_id}_time_geofencing")},
            "name": "Time & Geofencing",
            "manufacturer": "Custom Integration",
            "model": "Time & Geofencing Settings",
            "via_device": (DOMAIN, entry_id),
        }

    @property
    def native_value(self) -> datetime.time | None:
        """Return the value of the time entity."""
        time_str = self.coordinator.get_persistent_data(KEY_MORNING_TIME, "07:00")
        try:
            hour, minute = map(int, time_str.split(":"))
            return datetime.time(hour=hour, minute=minute)
        except (ValueError, AttributeError):
            return datetime.time(7, 0)

    async def async_set_value(self, value: datetime.time) -> None:
        """Update the time."""
        time_str = f"{value.hour:02d}:{value.minute:02d}"
        await self.coordinator.async_set_persistent_data(KEY_MORNING_TIME, time_str)
        self.async_write_ha_state()
