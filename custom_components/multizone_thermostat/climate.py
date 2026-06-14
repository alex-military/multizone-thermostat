"""Climate platform for Multizone Thermostat: virtual thermostats."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    CONF_VIRTUAL_THERMOSTATS,
    CONF_VT_HEATER_SWITCH,
    CONF_VT_NAME,
    CONF_VT_TARGET_TEMP,
    CONF_VT_TEMP_SENSOR,
    CONF_VT_TOLERANCE,
    DEFAULT_VT_TARGET_TEMP,
    DEFAULT_VT_TOLERANCE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual thermostat climate entities from a config entry."""
    virtual_thermostats = config_entry.data.get(CONF_VIRTUAL_THERMOSTATS, [])

    if not virtual_thermostats:
        return

    entities = []
    for vt_config in virtual_thermostats:
        entities.append(
            MultizoneVirtualThermostat(
                hass=hass,
                entry_id=config_entry.entry_id,
                name=vt_config[CONF_VT_NAME],
                temp_sensor=vt_config[CONF_VT_TEMP_SENSOR],
                heater_switch=vt_config[CONF_VT_HEATER_SWITCH],
                target_temp=vt_config.get(CONF_VT_TARGET_TEMP, DEFAULT_VT_TARGET_TEMP),
                tolerance=vt_config.get(CONF_VT_TOLERANCE, DEFAULT_VT_TOLERANCE),
            )
        )

    async_add_entities(entities)


def _make_vt_entity_id(name: str) -> str:
    """Generate a predictable entity_id for a virtual thermostat."""
    safe = name.lower().replace(" ", "_").replace("-", "_")
    # Remove non-alphanumeric chars except underscore
    safe = "".join(c for c in safe if c.isalnum() or c == "_")
    return f"climate.{DOMAIN}_vt_{safe}"


