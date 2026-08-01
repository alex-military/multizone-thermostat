"""Climate platform for Multizone Thermostat: virtual thermostats."""
from __future__ import annotations

import logging
from typing import Any
from datetime import timedelta

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
    CONF_VT_COOLER_SWITCH,
    CONF_VT_COOL_TOLERANCE,
    DEFAULT_VT_COOL_TOLERANCE,
    CONF_VT_PRESET_TEMPS,
    DEFAULT_VT_PRESET_TEMPS,
    GLOBAL_PRESETS,
)
from .pwm_engine import PWMEngine

_LOGGER = logging.getLogger(__name__)

# ===== ЛОКАЛЬНАЯ ФУНКЦИЯ =====
def make_vt_entity_id(name: str) -> str:
    """Generate entity_id for a virtual thermostat."""
    safe_name = name.lower().replace(" ", "_")
    safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
    return f"climate.vt_{safe_name}"


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
                cooler_switch=vt_config.get(CONF_VT_COOLER_SWITCH),
                cool_tolerance=vt_config.get(CONF_VT_COOL_TOLERANCE, DEFAULT_VT_COOL_TOLERANCE),
                preset_temperatures=vt_config.get(CONF_VT_PRESET_TEMPS, DEFAULT_VT_PRESET_TEMPS),
            )
        )
    async_add_entities(entities)


