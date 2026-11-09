"""Climate platform for Multizone Thermostat: Hybrid Master Virtual Thermostats."""
from __future__ import annotations

import inspect

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
    CONF_ZONE_SPLIT_CLIMATE,
    CONF_ZONE_SPLIT_ROLE,
    SPLIT_ROLE_HEAT_COOL,
    SPLIT_ROLE_COOLING_ONLY,
    DEFAULT_SPLIT_ROLE,
    CONF_ZONE_ALLOW_PASSIVE_HEAT,
    CONF_ZONE_SENSOR_TIMEOUT,
    DEFAULT_SENSOR_TIMEOUT_MIN,
    CONF_ZONE_WEIGHT,
    DEFAULT_ZONE_WEIGHT,
    CONF_ZONE_AUTHORITATIVE_SYNC,
    DEFAULT_AUTHORITATIVE_SYNC,
    DOMAIN,
    make_zone_entity_id,
    make_via_device_kwargs,
    make_zone_device_info,
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
    @property
    def can_cool(self) -> bool:
        """Return True if this zone has cooling capabilities."""
        if hasattr(self, "_coordinator") and hasattr(self._coordinator, "can_zone_cool"):
            return bool(self._coordinator.can_zone_cool(self.entity_id))
        return False

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return supported HVAC modes based on zone split configuration and central plant."""
        zone_conf = getattr(self, "_zone_conf", None) or getattr(self, "_zone_data", {})
        if zone_conf:
            split_entity = zone_conf.get(CONF_ZONE_SPLIT_CLIMATE)
            if split_entity and str(split_entity).lower() != "none":
                role = zone_conf.get(CONF_ZONE_SPLIT_ROLE, DEFAULT_SPLIT_ROLE)
                if role == SPLIT_ROLE_COOLING_ONLY:
                    climates = zone_conf.get("climates") or zone_conf.get(CONF_ZONE_CLIMATES) or getattr(self, "_climates", None)
                    switches = zone_conf.get("switches") or zone_conf.get(CONF_ZONE_SWITCHES) or getattr(self, "_switches", None)
                    valves = zone_conf.get("valves") or zone_conf.get(CONF_ZONE_VALVES) or getattr(self, "_valves", None)
                    has_hydronic = bool(climates or switches or valves)
                    central_heat_enabled = (
                        bool(getattr(self._coordinator, "enable_gas_heater", True))
                        or bool(getattr(self._coordinator, "enable_heat_pump", False))
                    )
                    if not has_hydronic and not central_heat_enabled:
                        return [HVACMode.COOL, HVACMode.OFF]
                elif role == SPLIT_ROLE_HEAT_COOL:
                    return [HVACMode.HEAT, HVACMode.COOL, HVACMode.OFF]
        if self.can_cool:
            return [HVACMode.HEAT, HVACMode.COOL, HVACMode.OFF]
        return [HVACMode.HEAT, HVACMode.OFF]
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
        self._zone_data = zone_data
        self._zone_conf = zone_data
        self._name = zone_data[CONF_ZONE_NAME]
        self._attr_name = self._name
        self._temp_sensor = zone_data.get(CONF_ZONE_TEMP_SENSOR)
        self._climates = zone_data.get(CONF_ZONE_CLIMATES, [])
        self._switches = zone_data.get(CONF_ZONE_SWITCHES, [])
        self._valves = zone_data.get(CONF_ZONE_VALVES, [])
        self._valve_scale = zone_data.get(CONF_VALVE_SCALE, DEFAULT_VALVE_SCALE)
        self._calibrations = zone_data.get(CONF_ZONE_CALIBRATIONS, {})
        self._sensor_timeout_min = zone_data.get(CONF_ZONE_SENSOR_TIMEOUT, DEFAULT_SENSOR_TIMEOUT_MIN)
        self._authoritative_sync: bool = bool(
            zone_data.get(CONF_ZONE_AUTHORITATIVE_SYNC, DEFAULT_AUTHORITATIVE_SYNC)
        )
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
        self._attr_device_info = make_zone_device_info(entry_id, self._name, master_dev_id)

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
            authoritative_sync=self._authoritative_sync,
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
            
        if self._hvac_mode == HVACMode.COOL:
            master_on = self._coordinator.get_master_state() if hasattr(self._coordinator, "get_master_state") else True
            if not master_on or not self.can_cool:
                return HVACAction.IDLE
            split_mgr = getattr(self._coordinator, "split_manager", None)
            if split_mgr and (split_mgr.is_split_active(self.entity_id) or split_mgr.is_local_manual_on(self.entity_id)):
                return HVACAction.COOLING
            if self._current_temperature is not None and self.target_temperature is not None:
                if self._current_temperature > self.target_temperature + 0.2:
                    return HVACAction.COOLING
            return HVACAction.IDLE

        # Heating mode
        split_mgr = getattr(self._coordinator, "split_manager", None)
        split_is_active = (
            (split_mgr.is_split_active(self.entity_id) or split_mgr.is_local_manual_on(self.entity_id))
            if (split_mgr and hasattr(split_mgr, "is_split_active"))
            else False
        )
        if split_is_active:
            return HVACAction.HEATING

        master_on = self._coordinator.get_master_state() if hasattr(self._coordinator, "get_master_state") else True
        if master_on:
            demand = self._coordinator.get_zone_demand(self.entity_id)
            if demand > 0:
                return HVACAction.HEATING

        return HVACAction.IDLE

    @property
    def current_temperature(self) -> float | None:
        return self._current_temperature

    @property
    def target_temperature(self) -> float | None:
        if hasattr(self._coordinator, "calendar_manager"):
            override_temp = self._coordinator.calendar_manager.temp_overrides.get(self.entity_id)
            if override_temp is not None and isinstance(override_temp, (int, float)):
                return float(override_temp)
        sched_manager = getattr(self._coordinator, "schedule_manager", None)
        if sched_manager:
            is_enabled = getattr(sched_manager, "scheduler_enabled", False) is True
            has_smart_return = isinstance(getattr(sched_manager, "smart_return", None), dict)
            if is_enabled or has_smart_return:
                sched_temp = sched_manager.get_effective_target(self.entity_id)
                if sched_temp is not None and isinstance(sched_temp, (int, float)):
                    return float(sched_temp)
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
            "zone_weight": self._coordinator.demand_aggregator.get_zone_weight(self.entity_id),
            "authoritative_climate_sync": self._authoritative_sync,
            "allow_passive_heat": self._coordinator.zone_manager.is_passive_heat_allowed(self.entity_id),
            "safety_fallback_active": self._safety_fallback_active,
            "sensor_timeout_min": self._sensor_timeout_min,
            "can_cool": self.can_cool,
            "master_hvac_mode": getattr(self._coordinator, "master_hvac_mode", "heat"),
        }
        if hasattr(self._coordinator, "plant_diagnostics"):
            bat = self._coordinator.plant_diagnostics.get_zone_battery_level(self.entity_id)
            if bat is not None:
                attrs["battery_level"] = bat
        sched_manager = getattr(self._coordinator, "schedule_manager", None)
        if sched_manager and hasattr(sched_manager, "manual_overrides") and isinstance(getattr(sched_manager, "manual_overrides", None), dict):
            manual_ovs = sched_manager.manual_overrides
            attrs["schedule_manual_override"] = self.entity_id in manual_ovs
            attrs["schedule_override_until"] = manual_ovs.get(self.entity_id, {}).get("until")
            smart_info = getattr(sched_manager, "smart_start_info", None)
            if isinstance(smart_info, dict):
                attrs["smart_start_active"] = self.entity_id in smart_info
                attrs["smart_start_detail"] = smart_info.get(self.entity_id)
            if hasattr(sched_manager, "_get_zone_heating_rate"):
                hr = sched_manager._get_zone_heating_rate(self.entity_id)
                if isinstance(hr, (int, float)):
                    attrs["heating_rate"] = hr

        if hasattr(self._coordinator, "get_zone_cooling_rate"):
            attrs["cooling_rate"] = self._coordinator.get_zone_cooling_rate(self.entity_id)
        elif sched_manager and hasattr(sched_manager, "_get_zone_cooling_rate"):
            cr = sched_manager._get_zone_cooling_rate(self.entity_id)
            if isinstance(cr, (int, float)):
                attrs["cooling_rate"] = cr

        split_is_heating = False
        hydronic_suppressed = False
        if hasattr(self._coordinator, "split_manager") and self._coordinator.split_manager.has_split(self.entity_id):
            split_info = self._coordinator.split_manager.get_split_info(self.entity_id) or {}
            attrs["split_climate_entity"] = split_info.get("split_entity_id")
            split_is_active = bool(self._coordinator.split_manager.is_split_active(self.entity_id))
            attrs["split_active"] = split_is_active
            attrs["split_manual_on"] = bool(self._coordinator.split_manager.is_local_manual_on(self.entity_id))
            split_is_heating = (self._hvac_mode == HVACMode.HEAT and split_is_active)
            split_is_cooling = (self._hvac_mode == HVACMode.COOL and split_is_active)
            attrs["split_cooling"] = split_is_cooling
            attrs["split_quick_boost_active"] = bool(self._coordinator.split_manager.is_quick_boost_active(self.entity_id))
            hydronic_suppressed = bool(self._coordinator.split_manager.should_suppress_hydronic_demand(self.entity_id))
            attrs["split_hydronic_suppressed"] = hydronic_suppressed

        # Determine real-time active heating source: gas, electric, dual, or none
        master_on = bool(self._coordinator.get_master_state()) if hasattr(self._coordinator, "get_master_state") else True
        split_mgr = getattr(self._coordinator, "split_manager", None)
        is_local_manual = bool(split_mgr.is_local_manual_on(self.entity_id)) if split_mgr else False

        is_heating = (self._hvac_mode == HVACMode.HEAT) and (self.hvac_action == HVACAction.HEATING or split_is_heating or is_local_manual)
        if not is_heating:
            attrs["active_heating_source"] = "none"
        else:
            gas_enabled = getattr(self._coordinator, "enable_gas_heater", True)
            hp_enabled = getattr(self._coordinator, "enable_heat_pump", False)
            hydronic_is_heating = master_on and (self.hvac_action == HVACAction.HEATING and not hydronic_suppressed)
            central_is_electric = hp_enabled and not gas_enabled

            if split_is_heating and hydronic_is_heating:
                attrs["active_heating_source"] = "electric" if central_is_electric else "dual"
            elif split_is_heating or is_local_manual:
                attrs["active_heating_source"] = "electric"
            elif hydronic_is_heating:
                attrs["active_heating_source"] = "electric" if central_is_electric else "gas"
            else:
                attrs["active_heating_source"] = "electric" if is_local_manual else "none"

        return attrs

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        self._hvac_mode = hvac_mode
        master_on = self._coordinator.get_master_state() if hasattr(self._coordinator, "get_master_state") else True
        split_mgr = getattr(self._coordinator, "split_manager", None)

        if hvac_mode == HVACMode.OFF:
            self._sync_manager._local_pwm_state = False
            self._coordinator.set_zone_demand(self.entity_id, 0.0)
            if split_mgr and hasattr(split_mgr, "set_local_manual_on"):
                split_mgr.set_local_manual_on(self.entity_id, False)
        else:
            if not master_on and split_mgr and hasattr(split_mgr, "has_split") and split_mgr.has_split(self.entity_id):
                split_mgr.set_local_manual_on(self.entity_id, True)

        self.async_write_ha_state()
        await self._trigger_trv_sync()
        await self._sync_manager.async_sync_switches()
        await self._sync_manager.async_sync_proportional_valves(self._hvac_mode)
        if hasattr(self._coordinator, "zone_controller") and self._coordinator.zone_controller:
            st = self.hass.states.get(self.entity_id) if hasattr(self, "hass") and self.hass and hasattr(self.hass, "states") else None
            if st is not None:
                coro = self._coordinator.zone_controller.async_update_zone(self.entity_id, st)
                if inspect.iscoroutine(coro):
                    await coro

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

        sched_manager = getattr(self._coordinator, "schedule_manager", None)
        sched_enabled = bool(sched_manager and getattr(sched_manager, "scheduler_enabled", False) is True)
        if sched_enabled:
            sched_manager.record_manual_override(self.entity_id, temperature)
            if hasattr(self.hass, "async_create_task"):
                self.hass.async_create_task(sched_manager.async_save_to_storage())

        current_preset = self._coordinator.get_global_preset()
        if current_preset and current_preset != "none":
            mode_val = str(self._hvac_mode.value if hasattr(self._hvac_mode, "value") else self._hvac_mode)
            if mode_val == "cool":
                self._coordinator.zone_manager.update_preset_temperature(
                    current_preset, self.entity_id, temperature, hvac_mode="cool"
                )
            else:
                self._coordinator.zone_manager.update_preset_temperature(
                    current_preset, self.entity_id, temperature
                )

        self.async_write_ha_state()
        await self._trigger_trv_sync()
        if hasattr(self._coordinator, "zone_controller") and self._coordinator.zone_controller:
            st = self.hass.states.get(self.entity_id) if hasattr(self, "hass") and self.hass and hasattr(self.hass, "states") else None
            if st is not None:
                coro = self._coordinator.zone_controller.async_update_zone(self.entity_id, st)
                if inspect.iscoroutine(coro):
                    await coro

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
            if self._safety_fallback_active:
                _LOGGER.info("Zone %s: External temp sensor recovered. Exiting safety fallback.", self._name)
                self._safety_fallback_active = False
            self.async_write_ha_state()
            self.hass.async_create_task(self._trigger_trv_sync())
        except ValueError:
            _LOGGER.error("Unable to parse temperature: %s", new_state.state)

    def check_sensor_staleness(self) -> bool:
        """Re-evaluate current temperature for sensor timeout or recovery."""
        if not self._temp_sensor:
            return False
        prev_temp = self._current_temperature
        prev_fallback = self._safety_fallback_active
        self._update_current_temp()
        if self._current_temperature != prev_temp or self._safety_fallback_active != prev_fallback:
            self.async_write_ha_state()
            return True
        return False

    def _update_current_temp(self) -> None:
        """Fetch current temperature, falling back to internal TRV readings if sensor is offline/timed out."""
        ext_temp_valid = False
        if self._temp_sensor:
            state = self.hass.states.get(self._temp_sensor)
            if state and state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                try:
                    now = time.time()
                    reported = state.last_reported if hasattr(state, "last_reported") else getattr(state, "last_updated", None)
                    ts = reported.timestamp() if (reported and hasattr(reported, "timestamp")) else None
                    elapsed = (now - ts) if isinstance(ts, (int, float)) else 0.0
                    
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
            else:
                self._current_temperature = None

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
        ctx = getattr(self, "_context", None)
        ctx_id = ctx.id if ctx else None
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
            if new_mode == HVACMode.OFF:
                self._sync_manager._local_pwm_state = False
                self._coordinator.set_zone_demand(self.entity_id, 0.0)
                await self._sync_manager.async_sync_switches()
                await self._sync_manager.async_sync_proportional_valves(self._hvac_mode)
            needs_sync = True
            
        if delta_temp is not None and self._target_temperature is not None and self._hvac_mode != HVACMode.OFF:
            sched_manager = getattr(self._coordinator, "schedule_manager", None)
            sched_enabled = bool(sched_manager and getattr(sched_manager, "scheduler_enabled", False) is True)
            if sched_enabled:
                base_temp = self.target_temperature if self.target_temperature is not None else self._target_temperature
                new_temp = max(self._attr_min_temp, min(self._attr_max_temp, base_temp + delta_temp))
                self._target_temperature = new_temp
                if (
                    hasattr(self._coordinator, "calendar_manager")
                    and self.entity_id in self._coordinator.calendar_manager.temp_overrides
                ):
                    self._coordinator.calendar_manager.temp_overrides[self.entity_id] = self._target_temperature
                sched_manager.record_manual_override(self.entity_id, new_temp)
                if hasattr(self.hass, "async_create_task"):
                    self.hass.async_create_task(sched_manager.async_save_to_storage())
            else:
                self._target_temperature = max(self._attr_min_temp, min(self._attr_max_temp, self._target_temperature + delta_temp))
                if (
                    hasattr(self._coordinator, "calendar_manager")
                    and self.entity_id in self._coordinator.calendar_manager.temp_overrides
                ):
                    self._coordinator.calendar_manager.temp_overrides[self.entity_id] = self._target_temperature
            current_preset = self._coordinator.get_global_preset()
            if current_preset and current_preset != "none":
                mode_val = str(self._hvac_mode.value if hasattr(self._hvac_mode, "value") else self._hvac_mode)
                if mode_val == "cool":
                    self._coordinator.zone_manager.update_preset_temperature(
                        current_preset, self.entity_id, self._target_temperature, hvac_mode="cool"
                    )
                else:
                    self._coordinator.zone_manager.update_preset_temperature(
                        current_preset, self.entity_id, self._target_temperature
                    )
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

