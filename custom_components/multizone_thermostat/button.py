"""Button platform for Multizone Thermostat: per-zone autotuner reset."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ZONE_NAME, DOMAIN, make_zone_entity_id

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entities from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    device_info = DeviceInfo(
        identifiers={(DOMAIN, config_entry.entry_id)},
        name="Master Control",
        manufacturer="Custom Integration",
        model="Master Control",
    )

    entities: list[ButtonEntity] = []
    for zone in coordinator.zones:
        zone_name = zone.get(CONF_ZONE_NAME)
        if not zone_name:
            continue
        entities.append(
            MultizoneResetAutotuneButton(
                coordinator,
                config_entry.entry_id,
                zone_name,
                device_info,
            )
        )

    async_add_entities(entities)


class MultizoneResetAutotuneButton(ButtonEntity):
    """Master Control button to reset a zone's Smart PID autotuner."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:restart-alert"

    def __init__(
        self,
        coordinator: Any,
        entry_id: str,
        zone_name: str,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the reset autotuner button."""
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._zone_name = zone_name
        self._climate_id = make_zone_entity_id(zone_name)

        safe_name = zone_name.lower().replace(" ", "_").replace("-", "_")
        safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_reset_autotune_{safe_name}"
        self._attr_name = f"{zone_name} Reset Autotuner"
        self._attr_device_info = device_info

    async def async_press(self) -> None:
        """Reset autotuner cycles and learned gains for this zone."""
        if hasattr(self._coordinator, "zone_controller"):
            await self._coordinator.zone_controller.async_reset_zone_autotuner(self._climate_id)
        if hasattr(self._coordinator, "async_notify_pid_entities"):
            self._coordinator.async_notify_pid_entities()
        _LOGGER.info("Reset Autotuner button pressed for zone %s (%s)", self._zone_name, self._climate_id)
