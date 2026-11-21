"""Climate platform for Multizone Thermostat: Hybrid Master Virtual Thermostats."""
from __future__ import annotations

from collections.abc import Mapping
import inspect

import asyncio
from datetime import timedelta
import logging
import math
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
    CONF_ZONE_TRV_CALIBRATION_MODE,
    CONF_ZONE_TRV_SENSOR_SELECTS,
    DEFAULT_TRV_CALIB_MODE,
    CONF_ZONE_TRV_CONTROL_MODE,
    DEFAULT_TRV_CONTROL_MODE,
    CONF_ZONE_TRV_OPEN_BOOST,
    DEFAULT_TRV_OPEN_BOOST,
    CONF_ZONE_TRV_CLOSE_OFFSET,
    DEFAULT_TRV_CLOSE_OFFSET,
    TRV_CONTROL_MODE_DEMAND_DRIVEN,
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
    CONF_ZONE_EMITTER_TYPE,
    DEFAULT_ZONE_EMITTER_TYPE,
    DEFAULT_AUTHORITATIVE_SYNC,
    DOMAIN,
    make_zone_entity_id,
    make_via_device_kwargs,
    make_zone_device_info,
    get_state_temp_unit,
    to_celsius,
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


def _collect_tuner_attrs(tuner: Any) -> dict[str, Any]:
    """Extract autotuner/PID diagnostic attributes safely from a tuner instance."""
    out: dict[str, Any] = {}
    if tuner is None:
        return out
    try:
        kp = tuner.kp
    except AttributeError:
        return out
    if not isinstance(kp, (int, float)):
        return out

    out["pid_kp"] = round(float(kp), 2)
    out["pid_ki"] = round(float(tuner.ki), 4)
    out["pid_kd"] = round(float(tuner.kd), 2)
    try:
        l_kp, l_ki, l_kd = tuner._learned_kp, tuner._learned_ki, tuner._learned_kd
    except AttributeError:
        l_kp, l_ki, l_kd = kp, tuner.ki, tuner.kd
    if isinstance(l_kp, (int, float)):
        out["learned_kp"] = round(float(l_kp), 2)
        out["learned_ki"] = round(float(l_ki), 4)
        out["learned_kd"] = round(float(l_kd), 2)
    try:
        if isinstance(tuner.state, str):
            out["autotune_state"] = tuner.state
        if isinstance(tuner.completed_cycles, list):
            out["autotune_cycles"] = len(tuner.completed_cycles)
        if isinstance(tuner.required_cycles, int):
            out["autotune_required_cycles"] = tuner.required_cycles
        if isinstance(tuner.manual_overrides, dict):
            out["pid_manual_overrides"] = sorted(tuner.manual_overrides.keys())
        if isinstance(tuner.weekly_candidates, list):
            out["weekly_candidates_count"] = len(tuner.weekly_candidates)
    except AttributeError:
        pass
    try:
        out["autotune_can_restore"] = bool(tuner.can_restore_pre_reset)
    except AttributeError:
        out["autotune_can_restore"] = False
    try:
        snap = tuner._pre_reset_snapshot
    except AttributeError:
        snap = None
    if isinstance(snap, dict):
        learned = snap.get("learned_pid") or {}
        if learned.get("Kp"):
            out["autotune_backup_pid"] = {
                "Kp": round(float(learned.get("Kp", 0.0)), 1),
                "Ki": round(float(learned.get("Ki", 0.0)), 4),
                "Kd": round(float(learned.get("Kd", 0.0)), 1),
            }
    return out


