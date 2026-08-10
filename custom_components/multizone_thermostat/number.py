"""Number platform for Multizone Thermostat: boiler protection parameters."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, RestoreNumber
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_MIN_CYCLE_ON,
    CONF_MIN_CYCLE_OFF,
    CONF_VALVE_DELAY,
    DEFAULT_MIN_CYCLE_ON,
    DEFAULT_MIN_CYCLE_OFF,
    DEFAULT_VALVE_DELAY,
    DOMAIN,
    KEY_ANTI_SEIZE_IDLE_DAYS,
    KEY_ANTI_SEIZE_DURATION,
    KEY_WEATHER_CURVE,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number entities from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    def _make_device_info() -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name="Master Control",
            manufacturer="Custom Integration",
            model="Master Control",
        )

    device_info = _make_device_info()

    entities = [
        MultizoneProtectionNumber(
            coordinator=coordinator,
            entry_id=config_entry.entry_id,
            key=CONF_MIN_CYCLE_ON,
            name="Min Cycle ON",
            min_value=0,
            max_value=60,
            step=1,
            unit_of_measurement="min",
            icon="mdi:timer-sand",
            default_val=DEFAULT_MIN_CYCLE_ON,
            device_info=device_info,
        ),
        MultizoneProtectionNumber(
            coordinator=coordinator,
            entry_id=config_entry.entry_id,
            key=CONF_MIN_CYCLE_OFF,
            name="Min Cycle OFF",
            min_value=0,
            max_value=60,
            step=1,
            unit_of_measurement="min",
            icon="mdi:timer-sand-empty",
            default_val=DEFAULT_MIN_CYCLE_OFF,
            device_info=device_info,
        ),
        MultizoneProtectionNumber(
            coordinator=coordinator,
            entry_id=config_entry.entry_id,
            key=CONF_VALVE_DELAY,
            name="Valve Delay",
            min_value=0,
            max_value=300,
            step=1,
            unit_of_measurement="s",
            icon="mdi:valve",
            default_val=DEFAULT_VALVE_DELAY,
            device_info=device_info,
        ),
        MultizonePersistentNumber(
            coordinator=coordinator,
            entry_id=config_entry.entry_id,
            key=KEY_ANTI_SEIZE_IDLE_DAYS,
            name="Anti-seize Idle Days",
            min_value=1,
            max_value=30,
            step=1,
            unit_of_measurement="days",
            icon="mdi:calendar-clock",
            default_val=15,
            device_info=device_info,
        ),
        MultizonePersistentNumber(
            coordinator=coordinator,
            entry_id=config_entry.entry_id,
            key=KEY_ANTI_SEIZE_DURATION,
            name="Anti-seize Duration",
            min_value=1,
            max_value=15,
            step=1,
            unit_of_measurement="min",
            icon="mdi:timer-outline",
            default_val=2,
            device_info=device_info,
        ),
        MultizonePersistentNumber(
            coordinator=coordinator,
            entry_id=config_entry.entry_id,
            key=KEY_WEATHER_CURVE,
            name="Weather Curve",
            min_value=0.0,
            max_value=3.0,
            step=0.1,
            unit_of_measurement="",
            icon="mdi:chart-bell-curve-cumulative",
            default_val=0.0,
            device_info=device_info,
        ),
    ]

    async_add_entities(entities)


class MultizoneProtectionNumber(RestoreNumber):
    """Number entity to control boiler protection parameters."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator,
        entry_id: str,
        key: str,
        name: str,
        min_value: float,
        max_value: float,
        step: float,
        unit_of_measurement: str,
        icon: str,
        default_val: float,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the number entity."""
        self._coordinator = coordinator
        self._key = key
        self._default_val = default_val

        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{key}"
        self._attr_name = name
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_icon = icon
        self._attr_device_info = device_info

        # State
        self._attr_native_value = float(default_val)

    async def async_added_to_hass(self) -> None:
        """Restore previous state on startup."""
        await super().async_added_to_hass()
        last_number_data = await self.async_get_last_number_data()

        if last_number_data is not None and last_number_data.native_value is not None:
            self._attr_native_value = last_number_data.native_value
            _LOGGER.debug(
                "Restored %s to value: %s", self._attr_unique_id, self._attr_native_value
            )
        else:
            self._attr_native_value = float(self._default_val)
            
        # Push the restored/default value to the coordinator
        self._update_coordinator(int(self._attr_native_value))
        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        """Update the value."""
        self._attr_native_value = value
        self._update_coordinator(int(value))
        self.async_write_ha_state()

    def _update_coordinator(self, value: int) -> None:
        """Push value to the coordinator."""
        if self._key == CONF_MIN_CYCLE_ON:
            self._coordinator.set_min_cycle_on(value)
        elif self._key == CONF_MIN_CYCLE_OFF:
            self._coordinator.set_min_cycle_off(value)
        elif self._key == CONF_VALVE_DELAY:
            self._coordinator.set_valve_delay(value)

class MultizonePersistentNumber(NumberEntity):
    """Generic Number entity that saves its state to the coordinator persistent storage."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator,
        entry_id: str,
        key: str,
        name: str,
        min_value: float,
        max_value: float,
        step: float,
        unit_of_measurement: str,
        icon: str,
        default_val: float,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the number entity."""
        self._coordinator = coordinator
        self._key = key
        self._default_val = default_val

        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{key}"
        self._attr_name = name
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_icon = icon
        self._attr_device_info = device_info

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self._coordinator.get_persistent_data(self._key, self._default_val)

    async def async_set_native_value(self, value: float) -> None:
        """Update the value."""
        await self._coordinator.async_set_persistent_data(self._key, value)
        self.async_write_ha_state()
