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
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
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
    make_vt_entity_id,
    # ===== НОВЫЕ ИМПОРТЫ =====
    CONF_VT_COOLER_SWITCH,
    CONF_VT_COOL_TOLERANCE,
    DEFAULT_VT_COOL_TOLERANCE,
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
                # ===== НОВЫЕ ПАРАМЕТРЫ =====
                cooler_switch=vt_config.get(CONF_VT_COOLER_SWITCH),
                cool_tolerance=vt_config.get(CONF_VT_COOL_TOLERANCE, DEFAULT_VT_COOL_TOLERANCE),
            )
        )
    async_add_entities(entities)


from .pwm_engine import PWMEngine

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
        self._name = name
        self._temp_sensor = temp_sensor
        self._heater_switch = heater_switch
        self._tolerance = tolerance

        # State
        self._hvac_mode = HVACMode.OFF
        self._target_temperature = target_temp
        self._current_temperature: float | None = None
        
        self._coordinator = hass.data[DOMAIN][entry_id]["coordinator"]
        
        # PWM Engine for local zone valve
        self._valve_pwm = PWMEngine(pwm_interval=900.0, min_on=0.0, min_off=0.0)

        # Entity setup
        vt_entity_id = make_vt_entity_id(name)
        # unique_id uses the entry_id to be unique per config entry
        safe_name = name.lower().replace(" ", "_").replace("-", "_")
        safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_vt_{safe_name}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_virtual_thermostats")},
            name="Virtual Thermostats",
            manufacturer="Custom Integration",
            model="Virtual Thermostats",
            via_device=(DOMAIN, entry_id),
        )

        # We explicitly set entity_id so the zone config can reference it
        self.entity_id = vt_entity_id

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
        
        # Start periodic PWM evaluation for the zone valve (every 10 seconds)
        from datetime import timedelta
        self._unsub_listeners.append(
            async_track_time_interval(
                self.hass,
                self._async_pwm_tick,
                timedelta(seconds=10)
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
        """Calculate PID demand when state changes."""
        if self._current_temperature is None:
            return

        if self._hvac_mode != HVACMode.HEAT:
            self._coordinator.set_zone_demand(self.entity_id, 0.0)
            return

        # Calculate PID Demand
        # The PID demand is now calculated by the Coordinator in _async_on_climate_state_changed
        demand = self._coordinator.get_zone_demand(self.entity_id)
        if demand is not None:
            _LOGGER.debug("VT '%s': Reading PID Demand from coordinator: %.1f%%", self._name, demand)
        else:
            _LOGGER.debug("VT '%s': No demand available yet from coordinator", self._name)
        
        # We immediately call the PWM tick so the valve responds without waiting 10s
        from datetime import datetime
        await self._async_pwm_tick(datetime.now())

    async def _async_pwm_tick(self, now) -> None:
        """Periodic tick to evaluate PWM state for the zone valve."""
        if self._hvac_mode != HVACMode.HEAT or not self._coordinator.get_master_state():
            await self._async_heater_turn_off()
            return
            
        demand = self._coordinator.get_zone_demand(self.entity_id)
        wanted_state = self._valve_pwm.calculate(demand)
        
        heater_state = self.hass.states.get(self._heater_switch)
        heater_on = heater_state is not None and heater_state.state == STATE_ON
        
        if wanted_state and not heater_on:
            _LOGGER.debug("VT '%s': PWM Valve → ON", self._name)
            await self._async_heater_turn_on()
        elif not wanted_state and heater_on:
            _LOGGER.debug("VT '%s': PWM Valve → OFF", self._name)
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