class MultizoneVirtualThermostat(RestoreEntity, ClimateEntity):
    """A Hybrid Master Virtual Thermostat that controls sub-slave TRVs and Switches."""

    _attr_has_entity_name = False
    @property
    def _zone_id(self) -> str:
        """Canonical zone identifier used for internal coordinator managers."""
        return self._canonical_id or self.entity_id

    @property
    def can_cool(self) -> bool:
        """Return True if this zone has cooling capabilities."""
        try:
            return bool(self._coordinator.can_zone_cool(self._zone_id))
        except AttributeError:
            return False

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return supported HVAC modes based on zone split configuration and central plant."""
        zone_conf = self._zone_conf or self._zone_data
        if zone_conf:
            split_entity = zone_conf.get(CONF_ZONE_SPLIT_CLIMATE)
            if split_entity and str(split_entity).lower() != "none":
                role = zone_conf.get(CONF_ZONE_SPLIT_ROLE, DEFAULT_SPLIT_ROLE)
                if role == SPLIT_ROLE_COOLING_ONLY:
                    climates = zone_conf.get("climates") or zone_conf.get(CONF_ZONE_CLIMATES) or self._climates
                    switches = zone_conf.get("switches") or zone_conf.get(CONF_ZONE_SWITCHES) or self._switches
                    valves = zone_conf.get("valves") or zone_conf.get(CONF_ZONE_VALVES) or self._valves
                    has_hydronic = bool(climates or switches or valves)
                    if not has_hydronic:
                        return [HVACMode.COOL, HVACMode.OFF]
                elif role == SPLIT_ROLE_HEAT_COOL:
                    return [HVACMode.HEAT, HVACMode.COOL, HVACMode.OFF]
        if self.can_cool:
            return [HVACMode.HEAT, HVACMode.COOL, HVACMode.OFF]
        return [HVACMode.HEAT, HVACMode.OFF]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
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
        self._trv_calibration_mode: str = zone_data.get(
            CONF_ZONE_TRV_CALIBRATION_MODE, DEFAULT_TRV_CALIB_MODE
        )
        self._trv_sensor_selects: dict[str, str] = (
            zone_data.get(CONF_ZONE_TRV_SENSOR_SELECTS, {}) or {}
        )
        self._trv_control_mode: str = zone_data.get(
            CONF_ZONE_TRV_CONTROL_MODE, DEFAULT_TRV_CONTROL_MODE
        )
        try:
            self._trv_open_boost: float = float(
                zone_data.get(CONF_ZONE_TRV_OPEN_BOOST, DEFAULT_TRV_OPEN_BOOST)
            )
        except (ValueError, TypeError):
            self._trv_open_boost = DEFAULT_TRV_OPEN_BOOST
        try:
            self._trv_close_offset: float = float(
                zone_data.get(CONF_ZONE_TRV_CLOSE_OFFSET, DEFAULT_TRV_CLOSE_OFFSET)
            )
        except (ValueError, TypeError):
            self._trv_close_offset = DEFAULT_TRV_CLOSE_OFFSET
        self._sensor_timeout_min = zone_data.get(CONF_ZONE_SENSOR_TIMEOUT, DEFAULT_SENSOR_TIMEOUT_MIN)
        self._authoritative_sync: bool = bool(
            zone_data.get(CONF_ZONE_AUTHORITATIVE_SYNC, DEFAULT_AUTHORITATIVE_SYNC)
        )
        self._emitter_type: str = zone_data.get(CONF_ZONE_EMITTER_TYPE, DEFAULT_ZONE_EMITTER_TYPE)
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

        self._canonical_id = vt_entity_id
        self.entity_id = vt_entity_id
        self._unsub_listeners: list = []

        self._sync_manager = ZoneSyncManager(
            hass=self.hass,
            coordinator=self._coordinator,
            zone_name=self._name,
            entity_id=self._zone_id,
            climates=self._climates,
            switches=self._switches,
            calibrations=self._calibrations,
            valves=self._valves,
            valve_scale=self._valve_scale,
            authoritative_sync=self._authoritative_sync,
            emitter_type=self._emitter_type,
            calibration_mode=self._trv_calibration_mode,
            trv_sensor_selects=self._trv_sensor_selects,
            trv_control_mode=self._trv_control_mode,
            trv_open_boost=self._trv_open_boost,
            trv_close_offset=self._trv_close_offset,
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

        coord = self._coordinator
        split_mgr = getattr(coord, "split_manager", None)
        try:
            master_on = coord.get_master_state()
        except AttributeError:
            master_on = True

        if self._hvac_mode == HVACMode.COOL:
            if not master_on or not self.can_cool:
                return HVACAction.IDLE
            if split_mgr and (split_mgr.is_split_active(self._zone_id) or split_mgr.is_local_manual_on(self._zone_id)):
                return HVACAction.COOLING
            if coord.get_zone_demand(self._zone_id) > 0:
                return HVACAction.COOLING
            return HVACAction.IDLE

        # Heating mode
        if split_mgr is not None:
            try:
                if split_mgr.is_split_active(self._zone_id) or split_mgr.is_local_manual_on(self._zone_id):
                    return HVACAction.HEATING
            except AttributeError:
                pass

        if master_on and coord.get_zone_demand(self._zone_id) > 0:
            return HVACAction.HEATING

        return HVACAction.IDLE

    @property
    def current_temperature(self) -> float | None:
        return self._current_temperature

    @property
    def target_temperature(self) -> float | None:
        coord = self._coordinator
        cal_mgr = getattr(coord, "calendar_manager", None)
        if cal_mgr is not None:
            override_temp = cal_mgr.temp_overrides.get(self._zone_id)
            if override_temp is not None and isinstance(override_temp, (int, float)):
                return float(override_temp)
        sched_manager = getattr(coord, "schedule_manager", None)
        if sched_manager is not None:
            is_enabled = getattr(sched_manager, "scheduler_enabled", False) is True
            has_smart_return = isinstance(getattr(sched_manager, "smart_return", None), dict)
            if is_enabled or has_smart_return:
                sched_temp = sched_manager.get_effective_target(self._zone_id)
                if sched_temp is not None and isinstance(sched_temp, (int, float)):
                    return float(sched_temp)
        return self._target_temperature

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        coord = self._coordinator
        zone_id = self._zone_id
        attrs = {
            "temperature_sensor": self._temp_sensor,
            "climates": self._climates,
            "switches": self._switches,
            "valves": self._valves,
            "valve_scale": self._valve_scale,
            "calibrations": self._calibrations,
            "trv_calibration_mode": self._trv_calibration_mode,
            "trv_sensor_selects": self._trv_sensor_selects,
            "trv_control_mode": self._trv_control_mode,
            "trv_open_boost": self._trv_open_boost,
            "trv_close_offset": self._trv_close_offset,
            "trv_demand_valve_open": getattr(self._sync_manager, "demand_valve_open", None),
            "hybrid_zone": True,
            "local_pwm_active": self._sync_manager.local_pwm_state,
            "boiler_entity_id": coord.boiler_switch,
            "zone_mode": coord.get_zone_mode(zone_id),
            "zone_weight": coord.demand_aggregator.get_zone_weight(zone_id),
            "authoritative_climate_sync": self._authoritative_sync,
            "allow_passive_heat": coord.zone_manager.is_passive_heat_allowed(zone_id),
            "safety_fallback_active": self._safety_fallback_active,
            "sensor_timeout_min": self._sensor_timeout_min,
            "can_cool": self.can_cool,
            "emitter_type": self._emitter_type,
            "master_hvac_mode": getattr(coord, "master_hvac_mode", "heat"),
        }
        diag = getattr(coord, "plant_diagnostics", None)
        if diag is not None:
            bat = diag.get_zone_battery_level(zone_id)
            if bat is not None:
                attrs["battery_level"] = bat
        sched_manager = getattr(coord, "schedule_manager", None)
        if sched_manager is not None:
            manual_ovs = getattr(sched_manager, "manual_overrides", None)
            if isinstance(manual_ovs, dict):
                attrs["schedule_manual_override"] = zone_id in manual_ovs
                attrs["schedule_override_until"] = (manual_ovs.get(zone_id) or {}).get("until")
                smart_info = getattr(sched_manager, "smart_start_info", None)
                if isinstance(smart_info, dict):
                    attrs["smart_start_active"] = zone_id in smart_info
                    attrs["smart_start_detail"] = smart_info.get(zone_id)
                try:
                    hr = sched_manager._get_zone_heating_rate(zone_id)
                    if isinstance(hr, (int, float)):
                        attrs["heating_rate"] = hr
                except AttributeError:
                    pass

        try:
            attrs["cooling_rate"] = coord.get_zone_cooling_rate(zone_id)
        except AttributeError:
            if sched_manager is not None:
                try:
                    cr = sched_manager._get_zone_cooling_rate(zone_id)
                    if isinstance(cr, (int, float)):
                        attrs["cooling_rate"] = cr
                except AttributeError:
                    pass

        if self._hvac_mode == HVACMode.COOL:
            active_mode = "cool"
        elif self._hvac_mode == HVACMode.HEAT:
            active_mode = "heat"
        else:
            season = attrs["master_hvac_mode"] or "heat"
            active_mode = "cool" if str(season).lower() == "cool" else "heat"
        attrs["pid_active_mode"] = active_mode
        tuner_getter = getattr(coord, "get_autotuner", None)
        cid_lookup = zone_id
        tuner = None
        if callable(tuner_getter):
            try:
                tuner = tuner_getter(cid_lookup, mode=active_mode)
            except TypeError:
                tuner = tuner_getter(cid_lookup)
        attrs.update(_collect_tuner_attrs(tuner))
        unlock_getter = getattr(coord, "get_pid_manual_unlock", None)
        if callable(unlock_getter):
            unlock_val = unlock_getter(self._name)
            if isinstance(unlock_val, bool):
                attrs["pid_manual_unlock"] = unlock_val

        split_is_heating = False
        hydronic_suppressed = False
        split_mgr = getattr(coord, "split_manager", None)
        if split_mgr is not None and split_mgr.has_split(zone_id):
            split_info = split_mgr.get_split_info(zone_id) or {}
            attrs["split_climate_entity"] = split_info.get("split_entity_id")
            split_is_active = bool(split_mgr.is_split_active(zone_id))
            attrs["split_active"] = split_is_active
            attrs["split_manual_on"] = bool(split_mgr.is_local_manual_on(zone_id))
            split_is_heating = (self._hvac_mode == HVACMode.HEAT and split_is_active)
            attrs["split_cooling"] = (self._hvac_mode == HVACMode.COOL and split_is_active)
            attrs["split_quick_boost_active"] = bool(split_mgr.is_quick_boost_active(zone_id))
            hydronic_suppressed = bool(split_mgr.should_suppress_hydronic_demand(zone_id))
            attrs["split_hydronic_suppressed"] = hydronic_suppressed

        # Determine real-time active heating source: gas, electric, dual, or none
        try:
            master_on = bool(coord.get_master_state())
        except AttributeError:
            master_on = True
        is_local_manual = bool(split_mgr.is_local_manual_on(zone_id)) if split_mgr else False

        is_heating = (self._hvac_mode == HVACMode.HEAT) and (self.hvac_action == HVACAction.HEATING or split_is_heating or is_local_manual)
        if not is_heating:
            attrs["active_heating_source"] = "none"
        else:
            gas_enabled = getattr(coord, "enable_gas_heater", True)
            hp_enabled = getattr(coord, "enable_heat_pump", False)
            hydronic_is_heating = master_on and (coord.get_zone_demand(zone_id) > 0) and not hydronic_suppressed
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

    async def async_turn_on(self) -> None:
        """Turn on the zone climate entity using the active season mode."""
        modes = self.hvac_modes
        master_mode = str(getattr(self._coordinator, "master_hvac_mode", "heat")).lower()
        if master_mode == "cool" and HVACMode.COOL in modes:
            target_mode = HVACMode.COOL
        elif HVACMode.HEAT in modes:
            target_mode = HVACMode.HEAT
        else:
            non_off = [m for m in modes if m != HVACMode.OFF]
            target_mode = non_off[0] if non_off else HVACMode.OFF
        await self.async_set_hvac_mode(target_mode)

    async def async_turn_off(self) -> None:
        """Turn off the zone climate entity."""
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        if hvac_mode not in self.hvac_modes:
            _LOGGER.warning(
                "Zone %s rejected unsupported HVAC mode %s (supported: %s)",
                self._name,
                hvac_mode,
                self.hvac_modes,
            )
            return
        self._hvac_mode = hvac_mode
        coord = self._coordinator
        zone_id = self._zone_id
        try:
            master_on = coord.get_master_state()
        except AttributeError:
            master_on = True
        split_mgr = getattr(coord, "split_manager", None)

        if hvac_mode == HVACMode.OFF:
            self._sync_manager._local_pwm_state = False
            coord.set_zone_demand(zone_id, 0.0)
            if split_mgr is not None:
                try:
                    split_mgr.set_local_manual_on(zone_id, False)
                except AttributeError:
                    pass
        else:
            if not master_on and split_mgr is not None:
                try:
                    if split_mgr.has_split(zone_id):
                        split_mgr.set_local_manual_on(zone_id, True)
                except AttributeError:
                    pass

        self.async_write_ha_state()
        await self._trigger_trv_sync()
        await self._sync_manager.async_sync_switches()
        await self._sync_manager.async_sync_proportional_valves(self._hvac_mode)
        zc = getattr(coord, "zone_controller", None)
        if zc is not None and self.hass and self.hass.states:
            st = self.hass.states.get(self.entity_id)
            if st is not None:
                coro = zc.async_update_zone(zone_id, st)
                if inspect.iscoroutine(coro):
                    await coro
                self.async_write_ha_state()

    async def async_apply_internal_target(self, temp_c: float) -> None:
        """Apply a programmatic Celsius target setpoint without recording a manual override."""
        try:
            temperature = float(temp_c)
        except (TypeError, ValueError):
            return
        if not math.isfinite(temperature):
            return
        temperature = max(self._attr_min_temp, min(self._attr_max_temp, temperature))
        self._target_temperature = temperature
        self.async_write_ha_state()
        await self._trigger_trv_sync()
        zc = getattr(self._coordinator, "zone_controller", None)
        if zc is not None and self.hass and self.hass.states:
            st = self.hass.states.get(self.entity_id)
            if st is not None:
                coro = zc.async_update_zone(self._zone_id, st)
                if inspect.iscoroutine(coro):
                    await coro
                self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperature."""
        raw_temp = kwargs.get(ATTR_TEMPERATURE)
        if raw_temp is None:
            return
        try:
            temperature = float(raw_temp)
        except (TypeError, ValueError):
            return
        if not math.isfinite(temperature):
            return

        coord = self._coordinator
        zone_id = self._zone_id
        self._target_temperature = temperature
        cal_mgr = getattr(coord, "calendar_manager", None)
        if cal_mgr is not None and zone_id in cal_mgr.temp_overrides:
            if hasattr(cal_mgr, "set_temp_override"):
                cal_mgr.set_temp_override(zone_id, temperature)
            else:
                cal_mgr.temp_overrides[zone_id] = temperature

        sched_manager = getattr(coord, "schedule_manager", None)
        sched_enabled = bool(sched_manager and getattr(sched_manager, "scheduler_enabled", False) is True)
        if sched_enabled:
            sched_manager.record_manual_override(zone_id, temperature)
            try:
                self.hass.async_create_task(sched_manager.async_save_to_storage())
            except AttributeError:
                pass

        has_temp_slot_override = (
            sched_enabled
            and isinstance(getattr(sched_manager, "manual_overrides", None), dict)
            and zone_id in sched_manager.manual_overrides
        )
        current_preset = coord.get_global_preset()
        if current_preset and current_preset != "none":
            target_preset = "manual" if has_temp_slot_override else current_preset
            mode_val = str(self._hvac_mode.value if isinstance(self._hvac_mode, HVACMode) else self._hvac_mode)
            if mode_val == "cool":
                coord.zone_manager.update_preset_temperature(
                    target_preset, zone_id, temperature, hvac_mode="cool"
                )
            else:
                coord.zone_manager.update_preset_temperature(
                    target_preset, zone_id, temperature
                )

        self.async_write_ha_state()
        await self._trigger_trv_sync()
        zc = getattr(coord, "zone_controller", None)
        if zc is not None and self.hass and self.hass.states:
            st = self.hass.states.get(self.entity_id)
            if st is not None:
                coro = zc.async_update_zone(zone_id, st)
                if inspect.iscoroutine(coro):
                    await coro
                self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added."""
        await super().async_added_to_hass()
        
        self._coordinator.register_climate(
            self.entity_id,
            self.async_write_ha_state,
            self,
            canonical_id=self._canonical_id or self.entity_id,
        )

        self._hvac_mode, self._target_temperature = await ZoneStateRestorer.async_restore_state(
            self, self._hvac_mode, self._target_temperature
        )
        if self._hvac_mode not in self.hvac_modes:
            self._hvac_mode = HVACMode.OFF
                
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

        if self._climates and self._temp_sensor and self._calibrations:
            self._unsub_listeners.append(
                async_track_time_interval(
                    self.hass, self._async_ext_temp_heartbeat_tick, timedelta(minutes=10)
                )
            )

        if self._climates and self._trv_control_mode == TRV_CONTROL_MODE_DEMAND_DRIVEN:
            self._unsub_listeners.append(
                async_track_time_interval(
                    self.hass, self._async_trv_demand_tick, timedelta(seconds=10)
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
            if self._safety_fallback_active and self._calibrations and self._climates:
                self.hass.async_create_task(
                    self._sync_manager.async_external_temp_heartbeat(
                        master_current_temp=self._current_temperature,
                        safety_fallback_active=True,
                        has_external_sensor=bool(self._temp_sensor),
                    )
                )
            if (
                self._safety_fallback_active
                and self._climates
                and self._trv_control_mode == TRV_CONTROL_MODE_DEMAND_DRIVEN
            ):
                self.hass.async_create_task(self._trigger_trv_sync())
            return

        try:
            parsed_val = float(new_state.state)
            if not math.isfinite(parsed_val):
                _LOGGER.warning("Zone %s: Ignoring non-finite temperature %s", self._name, new_state.state)
                return
            unit = get_state_temp_unit(new_state)
            self._current_temperature = to_celsius(parsed_val, unit, self.hass)
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
                    parsed_val = float(state.state)
                    if not math.isfinite(parsed_val):
                        raise ValueError(f"Non-finite temperature: {state.state}")
                    now = time.time()
                    reported = getattr(state, "last_reported", None) or getattr(state, "last_updated", None)
                    try:
                        ts = reported.timestamp() if reported is not None else None
                    except AttributeError:
                        ts = None
                    elapsed = (now - ts) if isinstance(ts, (int, float)) else 0.0
                    
                    if self._sensor_timeout_min == 0 or elapsed <= (self._sensor_timeout_min * 60):
                        unit = get_state_temp_unit(state)
                        self._current_temperature = to_celsius(parsed_val, unit, self.hass)
                        ext_temp_valid = True
                        if self._safety_fallback_active:
                            _LOGGER.info("Zone %s: External temp sensor recovered. Exiting safety fallback.", self._name)
                            self._safety_fallback_active = False
                    else:
                        _LOGGER.warning("Zone %s: Sensor timeout reached (%d min). Falling back to TRVs.", self._name, int(elapsed / 60))
                except (ValueError, TypeError):
                    pass

        if not ext_temp_valid:
            from .safety.watchdog import SensorWatchdog
            avg_temp = SensorWatchdog(self.hass).get_zone_trv_fallback_temp(
                {CONF_ZONE_CLIMATES: self._climates}, self.hass
            )
            if avg_temp is not None:
                self._current_temperature = avg_temp
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
        zone_id = self._zone_id
        if new_mode is not None:
            self._hvac_mode = new_mode
            if new_mode == HVACMode.OFF:
                self._sync_manager._local_pwm_state = False
                self._coordinator.set_zone_demand(zone_id, 0.0)
                await self._sync_manager.async_sync_switches()
                await self._sync_manager.async_sync_proportional_valves(self._hvac_mode)
            needs_sync = True
            
        if delta_temp is not None and self._target_temperature is not None and self._hvac_mode != HVACMode.OFF:
            coord = self._coordinator
            cal_mgr = getattr(coord, "calendar_manager", None)
            sched_manager = getattr(coord, "schedule_manager", None)
            sched_enabled = bool(sched_manager and getattr(sched_manager, "scheduler_enabled", False) is True)
            if sched_enabled:
                base_temp = self.target_temperature if self.target_temperature is not None else self._target_temperature
                new_temp = max(self._attr_min_temp, min(self._attr_max_temp, base_temp + delta_temp))
                self._target_temperature = new_temp
                if cal_mgr is not None and zone_id in cal_mgr.temp_overrides:
                    if hasattr(cal_mgr, "set_temp_override"):
                        cal_mgr.set_temp_override(zone_id, self._target_temperature)
                    else:
                        cal_mgr.temp_overrides[zone_id] = self._target_temperature
                sched_manager.record_manual_override(zone_id, new_temp)
                try:
                    self.hass.async_create_task(sched_manager.async_save_to_storage())
                except AttributeError:
                    pass
            else:
                self._target_temperature = max(self._attr_min_temp, min(self._attr_max_temp, self._target_temperature + delta_temp))
                if cal_mgr is not None and zone_id in cal_mgr.temp_overrides:
                    if hasattr(cal_mgr, "set_temp_override"):
                        cal_mgr.set_temp_override(zone_id, self._target_temperature)
                    else:
                        cal_mgr.temp_overrides[zone_id] = self._target_temperature
            has_temp_slot_override = (
                sched_enabled
                and isinstance(getattr(sched_manager, "manual_overrides", None), dict)
                and zone_id in sched_manager.manual_overrides
            )
            current_preset = coord.get_global_preset()
            if current_preset and current_preset != "none":
                target_preset = "manual" if has_temp_slot_override else current_preset
                mode_val = str(self._hvac_mode.value if isinstance(self._hvac_mode, HVACMode) else self._hvac_mode)
                if mode_val == "cool":
                    coord.zone_manager.update_preset_temperature(
                        target_preset, zone_id, self._target_temperature, hvac_mode="cool"
                    )
                else:
                    coord.zone_manager.update_preset_temperature(
                        target_preset, zone_id, self._target_temperature
                    )
            needs_sync = True
            
        if needs_sync:
            self.async_write_ha_state()
            await self._trigger_trv_sync()

    async def _trigger_trv_sync(self) -> None:
        """Helper to invoke SyncManager's TRV sync."""
        zone_demand = (
            self._coordinator.get_zone_demand(self._zone_id)
            if hasattr(self._coordinator, "get_zone_demand")
            else None
        )
        await self._sync_manager.async_sync_trvs(
            master_hvac_mode=self._hvac_mode,
            master_target_temp=self.target_temperature,
            master_current_temp=self._current_temperature,
            safety_fallback_active=self._safety_fallback_active,
            has_external_sensor=bool(self._temp_sensor),
            zone_demand=zone_demand,
        )

    async def _async_pwm_tick(self, now: Any) -> None:
        """Evaluate local PWM for switches."""
        if await self._sync_manager.async_pwm_tick(self._hvac_mode):
            self.async_write_ha_state()

    async def _async_valve_tick(self, now: Any) -> None:
        """Evaluate and synchronize proportional valves."""
        await self._sync_manager.async_sync_proportional_valves(self._hvac_mode)

    async def _async_ext_temp_heartbeat_tick(self, now: Any) -> None:
        """Periodically refresh external temperature feed and fallback source on TRVs."""
        self.check_sensor_staleness()
        await self._sync_manager.async_external_temp_heartbeat(
            master_current_temp=self._current_temperature,
            safety_fallback_active=self._safety_fallback_active,
            has_external_sensor=bool(self._temp_sensor),
        )

    async def _async_trv_demand_tick(self, now: Any) -> None:
        """Periodically re-evaluate demand-driven TRV open/close targets."""
        self.check_sensor_staleness()
        zone_demand = (
            self._coordinator.get_zone_demand(self._zone_id)
            if hasattr(self._coordinator, "get_zone_demand")
            else None
        )
        await self._sync_manager.async_demand_driven_tick(
            master_hvac_mode=self._hvac_mode,
            master_target_temp=self.target_temperature,
            master_current_temp=self._current_temperature,
            safety_fallback_active=self._safety_fallback_active,
            has_external_sensor=bool(self._temp_sensor),
            zone_demand=zone_demand,
        )

