"""Climate platform for Multizone Thermostat: Hybrid Master Virtual Thermostats."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
import time
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback, Event, State
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
    CONF_ZONE_VALVES,
    CONF_VALVE_SCALE,
    DEFAULT_VALVE_SCALE,
    CONF_ZONE_TEMP_SENSOR,
    CONF_ZONE_TARGET_TEMP,
    CONF_ZONE_CALIBRATIONS,
    CONF_ZONE_ALLOW_PASSIVE_HEAT,
    CONF_ZONE_SENSOR_TIMEOUT,
    DEFAULT_SENSOR_TIMEOUT_MIN,
    DOMAIN,
    make_zone_entity_id,
    make_via_device_kwargs,
)
from .sync_manager import ZoneSyncManager
from .state_restorer import ZoneStateRestorer

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hybrid Master Virtual Thermostats from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    zones = coordinator.zones

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
        self._valves = zone_data.get(CONF_ZONE_VALVES, [])
        self._valve_scale = zone_data.get(CONF_VALVE_SCALE, DEFAULT_VALVE_SCALE)
        self._calibrations = zone_data.get(CONF_ZONE_CALIBRATIONS, {})
        self._sensor_timeout_min = zone_data.get(CONF_ZONE_SENSOR_TIMEOUT, DEFAULT_SENSOR_TIMEOUT_MIN)
        self._safety_fallback_active = False
        
        self._hvac_mode = HVACMode.OFF
        self._target_temperature = zone_data.get(CONF_ZONE_TARGET_TEMP, 20.0)
        self._current_temperature: float | None = None
        
        self._coordinator = hass.data[DOMAIN][entry_id]["coordinator"]
        self._entry_id = entry_id
        
        vt_entity_id = make_zone_entity_id(self._name)
        safe_name = self._name.lower().replace(" ", "_").replace("-", "_")
        safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_zone_{safe_name}"
        
        master_dev_id = getattr(self._coordinator, "master_device_id", None)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_zones")},
            name="Heating Zones",
            manufacturer="Multizone Thermostat",
            model="Hybrid Zone Controller",
            **make_via_device_kwargs(entry_id, master_dev_id),
        )

        self.entity_id = vt_entity_id
        self._unsub_listeners: list = []

        self._sync_manager = ZoneSyncManager(
            hass=self.hass,
            coordinator=self._coordinator,
            zone_name=self._name,
            entity_id=self.entity_id,
            climates=self._climates,
            switches=self._switches,
            calibrations=self._calibrations,
            valves=self._valves,
            valve_scale=self._valve_scale,
        )

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
            
        demand = self._coordinator.get_zone_demand(self.entity_id)
        if demand > 0:
            return HVACAction.HEATING
        return HVACAction.IDLE

    @property
    def current_temperature(self) -> float | None:
        return self._current_temperature

    @property
    def target_temperature(self) -> float | None:
        override_temp = self._coordinator.calendar_manager.temp_overrides.get(self.entity_id)
        if override_temp is not None:
            return override_temp
        return self._target_temperature

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = {
            "temperature_sensor": self._temp_sensor,
            "climates": self._climates,
            "switches": self._switches,
            "valves": self._valves,
            "valve_scale": self._valve_scale,
            "calibrations": self._calibrations,
            "hybrid_zone": True,
            "local_pwm_active": self._sync_manager.local_pwm_state,
            "boiler_entity_id": self._coordinator.boiler_switch,
            "zone_mode": self._coordinator.get_zone_mode(self.entity_id),
            "allow_passive_heat": self._coordinator.zone_manager.is_passive_heat_allowed(self.entity_id),
            "safety_fallback_active": self._safety_fallback_active,
            "sensor_timeout_min": self._sensor_timeout_min,
        }
        if hasattr(self._coordinator, "plant_diagnostics"):
            bat = self._coordinator.plant_diagnostics.get_zone_battery_level(self.entity_id)
            if bat is not None:
                attrs["battery_level"] = bat
        return attrs

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        self._hvac_mode = hvac_mode
        if hvac_mode == HVACMode.OFF:
            self._sync_manager._local_pwm_state = False
            self._coordinator.set_zone_demand(self.entity_id, 0.0)
        self.async_write_ha_state()
        await self._trigger_trv_sync()
        await self._sync_manager.async_sync_switches()
        await self._sync_manager.async_sync_proportional_valves(self._hvac_mode)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        self._target_temperature = temperature
        if (
            hasattr(self._coordinator, "calendar_manager")
            and self.entity_id in self._coordinator.calendar_manager.temp_overrides
        ):
            self._coordinator.calendar_manager.temp_overrides[self.entity_id] = temperature
        self.async_write_ha_state()
        await self._trigger_trv_sync()
        
        current_preset = self._coordinator.get_global_preset()
        if current_preset and current_preset != "none":
            self._coordinator.zone_manager.update_preset_temperature(current_preset, self.entity_id, temperature)

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added."""
        await super().async_added_to_hass()
        
        self._coordinator.register_climate(self.entity_id, self.async_write_ha_state, self)

        self._hvac_mode, self._target_temperature = await ZoneStateRestorer.async_restore_state(
            self, self._hvac_mode, self._target_temperature
        )
                
        self._update_current_temp()

        if self._temp_sensor:
            self._unsub_listeners.append(
                async_track_state_change_event(
                    self.hass, [self._temp_sensor], self._on_temp_changed
                )
            )

        if self._climates:
            self._unsub_listeners.append(
                async_track_state_change_event(
                    self.hass, self._climates, self._on_trv_changed_wrapper
                )
            )
            self._sync_manager.init_known_targets()

        if self._switches:
            self._unsub_listeners.append(
                async_track_time_interval(
                    self.hass, self._async_pwm_tick, timedelta(seconds=10)
                )
            )

        if self._valves:
            self._unsub_listeners.append(
                async_track_time_interval(
                    self.hass, self._async_valve_tick, timedelta(seconds=10)
                )
            )

        await self._trigger_trv_sync()
        if self._valves:
            await self._sync_manager.async_sync_proportional_valves(self._hvac_mode)

    async def async_will_remove_from_hass(self) -> None:
        """Clean up listeners."""
        for unsub in self._unsub_listeners:
            unsub()
        self._unsub_listeners.clear()
        self._coordinator.unregister_climate(self.entity_id)

    def get_trv_health(self) -> dict[str, Any]:
        """Return sanitized TRV health, communication status and latency statistics."""
        return self._sync_manager.get_trv_health()

    @callback
    def _on_temp_changed(self, event: Event) -> None:
        """Handle external temperature sensor changes."""
        new_state: State | None = event.data.get("new_state")
        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            # Sensore non valido: valuta subito il fallback sui TRV senza
            # attendere il prossimo aggiornamento periodico.
            self._update_current_temp()
            self.async_write_ha_state()
            return

        try:
            self._current_temperature = float(new_state.state)
            self.async_write_ha_state()
            self.hass.async_create_task(self._trigger_trv_sync())
        except ValueError:
            _LOGGER.error("Unable to parse temperature: %s", new_state.state)

    def _update_current_temp(self) -> None:
        """Fetch current temperature, falling back to internal TRV readings if sensor is offline/timed out."""
        ext_temp_valid = False
        if self._temp_sensor:
            state = self.hass.states.get(self._temp_sensor)
            if state and state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                try:
                    now = time.time()
                    reported = state.last_reported if hasattr(state, "last_reported") else state.last_updated
                    elapsed = (now - reported.timestamp()) if reported else 0
                    
                    if self._sensor_timeout_min == 0 or elapsed <= (self._sensor_timeout_min * 60):
                        self._current_temperature = float(state.state)
                        ext_temp_valid = True
                        if self._safety_fallback_active:
                            _LOGGER.info("Zone %s: External temp sensor recovered. Exiting safety fallback.", self._name)
                            self._safety_fallback_active = False
                    else:
                        _LOGGER.warning("Zone %s: Sensor timeout reached (%d min). Falling back to TRVs.", self._name, int(elapsed / 60))
                except (ValueError, TypeError):
                    pass

        if not ext_temp_valid:
            temps = []
            for trv in self._climates:
                st = self.hass.states.get(trv)
                if st and st.attributes.get("current_temperature") is not None:
                    try:
                        temps.append(float(st.attributes["current_temperature"]))
                    except (ValueError, TypeError):
                        pass
            if temps:
                self._current_temperature = sum(temps) / len(temps)
                if self._temp_sensor and not self._safety_fallback_active:
                    self._safety_fallback_active = True
                    _LOGGER.warning("Zone %s: Safety fallback active, using onboard TRV average: %.1f°C", self._name, self._current_temperature)
            elif self._temp_sensor:
                st = self.hass.states.get(self._temp_sensor)
                if st and st.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                    try:
                        self._current_temperature = float(st.state)
                    except (ValueError, TypeError):
                        pass

    @callback
    def _on_trv_changed_wrapper(self, event: Event) -> None:
        """Wrapper for TRV changes."""
        if not self._temp_sensor or self._safety_fallback_active:
            new_state: State | None = event.data.get("new_state")
            old_state: State | None = event.data.get("old_state")
            if new_state:
                new_current = new_state.attributes.get("current_temperature")
                old_current = old_state.attributes.get("current_temperature") if old_state else None
                if new_current is not None and new_current != old_current:
                    self._update_current_temp()
                    self.async_write_ha_state()

        self.hass.async_create_task(self._async_on_trv_changed(event))

    async def _async_on_trv_changed(self, event: Event) -> None:
        """Handle TRV knob changes delegating to SyncManager."""
        ctx_id = self._context.id if self._context else None
        new_mode, delta_temp = await self._sync_manager.process_trv_change(
            event=event,
            master_context_id=ctx_id,
            master_hvac_mode=self._hvac_mode,
            master_min_temp=self._attr_min_temp,
            master_max_temp=self._attr_max_temp
        )

        needs_sync = False
        if new_mode is not None:
            self._hvac_mode = new_mode
            needs_sync = True
            
        if delta_temp is not None and self._target_temperature is not None:
            self._target_temperature = max(self._attr_min_temp, min(self._attr_max_temp, self._target_temperature + delta_temp))
            needs_sync = True
            
        if needs_sync:
            self.async_write_ha_state()
            await self._trigger_trv_sync()

    async def _trigger_trv_sync(self) -> None:
        """Helper to invoke SyncManager's TRV sync."""
        await self._sync_manager.async_sync_trvs(
            master_hvac_mode=self._hvac_mode,
            master_target_temp=self.target_temperature,
            master_current_temp=self._current_temperature,
            safety_fallback_active=self._safety_fallback_active,
            has_external_sensor=bool(self._temp_sensor)
        )

    async def _async_pwm_tick(self, now: Any) -> None:
        """Evaluate local PWM for switches."""
        if await self._sync_manager.async_pwm_tick(self._hvac_mode):
            self.async_write_ha_state()

    async def _async_valve_tick(self, now: Any) -> None:
        """Evaluate and synchronize proportional valves."""
        await self._sync_manager.async_sync_proportional_valves(self._hvac_mode)