class MultizoneVirtualThermostat(RestoreEntity, ClimateEntity):
    """A virtual thermostat that controls a heater and optionally a cooler switch, with presets."""

    _attr_has_entity_name = True
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = 5.0
    _attr_max_temp = 35.0
    _attr_target_temperature_step = 0.5
    _attr_preset_modes = GLOBAL_PRESETS

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        name: str,
        temp_sensor: str,
        heater_switch: str,
        target_temp: float,
        tolerance: float,
        cooler_switch: str | None = None,
        cool_tolerance: float = DEFAULT_VT_COOL_TOLERANCE,
        preset_temperatures: dict[str, float] = DEFAULT_VT_PRESET_TEMPS,
    ) -> None:
        """Initialize the virtual thermostat."""
        self.hass = hass
        self._name = name
        self._temp_sensor = temp_sensor
        self._heater_switch = heater_switch
        self._tolerance = tolerance
        self._cooler_switch = cooler_switch
        self._cool_tolerance = cool_tolerance
        self._preset_temperatures = preset_temperatures

        # State
        self._hvac_mode = HVACMode.OFF
        self._target_temperature = target_temp
        self._current_temperature: float | None = None
        self._preset_mode: str | None = None
        self._coordinator = hass.data[DOMAIN][entry_id]["coordinator"]

        # PWM Engine for local zone valve (heating only)
        self._valve_pwm = PWMEngine(pwm_interval=900.0, min_on=0.0, min_off=0.0)

        # State of switches (cached)
        self._heater_state: bool | None = None
        self._cooler_state: bool | None = None

        # Entity setup
        vt_entity_id = make_vt_entity_id(name)
        safe_name = name.lower().replace(" ", "_")
        safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_vt_{safe_name}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_virtual_thermostats")},
            name="Virtual Thermostats",
            manufacturer="Custom Integration",
            model="Virtual Thermostats",
            via_device=(DOMAIN, entry_id),
        )
        self.entity_id = vt_entity_id

        self._unsub_listeners: list = []

    @property
    def name(self) -> str:
        """Return the name."""
        return f"VT {self._name}"

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return the list of available hvac modes."""
        modes = [HVACMode.OFF, HVACMode.HEAT]
        if self._cooler_switch is not None:
            modes.append(HVACMode.COOL)
            modes.append(HVACMode.HEAT_COOL)
        return modes

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        return self._hvac_mode

    @property
    def hvac_action(self) -> HVACAction:
        """Return current HVAC action."""
        if self._hvac_mode == HVACMode.OFF:
            return HVACAction.OFF

        if self._heater_state:
            return HVACAction.HEATING
        if self._cooler_state:
            return HVACAction.COOLING
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
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        return self._preset_mode

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        attrs = {
            "temperature_sensor": self._temp_sensor,
            "heater_switch": self._heater_switch,
            "tolerance": self._tolerance,
            "virtual_thermostat": True,
        }
        if self._cooler_switch is not None:
            attrs["cooler_switch"] = self._cooler_switch
            attrs["cool_tolerance"] = self._cool_tolerance
        if self._preset_mode is not None:
            attrs["preset_mode"] = self._preset_mode
        return attrs

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        if hvac_mode not in self.hvac_modes:
            raise ValueError(f"Unsupported HVAC mode: {hvac_mode}")
        if hvac_mode == HVACMode.COOL and self._cooler_switch is None:
            raise ValueError("Cooling not supported")
        self._hvac_mode = hvac_mode
        self.async_write_ha_state()
        await self._async_control()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        self._target_temperature = temperature
        # Manual change clears preset
        self._preset_mode = None
        self.async_write_ha_state()
        await self._async_control()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode and update target temperature."""
        if preset_mode not in self._attr_preset_modes:
            raise ValueError(f"Unsupported preset mode: {preset_mode}")
        if preset_mode not in self._preset_temperatures:
            _LOGGER.warning("No temperature defined for preset %s, keeping current", preset_mode)
            self._preset_mode = preset_mode
            self.async_write_ha_state()
            return

        self._preset_mode = preset_mode
        self._target_temperature = self._preset_temperatures[preset_mode]
        _LOGGER.debug("VT '%s' preset %s set to %.1f°C", self._name, preset_mode, self._target_temperature)
        self.async_write_ha_state()
        await self._async_control()

    async def async_added_to_hass(self) -> None:
        """Restore state and set up listeners."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state is not None:
            if last_state.state in (HVACMode.HEAT, HVACMode.COOL, HVACMode.HEAT_COOL, HVACMode.OFF):
                self._hvac_mode = HVACMode(last_state.state)
            if last_state.attributes.get(ATTR_TEMPERATURE) is not None:
                self._target_temperature = float(last_state.attributes[ATTR_TEMPERATURE])
            # Restore preset mode if saved
            if last_state.attributes.get("preset_mode") in self._attr_preset_modes:
                self._preset_mode = last_state.attributes["preset_mode"]
            _LOGGER.debug(
                "VT '%s' restored: mode=%s, target=%s, preset=%s",
                self._name, self._hvac_mode, self._target_temperature, self._preset_mode,
            )

        self._update_current_temp()

        self._unsub_listeners.append(
            async_track_state_change_event(
                self.hass,
                [self._temp_sensor],
                self._async_on_temp_changed,
            )
        )

        self._unsub_listeners.append(
            async_track_state_change_event(
                self.hass,
                [self._heater_switch],
                self._async_on_heater_changed,
            )
        )

        if self._cooler_switch is not None:
            self._unsub_listeners.append(
                async_track_state_change_event(
                    self.hass,
                    [self._cooler_switch],
                    self._async_on_cooler_changed,
                )
            )

        self._unsub_listeners.append(
            async_track_time_interval(
                self.hass,
                self._async_pwm_tick,
                timedelta(seconds=10)
            )
        )

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
        self.hass.async_create_task(self._async_control())
        self.async_write_ha_state()

    @callback
    def _async_on_heater_changed(self, event: Event) -> None:
        """Handle heater switch state changes."""
        state = self.hass.states.get(self._heater_switch)
        if state is not None:
            self._heater_state = state.state == STATE_ON
        self.async_write_ha_state()

    @callback
    def _async_on_cooler_changed(self, event: Event) -> None:
        """Handle cooler switch state changes."""
        if self._cooler_switch is None:
            return
        state = self.hass.states.get(self._cooler_switch)
        if state is not None:
            self._cooler_state = state.state == STATE_ON
        self.async_write_ha_state()

    async def _async_control(self) -> None:
        """Main control logic: decide what to turn on/off based on mode."""
        if self._current_temperature is None:
            return

        target = self._target_temperature
        current = self._current_temperature

        need_heat = current < target - self._tolerance
        need_cool = current > target + self._cool_tolerance

        if self._hvac_mode == HVACMode.OFF:
            await self._async_set_heater(False)
            await self._async_set_cooler(False)
            self._coordinator.set_zone_demand(self.entity_id, 0.0)

        elif self._hvac_mode == HVACMode.HEAT:
            await self._async_set_cooler(False)
            if self._coordinator.get_master_state():
                demand = 100.0 if need_heat else 0.0
                self._coordinator.set_zone_demand(self.entity_id, demand)
            else:
                self._coordinator.set_zone_demand(self.entity_id, 0.0)
                await self._async_set_heater(False)

        elif self._hvac_mode == HVACMode.COOL:
            await self._async_set_heater(False)
            await self._async_set_cooler(need_cool)

        elif self._hvac_mode == HVACMode.HEAT_COOL:
            if need_heat and not need_cool:
                await self._async_set_cooler(False)
                if self._coordinator.get_master_state():
                    self._coordinator.set_zone_demand(self.entity_id, 100.0)
                else:
                    self._coordinator.set_zone_demand(self.entity_id, 0.0)
                    await self._async_set_heater(False)
            elif need_cool and not need_heat:
                await self._async_set_heater(False)
                await self._async_set_cooler(True)
                self._coordinator.set_zone_demand(self.entity_id, 0.0)
            else:
                await self._async_set_heater(False)
                await self._async_set_cooler(False)
                self._coordinator.set_zone_demand(self.entity_id, 0.0)

    async def _async_pwm_tick(self, now) -> None:
        """Periodic tick to evaluate PWM state for the zone valve (heating only)."""
        if self._hvac_mode != HVACMode.HEAT and self._hvac_mode != HVACMode.HEAT_COOL:
            await self._async_set_heater(False)
            return

        if self._hvac_mode == HVACMode.HEAT_COOL and self._cooler_state:
            await self._async_set_heater(False)
            return

        if not self._coordinator.get_master_state():
            await self._async_set_heater(False)
            return

        demand = self._coordinator.get_zone_demand(self.entity_id)
        if demand is None:
            demand = 0.0
        wanted_state = self._valve_pwm.calculate(demand)
        if wanted_state != self._heater_state:
            await self._async_set_heater(wanted_state)

    async def _async_set_heater(self, state: bool) -> None:
        """Set heater switch to on/off."""
        if state == self._heater_state:
            return
        self._heater_state = state
        if state:
            await self.hass.services.async_call(
                "switch",
                SERVICE_TURN_ON,
                {ATTR_ENTITY_ID: self._heater_switch},
                blocking=False,
            )
        else:
            await self.hass.services.async_call(
                "switch",
                SERVICE_TURN_OFF,
                {ATTR_ENTITY_ID: self._heater_switch},
                blocking=False,
            )
        self.async_write_ha_state()

    async def _async_set_cooler(self, state: bool) -> None:
        """Set cooler switch to on/off."""
        if self._cooler_switch is None:
            return
        if state == self._cooler_state:
            return
        self._cooler_state = state
        if state:
            await self.hass.services.async_call(
                "switch",
                SERVICE_TURN_ON,
                {ATTR_ENTITY_ID: self._cooler_switch},
                blocking=False,
            )
        else:
            await self.hass.services.async_call(
                "switch",
                SERVICE_TURN_OFF,
                {ATTR_ENTITY_ID: self._cooler_switch},
                blocking=False,
            )
        self.async_write_ha_state()
