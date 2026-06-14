"""Switch platform for Multizone Thermostat: master switch + per-zone switches."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    CONF_ZONE_CLIMATE,
    CONF_ZONE_NAME,
    CONF_ZONES,
    DOMAIN,
    SWITCH_MASTER_SUFFIX,
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

    # Per-zone switches
    for zone in zones:
        zone_switch = MultizoneZoneSwitch(
            coordinator=coordinator,
            entry_id=config_entry.entry_id,
            zone_name=zone[CONF_ZONE_NAME],
            climate_entity=zone[CONF_ZONE_CLIMATE],
        )
        entities.append(zone_switch)

    async_add_entities(entities, True)


def _make_device_info(entry_id: str) -> DeviceInfo:
    """Create a shared device info for all entities of this integration instance."""
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
        # Register with coordinator
        self._coordinator.register_switch("master", self)


class MultizoneZoneSwitch(RestoreEntity, SwitchEntity):
    """Switch for an individual heating zone."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:radiator"

    def __init__(
        self,
        coordinator: Any,
        entry_id: str,
        zone_name: str,
        climate_entity: str,
    ) -> None:
        """Initialize zone switch."""
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._zone_name = zone_name
        self._climate_entity = climate_entity
        self._is_on: bool = True  # Default: zone enabled

        # Unique ID based on climate entity to survive renames
        safe_id = climate_entity.replace(".", "_").replace("-", "_")
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_zone_{safe_id}"
        self._attr_device_info = _make_device_info(entry_id)

    @property
    def name(self) -> str:
        """Return zone name."""
        return self._zone_name

    @property
    def is_on(self) -> bool:
        """Return true if zone is enabled."""
        return self._is_on

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "climate_entity": self._climate_entity,
            "zone_name": self._zone_name,
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable this zone."""
        self._is_on = True
        self._coordinator.set_zone_state(self._climate_entity, True)
        self.async_write_ha_state()
        await self._coordinator.async_apply_zone_on(self._climate_entity)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable this zone."""
        self._is_on = False
        self._coordinator.set_zone_state(self._climate_entity, False)
        self.async_write_ha_state()
        await self._coordinator.async_apply_zone_off(self._climate_entity)

    async def async_added_to_hass(self) -> None:
        """Restore state on HA restart."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._is_on = last_state.state == "on"
            self._coordinator.set_zone_state(self._climate_entity, self._is_on)
            _LOGGER.debug(
                "Zone switch '%s' restored to: %s", self._zone_name, self._is_on
            )
        # Register with coordinator
        self._coordinator.register_switch(self._climate_entity, self)