class MultizoneVirtualThermostat(RestoreEntity, ClimateEntity):
    """A virtual thermostat that controls a heater switch based on a temperature sensor."""

    _attr_has_entity_name = True
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = 5.0
    _attr_max_temp = 35.0
    _attr_target_temperature_step = 0.5

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        name: str,
        temp_sensor: str,
        heater_switch: str,
        target_temp: float,
        tolerance: float,
    ) -> None:
        """Initialize the virtual thermostat."""
        self.hass = hass
        self._entry_id = entry_id
        self._name = name
        self._temp_sensor = temp_sensor
        self._heater_switch = heater_switch
        self._tolerance = tolerance

        # State
        self._hvac_mode = HVACMode.OFF
        self._target_temperature = target_temp
        self._current_temperature: float | None = None

        # Entity setup
        safe_name = name.lower().replace(" ", "_").replace("-", "_")
        safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_vt_{safe_name}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="Multizone Thermostat",
            manufacturer="Custom Integration",
            model="Multizone Thermostat",
        )

        # We explicitly set entity_id so the zone config can reference it
        self.entity_id = f"climate.{DOMAIN}_vt_{safe_name}"

        self._unsub_listeners: list = []

    @property
    def name(self) -> str:
        """Return the name."""
        return f"VT {self._name}"

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        return self._hvac_mode

    @property
    def hvac_action(self) -> HVACAction:
        """Return current HVAC action."""
        if self._hvac_mode == HVACMode.OFF:
            return HVACAction.OFF

        # Check if the heater is actually on
        heater_state = self.hass.states.get(self._heater_switch)
        if heater_state and heater_state.state == STATE_ON:
            return HVACAction.HEATING
        return HVACAction.IDLE

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        return self._target_temperature

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        return {
            "temperature_sensor": self._temp_sensor,
            "heater_switch": self._heater_switch,
            "tolerance": self._tolerance,
            "virtual_thermostat": True,
        }

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        self._hvac_mode = hvac_mode

        if hvac_mode == HVACMode.OFF:
            await self._async_heater_turn_off()
        elif hvac_mode == HVACMode.HEAT:
            await self._async_control()

        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        self._target_temperature = temperature
        if self._hvac_mode == HVACMode.HEAT:
            await self._async_control()
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Restore state and set up listeners."""
        await super().async_added_to_hass()

        # Restore previous state
        last_state = await self.async_get_last_state()
        if last_state is not None:
            if last_state.state in (HVACMode.HEAT, HVACMode.OFF):
                self._hvac_mode = HVACMode(last_state.state)
            if last_state.attributes.get(ATTR_TEMPERATURE) is not None:
                self._target_temperature = float(last_state.attributes[ATTR_TEMPERATURE])
            _LOGGER.debug(
                "VT '%s' restored: mode=%s, target=%s",
                self._name, self._hvac_mode, self._target_temperature,
            )

        # Read current temperature
        self._update_current_temp()

        # Listen for temperature sensor changes
        self._unsub_listeners.append(
            async_track_state_change_event(
                self.hass,
                [self._temp_sensor],
                self._async_on_temp_changed,
            )
        )

        # Listen for heater switch changes (to update hvac_action)
        self._unsub_listeners.append(
            async_track_state_change_event(
                self.hass,
                [self._heater_switch],
                self._async_on_heater_changed,
            )
        )

        # Initial control pass
        if self._hvac_mode == HVACMode.HEAT:
            await self._async_control()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up listeners."""
        for unsub in self._unsub_listeners:
            unsub()
        self._unsub_listeners.clear()

    @callback
    def _update_current_temp(self) -> None:
        """Read the temperature sensor and update current temperature."""
        state = self.hass.states.get(self._temp_sensor)
        if state and state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            try:
                self._current_temperature = float(state.state)
            except (ValueError, TypeError):
                _LOGGER.warning(
                    "VT '%s': unable to parse temperature from %s: '%s'",
                    self._name, self._temp_sensor, state.state,
                )

    @callback
    def _async_on_temp_changed(self, event: Event) -> None:
        """Handle temperature sensor state changes."""
        new_state = event.data.get("new_state")
        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return

        try:
            self._current_temperature = float(new_state.state)
        except (ValueError, TypeError):
            return

        if self._hvac_mode == HVACMode.HEAT:
            self.hass.async_create_task(self._async_control())

        self.async_write_ha_state()

    @callback
    def _async_on_heater_changed(self, event: Event) -> None:
        """Handle heater switch state changes (update hvac_action display)."""
        self.async_write_ha_state()

    async def _async_control(self) -> None:
        """Core thermostat logic: turn heater on/off based on temperature."""
        if self._current_temperature is None:
            return

        if self._hvac_mode != HVACMode.HEAT:
            return

        too_cold = self._current_temperature < (self._target_temperature - self._tolerance)
        too_hot = self._current_temperature > (self._target_temperature + self._tolerance)

        heater_state = self.hass.states.get(self._heater_switch)
        heater_on = heater_state is not None and heater_state.state == STATE_ON

        if too_cold and not heater_on:
            _LOGGER.debug(
                "VT '%s': temp %.1f < target %.1f - tol %.1f → heater ON",
                self._name, self._current_temperature,
                self._target_temperature, self._tolerance,
            )
            await self._async_heater_turn_on()
        elif too_hot and heater_on:
            _LOGGER.debug(
                "VT '%s': temp %.1f > target %.1f + tol %.1f → heater OFF",
                self._name, self._current_temperature,
                self._target_temperature, self._tolerance,
            )
            await self._async_heater_turn_off()

    async def _async_heater_turn_on(self) -> None:
        """Turn the heater switch on."""
        await self.hass.services.async_call(
            "switch",
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: self._heater_switch},
            blocking=False,
        )

    async def _async_heater_turn_off(self) -> None:
        """Turn the heater switch off."""
        await self.hass.services.async_call(
            "switch",
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: self._heater_switch},
            blocking=False,
        )
