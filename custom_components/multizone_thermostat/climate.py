"""Climate platform for Multizone Thermostat: Hybrid Master Virtual Thermostats."""
from __future__ import annotations

import asyncio
from datetime import timedelta
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
from homeassistant.core import HomeAssistant, callback, Event, State, Context
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    CONF_ZONES,
    CONF_ZONE_NAME,
    CONF_ZONE_CLIMATES,
    CONF_ZONE_SWITCHES,
    CONF_ZONE_TEMP_SENSOR,
    CONF_ZONE_TARGET_TEMP,
    CONF_ZONE_CALIBRATIONS,
    DOMAIN,
    make_zone_entity_id,
)
from .pwm_engine import PWMEngine

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hybrid Master Virtual Thermostats from a config entry."""
    zones = config_entry.data.get(CONF_ZONES, [])

    if not zones:
        return

    entities = []
    for zone_data in zones:
        entities.append(
            MultizoneVirtualThermostat(
                hass=hass,
                entry_id=config_entry.entry_id,
                zone_data=zone_data,
            )
        )

    async_add_entities(entities)


class MultizoneVirtualThermostat(RestoreEntity, ClimateEntity):
    """A Hybrid Master Virtual Thermostat that controls sub-slave TRVs and Switches."""

    _attr_has_entity_name = False
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
        zone_data: dict[str, Any],
    ) -> None:
        """Initialize the virtual thermostat."""
        self.hass = hass
        self._name = zone_data[CONF_ZONE_NAME]
        self._attr_name = self._name
        self._temp_sensor = zone_data.get(CONF_ZONE_TEMP_SENSOR)
        self._climates = zone_data.get(CONF_ZONE_CLIMATES, [])
        self._switches = zone_data.get(CONF_ZONE_SWITCHES, [])
        self._calibrations = zone_data.get(CONF_ZONE_CALIBRATIONS, {})
        
        # State
        self._hvac_mode = HVACMode.OFF
        self._target_temperature = zone_data.get(CONF_ZONE_TARGET_TEMP, 20.0)
        self._current_temperature: float | None = None
        
        self._coordinator = hass.data[DOMAIN][entry_id]["coordinator"]
        
        # Syncing locks and state tracking
        self._sync_lock = asyncio.Lock()
        self._syncing_trvs = False
        self._last_known_trv_targets = {}
        self._internal_context = Context()
        
        # Local PWM Engine for Switches (e.g. Relays, local valves)
        self._local_pwm = PWMEngine(pwm_interval=900.0, min_on=0.0, min_off=0.0)
        self._local_pwm_state = False
        
        # Entity setup
        vt_entity_id = make_zone_entity_id(self._name)
        safe_name = self._name.lower().replace(" ", "_").replace("-", "_")
        safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_zone_{safe_name}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_zones")},
            name="Heating Zones",
            manufacturer="Multizone Thermostat",
            model="Hybrid Zone Controller",
            via_device=(DOMAIN, entry_id),
        )

        self.entity_id = vt_entity_id
        self._unsub_listeners: list = []

    @property
    def name(self) -> str:
        return f"Zone {self._name}"

    @property
    def hvac_mode(self) -> HVACMode:
        return self._hvac_mode

    @property
    def hvac_action(self) -> HVACAction:
        if self._hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
            
        # Get demand from coordinator
        demand = self._coordinator.get_zone_demand(self.entity_id)
        if demand > 0:
            return HVACAction.HEATING
        return HVACAction.IDLE

    @property
    def current_temperature(self) -> float | None:
        return self._current_temperature

    @property
    def target_temperature(self) -> float | None:
        return self._target_temperature

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "temperature_sensor": self._temp_sensor,
            "climates": self._climates,
            "switches": self._switches,
            "calibrations": self._calibrations,
            "hybrid_zone": True,
            "local_pwm_active": self._local_pwm_state,
            "boiler_entity_id": self._coordinator.boiler_switch,
        }

    def async_write_ha_state(self) -> None:
        """Override to debug rapid calls."""
        import traceback
        _LOGGER.debug("async_write_ha_state called for %s", self.entity_id)
        _LOGGER.debug("Stack trace: %s", "".join(traceback.format_stack()))
        super().async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        self._hvac_mode = hvac_mode
        self.async_write_ha_state()
        await self._async_sync_trvs()
        await self._async_sync_switches()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        self._target_temperature = temperature
        self.async_write_ha_state()
        await self._async_sync_trvs()

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added."""
        await super().async_added_to_hass()
        
        self._coordinator.register_climate(self.entity_id, self.async_write_ha_state)

        last_state = await self.async_get_last_state()
        if last_state is not None:
            if last_state.state in (HVACMode.HEAT, HVACMode.OFF):
                self._hvac_mode = HVACMode(last_state.state)
            if last_state.attributes.get(ATTR_TEMPERATURE) is not None:
                self._target_temperature = float(last_state.attributes[ATTR_TEMPERATURE])
                
        # Read current temperature
        self._update_current_temp()

        if self._temp_sensor:
            self._unsub_listeners.append(
                async_track_state_change_event(
                    self.hass,
                    [self._temp_sensor],
                    self._on_temp_changed,
                )
            )

        if self._climates:
            self._unsub_listeners.append(
                async_track_state_change_event(
                    self.hass,
                    self._climates,
                    self._on_trv_changed_wrapper,
                )
            )
            # Initialize known TRV targets
            for trv in self._climates:
                st = self.hass.states.get(trv)
                if st and st.attributes.get(ATTR_TEMPERATURE) is not None:
                    self._last_known_trv_targets[trv] = float(st.attributes[ATTR_TEMPERATURE])

        # Start periodic local PWM evaluation for switches
        if self._switches:
            self._unsub_listeners.append(
                async_track_time_interval(
                    self.hass,
                    self._async_pwm_tick,
                    timedelta(seconds=10)
                )
            )

        await self._async_sync_trvs()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up listeners."""
        for unsub in self._unsub_listeners:
            unsub()
        self._unsub_listeners.clear()

    @callback
    def _on_temp_changed(self, event: Event) -> None:
        """Handle external temperature sensor changes."""
        new_state: State | None = event.data.get("new_state")
        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return

        try:
            self._current_temperature = float(new_state.state)
            self.async_write_ha_state()
            
            # Since external temp changed, update TRV calibrations or fake targets
            self.hass.async_create_task(self._async_sync_trvs())
        except ValueError:
            _LOGGER.error("Unable to parse temperature: %s", new_state.state)

    def _update_current_temp(self) -> None:
        """Fetch initial temperature."""
        if not self._temp_sensor:
            # Try to average TRV sensors
            temps = []
            for trv in self._climates:
                st = self.hass.states.get(trv)
                if st and st.attributes.get("current_temperature") is not None:
                    temps.append(float(st.attributes["current_temperature"]))
            if temps:
                self._current_temperature = sum(temps) / len(temps)
            return

        state = self.hass.states.get(self._temp_sensor)
        if state and state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            try:
                self._current_temperature = float(state.state)
            except ValueError:
                pass

    @callback
    def _on_trv_changed_wrapper(self, event: Event) -> None:
        """Wrapper for TRV changes."""
        if self._syncing_trvs:
            return
        self.hass.async_create_task(self._async_on_trv_changed(event))

    async def _async_on_trv_changed(self, event: Event) -> None:
        """Handle TRV knob changes."""
        if event.context == self._context or event.context == self._internal_context:
            return
            
        entity_id = event.data.get("entity_id")
        new_state: State | None = event.data.get("new_state")
        old_state: State | None = event.data.get("old_state")
        
        if not new_state or not old_state:
            return
            
        new_temp = new_state.attributes.get(ATTR_TEMPERATURE)
        old_temp = self._last_known_trv_targets.get(entity_id)
        
        if new_temp is not None and old_temp is not None:
            new_temp = float(new_temp)
            old_temp = float(old_temp)
            if abs(new_temp - old_temp) > 0.01:
                delta = new_temp - old_temp
                _LOGGER.info("TRV %s changed target by %s degrees. Applying delta to Zone %s", entity_id, delta, self._name)
                
                # Apply delta to Master target
                if self._target_temperature is not None:
                    self._target_temperature = max(self._attr_min_temp, min(self._attr_max_temp, self._target_temperature + delta))
                    self.async_write_ha_state()
                    
                # Sync all other TRVs now
                await self._async_sync_trvs()

    async def _async_sync_trvs(self) -> None:
        """Sync target temperature and mode to all sub-slave TRVs."""
        if not self._climates:
            return
            
        async with self._sync_lock:
            self._syncing_trvs = True
            try:
                demand = self._coordinator.get_zone_demand(self.entity_id)
            
                # If Master is OFF force TRVs OFF
                target_hvac_mode = HVACMode.HEAT
                if self._hvac_mode == HVACMode.OFF:
                    target_hvac_mode = HVACMode.OFF
                    
                for trv in self._climates:
                    st = self.hass.states.get(trv)
                    if not st:
                        continue
                        
                    # Sync HVAC Mode
                    if st.state != target_hvac_mode:
                        await self.hass.services.async_call(
                            "climate",
                            "set_hvac_mode",
                            {"entity_id": trv, "hvac_mode": target_hvac_mode},
                            context=self._internal_context,
                        )
                    
                    # Sync Target Temp & Calibration
                    if self._target_temperature is not None and target_hvac_mode != HVACMode.OFF:
                        trv_target = self._target_temperature
                        
                        calib_entity = self._calibrations.get(trv)
                        trv_current = st.attributes.get("current_temperature")
                        
                        if self._temp_sensor and self._current_temperature is not None and trv_current is not None:
                            # Scenario B: Ext Sensor + Calibration Entity
                            if calib_entity:
                                calib_state = self.hass.states.get(calib_entity)
                                current_calib_value = float(calib_state.state) if calib_state and calib_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN) else 0.0
                                offset = current_calib_value + (self._current_temperature - float(trv_current))
                                
                                domain = "number"
                                if calib_entity.startswith("input_number."):
                                    domain = "input_number"
                                    
                                await self.hass.services.async_call(
                                    domain,
                                    "set_value",
                                    {"entity_id": calib_entity, "value": offset},
                                    context=self._internal_context,
                                )
                            # Scenario C: Ext Sensor + NO Calibration (Fake Target)
                            else:
                                trv_target = self._target_temperature + (float(trv_current) - self._current_temperature)
                                trv_target = max(5.0, min(35.0, trv_target))
                        
                        # Round target to TRV's native step to prevent rounding-induced feedback loops
                        step = st.attributes.get("target_temp_step", 0.5)
                        if step > 0:
                            trv_target = round(trv_target / step) * step
                        
                        # Send target to TRV
                        if st.attributes.get(ATTR_TEMPERATURE) != trv_target:
                            await self.hass.services.async_call(
                                "climate",
                                "set_temperature",
                                {"entity_id": trv, "temperature": trv_target},
                                context=self._internal_context,
                            )
                        
                        # Save last known target to avoid delta loops
                        self._last_known_trv_targets[trv] = trv_target
            finally:
                self._syncing_trvs = False

    async def _async_pwm_tick(self, now: Any) -> None:
        """Evaluate local PWM for switches."""
        if not self._switches:
            return
            
        if self._hvac_mode == HVACMode.OFF:
            new_pwm_state = False
        else:
            demand = self._coordinator.get_zone_demand(self.entity_id)
            new_pwm_state = self._local_pwm.calculate(demand)
            
        if new_pwm_state != self._local_pwm_state:
            self._local_pwm_state = new_pwm_state
            await self._async_sync_switches()

    async def _async_sync_switches(self) -> None:
        """Turn local switches ON or OFF based on PWM state."""
        if not self._switches:
            return
            
        service = SERVICE_TURN_ON if self._local_pwm_state else SERVICE_TURN_OFF
        
        for switch in self._switches:
            st = self.hass.states.get(switch)
            if st and st.state != (STATE_ON if self._local_pwm_state else "off"):
                await self.hass.services.async_call(
                    "switch",
                    service,
                    {ATTR_ENTITY_ID: switch},
                    context=self._internal_context,
                )
