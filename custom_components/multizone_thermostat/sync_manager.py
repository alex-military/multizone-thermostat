"""TRV and Switch synchronization logic for Multizone Thermostat."""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
import logging
import math
import re
import time
from typing import Any

import homeassistant.util.dt as dt_util
from homeassistant.components.climate import HVACMode
from homeassistant.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE, SERVICE_TURN_OFF, SERVICE_TURN_ON, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, Context, State, Event

from .pwm_engine import PWMEngine
from .const import (
    KEY_PHYSICAL_SYNC_PREFIX,
    VALVE_SCALE_VOLT,
    DEFAULT_VALVE_SCALE,
    DEFAULT_MIN_CYCLE_ON,
    DEFAULT_MIN_CYCLE_OFF,
    CONF_ZONE_EMITTER_TYPE,
    EMITTER_TYPE_RADIATOR,
    EMITTER_TYPE_UNDERFLOOR,
    EMITTER_TYPE_FANCOIL,
    DEFAULT_ZONE_EMITTER_TYPE,
    TRV_CALIB_MODE_AUTO,
    TRV_CALIB_MODE_OFFSET,
    TRV_CALIB_MODE_EXTERNAL,
    TRV_CALIB_MODE_DISABLED,
    TRV_CALIB_MODES,
    DEFAULT_TRV_CALIB_MODE,
    DEFAULT_EXTERNAL_TEMP_HEARTBEAT_S,
    DEFAULT_EXTERNAL_TEMP_MIN_INTERVAL_S,
    DEFAULT_OFFSET_MIN_INTERVAL_S,
    DEFAULT_OFFSET_DEADBAND_C,
    DEFAULT_OFFSET_SETTLE_S,
    DEFAULT_OFFSET_MAX_UNRESPONSIVE,
    TRV_CONTROL_MODE_STANDARD,
    TRV_CONTROL_MODE_DEMAND_DRIVEN,
    TRV_CONTROL_MODES,
    DEFAULT_TRV_CONTROL_MODE,
    DEFAULT_TRV_OPEN_BOOST,
    DEFAULT_TRV_CLOSE_OFFSET,
    DEFAULT_TRV_DEMAND_OPEN_THRESHOLD,
    DEFAULT_TRV_DEMAND_DEBOUNCE_S,
    get_state_temp_unit,
    to_celsius,
    from_celsius,
)

_LOGGER = logging.getLogger(__name__)

EMITTER_PWM_INTERVALS: dict[str, float] = {
    EMITTER_TYPE_RADIATOR: 900.0,    # 15 min default for radiators
    EMITTER_TYPE_UNDERFLOOR: 1800.0, # 30 min default for underfloor
    EMITTER_TYPE_FANCOIL: 600.0,     # 10 min default for fan coils
}


class ZoneSyncManager:
    """Manages the synchronization of state from virtual zone to physical TRVs, Switches, and Proportional Valves."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: Any,
        zone_name: str,
        entity_id: str,
        climates: list[str],
        switches: list[str],
        calibrations: dict[str, str],
        valves: list[str] | None = None,
        valve_scale: str = DEFAULT_VALVE_SCALE,
        authoritative_sync: bool = False,
        emitter_type: str = DEFAULT_ZONE_EMITTER_TYPE,
        calibration_mode: str = DEFAULT_TRV_CALIB_MODE,
        trv_sensor_selects: dict[str, str] | None = None,
        ext_temp_heartbeat_s: float = DEFAULT_EXTERNAL_TEMP_HEARTBEAT_S,
        ext_temp_min_interval_s: float = DEFAULT_EXTERNAL_TEMP_MIN_INTERVAL_S,
        offset_min_interval_s: float = DEFAULT_OFFSET_MIN_INTERVAL_S,
        offset_deadband_c: float = DEFAULT_OFFSET_DEADBAND_C,
        offset_settle_s: float = DEFAULT_OFFSET_SETTLE_S,
        offset_max_unresponsive: int = DEFAULT_OFFSET_MAX_UNRESPONSIVE,
        trv_control_mode: str = DEFAULT_TRV_CONTROL_MODE,
        trv_open_boost: float = DEFAULT_TRV_OPEN_BOOST,
        trv_close_offset: float = DEFAULT_TRV_CLOSE_OFFSET,
        trv_demand_open_threshold: float = DEFAULT_TRV_DEMAND_OPEN_THRESHOLD,
        trv_demand_debounce_s: float = DEFAULT_TRV_DEMAND_DEBOUNCE_S,
        invert_switch: bool = False,
        invert_valve: bool = False,
    ) -> None:
        """Initialize the sync manager."""
        self.hass = hass
        self._coordinator = coordinator
        self._zone_name = zone_name
        self._entity_id = entity_id
        self._climates = climates
        self._switches = switches
        self._valves = valves or []
        self._valve_scale = valve_scale
        self._invert_switch = bool(invert_switch)
        self._invert_valve = bool(invert_valve)
        self._calibrations = calibrations
        self._authoritative_sync = bool(authoritative_sync)
        self._calibration_mode = (
            calibration_mode
            if calibration_mode in TRV_CALIB_MODES
            else DEFAULT_TRV_CALIB_MODE
        )
        self._trv_sensor_selects: dict[str, str] = dict(trv_sensor_selects or {})
        self._ext_temp_heartbeat_s = float(ext_temp_heartbeat_s)
        self._ext_temp_min_interval_s = float(ext_temp_min_interval_s)
        self._offset_min_interval_s = max(0.0, float(offset_min_interval_s))
        self._offset_deadband_c = max(0.0, float(offset_deadband_c))
        self._offset_settle_s = max(0.0, float(offset_settle_s))
        self._offset_max_unresponsive = max(1, int(offset_max_unresponsive))
        self._last_ext_temp_push: dict[str, tuple[float, float]] = {}
        self._last_offset_write_ts: dict[str, float] = {}
        self._last_written_calib: dict[str, float] = {}
        self._offset_unresponsive_count: dict[str, int] = {}
        self._offset_stalled: dict[str, bool] = {}
        self._last_valve_positions: dict[str, float] = {}

        self._trv_control_mode = (
            trv_control_mode if trv_control_mode in TRV_CONTROL_MODES else DEFAULT_TRV_CONTROL_MODE
        )
        try:
            self._trv_open_boost = max(0.0, min(5.0, float(trv_open_boost)))
        except (ValueError, TypeError):
            self._trv_open_boost = DEFAULT_TRV_OPEN_BOOST
        try:
            self._trv_close_offset = max(0.0, min(5.0, float(trv_close_offset)))
        except (ValueError, TypeError):
            self._trv_close_offset = DEFAULT_TRV_CLOSE_OFFSET
        try:
            self._trv_demand_open_threshold = max(0.0, min(100.0, float(trv_demand_open_threshold)))
        except (ValueError, TypeError):
            self._trv_demand_open_threshold = DEFAULT_TRV_DEMAND_OPEN_THRESHOLD
        try:
            self._trv_demand_debounce_s = max(0.0, float(trv_demand_debounce_s))
        except (ValueError, TypeError):
            self._trv_demand_debounce_s = DEFAULT_TRV_DEMAND_DEBOUNCE_S
        self._demand_valve_open: bool | None = None
        self._last_demand_switch_mono: float | None = None

        self._sync_lock = asyncio.Lock()
        self._trv_event_lock = self._sync_lock
        self._last_known_trv_targets: dict[str, float] = {}
        self._pending_trv_targets: dict[str, float] = {}
        self._pending_calib: dict[str, tuple[float, float, float]] = {}
        self._internal_context = Context()

        self._emitter_type = emitter_type
        min_on_s = float(getattr(coordinator, "_min_cycle_on", DEFAULT_MIN_CYCLE_ON)) * 60.0
        min_off_s = float(getattr(coordinator, "_min_cycle_off", DEFAULT_MIN_CYCLE_OFF)) * 60.0
        base_pwm_interval = EMITTER_PWM_INTERVALS.get(emitter_type, 900.0)
        self._local_pwm = PWMEngine(pwm_interval=base_pwm_interval, min_on=min_on_s, min_off=min_off_s)
        self._local_pwm_state = False
        self._last_pwm_change: float = time.monotonic()

        self.trv_health: dict[str, dict[str, Any]] = {
            trv: {
                "sync_status": "INITIALIZED",
                "last_command_target": None,
                "last_command_mode": None,
                "last_command_time": None,
                "last_ack_time": None,
                "last_reported_temp": None,
                "latency_s": None,
                "consecutive_timeouts": 0,
                "last_error": None,
            }
            for trv in self._climates
        }

    @property
    def internal_context(self) -> Context:
        """Return the internal context used to flag self-generated events."""
        return self._internal_context

    @property
    def _sync_switch_key(self) -> str:
        """Return the dynamic key for physical sync persistence."""
        safe_name = self._zone_name.lower().replace(" ", "_").replace("-", "_")
        safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
        return f"{KEY_PHYSICAL_SYNC_PREFIX}{safe_name}"

    def get_trv_health(self) -> dict[str, Any]:
        """Return sanitized TRV health statistics."""
        sanitized = {}
        for trv, health in self.trv_health.items():
            entry = dict(health)
            entry.pop("last_command_time_monotonic", None)
            sanitized[trv] = entry
        return sanitized

    def init_known_targets(self) -> None:
        """Initialize known targets from HA states."""
        for trv in self._climates:
            st = self.hass.states.get(trv)
            if st and st.attributes.get(ATTR_TEMPERATURE) is not None:
                try:
                    self._last_known_trv_targets[trv] = to_celsius(
                        float(st.attributes[ATTR_TEMPERATURE]), get_state_temp_unit(st), self.hass
                    )
                except (ValueError, TypeError):
                    pass

    def resolve_calibration_mode(self, calib_entity: str, calib_state: State | None) -> str:
        """Resolve whether a calibration entity uses offset, external temperature, or is disabled."""
        if self._calibration_mode == TRV_CALIB_MODE_DISABLED:
            return TRV_CALIB_MODE_DISABLED
        if self._calibration_mode == TRV_CALIB_MODE_OFFSET:
            return TRV_CALIB_MODE_OFFSET
        if self._calibration_mode == TRV_CALIB_MODE_EXTERNAL:
            return TRV_CALIB_MODE_EXTERNAL

        eid = str(calib_entity).lower()
        if (
            "calibration" in eid
            or "offset" in eid
            or re.search(r"(^|_|\.)cal($|_)", eid)
        ):
            return TRV_CALIB_MODE_OFFSET
        if any(
            kw in eid
            for kw in (
                "external_temp",
                "remote_temp",
                "external_measured_room_sensor",
                "room_sensor_temp",
                "external_sensor",
            )
        ):
            return TRV_CALIB_MODE_EXTERNAL

        attrs = getattr(calib_state, "attributes", None) if calib_state is not None else None
        if isinstance(attrs, Mapping):
            raw_min = attrs.get("min")
            raw_max = attrs.get("max")
            try:
                if raw_min is not None and raw_max is not None:
                    min_v = float(raw_min)
                    max_v = float(raw_max)
                    if math.isfinite(min_v) and math.isfinite(max_v):
                        if min_v >= 0.0 and max_v >= 30.0:
                            return TRV_CALIB_MODE_EXTERNAL
                        if min_v < 0.0 and max_v <= 15.0:
                            return TRV_CALIB_MODE_OFFSET
            except (ValueError, TypeError):
                pass

        return TRV_CALIB_MODE_OFFSET

    async def _async_set_trv_sensor_source(self, trv: str, use_remote: bool) -> None:
        """Optionally switch TRV sensor source select entity between remote and local."""
        select_entity = self._trv_sensor_selects.get(trv)
        if not select_entity:
            return
        sel_state = self.hass.states.get(select_entity)
        if not sel_state or sel_state.state == STATE_UNAVAILABLE:
            return
        attrs = getattr(sel_state, "attributes", None)
        if not isinstance(attrs, Mapping):
            return
        raw_options = attrs.get("options")
        if not isinstance(raw_options, (list, tuple)):
            return
        options = [str(opt) for opt in raw_options]
        if not options:
            return

        valid_options = [(opt, opt.lower()) for opt in options if "offline" not in opt.lower()]
        if not valid_options:
            return

        if use_remote:
            exact_names = ("remote_temperature", "external", "remote", "external_sensor", "external_2")
            partial_kws = ("remote", "external")
        else:
            exact_names = ("local_temperature", "internal", "local", "internal_sensor", "built_in")
            partial_kws = ("local", "internal")

        target_opt: str | None = None
        for candidate in exact_names:
            for opt, opt_low in valid_options:
                if opt_low == candidate:
                    target_opt = opt
                    break
            if target_opt is not None:
                break

        if target_opt is None:
            for opt, opt_low in valid_options:
                if any(kw in opt_low for kw in partial_kws):
                    target_opt = opt
                    break

        if target_opt is not None and sel_state.state != target_opt:
            try:
                await self.hass.services.async_call(
                    "select",
                    "select_option",
                    {"entity_id": select_entity, "option": target_opt},
                    blocking=True,
                    context=self._internal_context,
                )
            except Exception as err:
                _LOGGER.warning(
                    "Failed to switch TRV sensor source %s for %s to '%s': %s",
                    select_entity,
                    trv,
                    target_opt,
                    err,
                )

    async def _async_push_external_temp(
        self,
        trv: str,
        calib_entity: str,
        master_current_temp: float,
        force: bool = False,
    ) -> bool:
        """Push absolute external room temperature to TRV external temperature input with heartbeat."""
        try:
            master_curr_f = float(master_current_temp)
        except (ValueError, TypeError):
            return False
        if not math.isfinite(master_curr_f):
            return False

        calib_state = self.hass.states.get(calib_entity)
        if calib_state is not None and calib_state.state == STATE_UNAVAILABLE:
            return False

        attrs = getattr(calib_state, "attributes", None) if calib_state is not None else None
        has_attrs = isinstance(attrs, Mapping)

        c_unit = attrs.get("unit_of_measurement") if has_attrs else None
        if c_unit is not None and str(c_unit).strip().lower() in ("°f", "f", "fahrenheit"):
            val_out = from_celsius(master_curr_f, unit=str(c_unit))
        else:
            val_out = master_curr_f

        raw_step = attrs.get("step") if has_attrs else None
        step_val: float | None = None
        if raw_step is not None:
            try:
                parsed_step = float(raw_step)
                if math.isfinite(parsed_step) and parsed_step > 0.0:
                    step_val = parsed_step
            except (ValueError, TypeError):
                step_val = None
        if step_val is not None:
            val_out = round(round(val_out / step_val) * step_val, 4)
        else:
            val_out = round(val_out, 1)

        if has_attrs:
            c_min = attrs.get("min")
            c_max = attrs.get("max")
            if c_min is not None:
                try:
                    min_v = float(c_min)
                    if math.isfinite(min_v):
                        val_out = max(min_v, val_out)
                except (ValueError, TypeError):
                    pass
            if c_max is not None:
                try:
                    max_v = float(c_max)
                    if math.isfinite(max_v):
                        val_out = min(max_v, val_out)
                except (ValueError, TypeError):
                    pass

        now_mono = time.monotonic()
        last_val, last_ts = self._last_ext_temp_push.get(trv, (None, None))
        curr_num: float | None = None
        if calib_state is not None and calib_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            try:
                parsed_curr = float(calib_state.state)
                if math.isfinite(parsed_curr):
                    curr_num = parsed_curr
            except (ValueError, TypeError):
                curr_num = None

        heartbeat_due = (last_ts is None) or ((now_mono - last_ts) >= self._ext_temp_heartbeat_s)
        value_changed = (
            (curr_num is None)
            or (round(abs(val_out - curr_num), 3) >= 0.1)
            or (last_val is not None and round(abs(val_out - last_val), 3) >= 0.1)
        )

        if not force and not heartbeat_due and not value_changed:
            return False

        if (
            not force
            and not heartbeat_due
            and last_ts is not None
            and (now_mono - last_ts) < self._ext_temp_min_interval_s
            and last_val is not None
            and round(abs(val_out - last_val), 3) < 0.5
        ):
            return False

        try:
            await self._async_set_trv_sensor_source(trv, use_remote=True)
            domain = "input_number" if calib_entity.startswith("input_number.") else "number"
            await self.hass.services.async_call(
                domain,
                "set_value",
                {"entity_id": calib_entity, "value": val_out},
                blocking=True,
                context=self._internal_context,
            )
            self._last_ext_temp_push[trv] = (val_out, now_mono)
            health = self.trv_health.setdefault(trv, {})
            health["ext_temp_feed_mode"] = TRV_CALIB_MODE_EXTERNAL
            health["last_ext_temp_sent"] = val_out
            health["last_ext_temp_time"] = dt_util.now().isoformat()
            return True
        except Exception as err:
            _LOGGER.warning(
                "Failed to push external temperature to %s for TRV %s: %s",
                calib_entity,
                trv,
                err,
            )
            return False

    async def async_external_temp_heartbeat(
        self,
        master_current_temp: float | None,
        safety_fallback_active: bool,
        has_external_sensor: bool,
    ) -> None:
        """Periodic heartbeat / fallback check for TRVs configured with external temperature feed."""
        if (
            self._calibration_mode == TRV_CALIB_MODE_DISABLED
            or not has_external_sensor
            or not self._calibrations
            or not self._climates
        ):
            return

        async with self._sync_lock:
            for trv in self._climates:
                calib_entity = self._calibrations.get(trv)
                if not calib_entity:
                    continue
                st = self.hass.states.get(trv)
                if not st or st.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                    continue
                calib_state = self.hass.states.get(calib_entity)
                if self.resolve_calibration_mode(calib_entity, calib_state) != TRV_CALIB_MODE_EXTERNAL:
                    continue
                if safety_fallback_active:
                    self._last_ext_temp_push.pop(trv, None)
                    await self._async_set_trv_sensor_source(trv, use_remote=False)
                elif master_current_temp is not None:
                    await self._async_push_external_temp(
                        trv, calib_entity, float(master_current_temp)
                    )

    async def _async_sync_trv_offset(
        self,
        trv: str,
        calib_entity: str,
        calib_state: State | None,
        master_curr_f: float,
        trv_curr_f: float,
    ) -> None:
        """Synchronize TRV temperature_offset with deadband, cooldown, and anti-ratchet guard."""
        try:
            if calib_state is not None and calib_state.state == STATE_UNAVAILABLE:
                return

            now_mono = time.monotonic()
            current_calib_value = 0.0
            calib_state_valid = False
            if calib_state and calib_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                try:
                    parsed = float(calib_state.state)
                    if math.isfinite(parsed):
                        current_calib_value = parsed
                        calib_state_valid = True
                except (ValueError, TypeError):
                    pass

            # Detect external/manual reset or adjustment of the calibration entity
            last_written = self._last_written_calib.get(trv)
            if (
                last_written is not None
                and calib_state_valid
                and abs(current_calib_value - last_written) >= 0.15
            ):
                self._pending_calib.pop(trv, None)
                self._last_written_calib.pop(trv, None)
                self._last_offset_write_ts.pop(trv, None)
                self._offset_unresponsive_count[trv] = 0
                self._offset_stalled[trv] = False
                self.trv_health.setdefault(trv, {})["offset_stalled"] = False

            effective_base_calib = current_calib_value
            if trv in self._pending_calib:
                _written_off, prev_trv_curr, prev_base_calib, expected_delta_c, sent_ts = (
                    self._pending_calib[trv]
                )
                trv_shift = trv_curr_f - prev_trv_curr
                moved_expected = (
                    expected_delta_c != 0.0
                    and (trv_shift * expected_delta_c) > 0.0
                    and abs(trv_shift) >= max(0.1, 0.3 * abs(expected_delta_c))
                )
                if moved_expected:
                    self._pending_calib.pop(trv, None)
                    self._offset_unresponsive_count[trv] = 0
                    self._offset_stalled[trv] = False
                    self.trv_health.setdefault(trv, {})["offset_stalled"] = False
                elif (now_mono - sent_ts) < self._offset_settle_s:
                    effective_base_calib = prev_base_calib
                else:
                    self._pending_calib.pop(trv, None)
                    if abs(expected_delta_c) >= 0.3:
                        cnt = self._offset_unresponsive_count.get(trv, 0) + 1
                        self._offset_unresponsive_count[trv] = cnt
                        if cnt >= self._offset_max_unresponsive:
                            self._offset_stalled[trv] = True
                            self.trv_health.setdefault(trv, {})["offset_stalled"] = True
                            _LOGGER.warning(
                                "TRV %s current_temperature did not respond after %d offset writes "
                                "(common when externally bound via Matter/Thread); pausing offset "
                                "integration. Consider setting trv_calibration_mode to 'disabled'.",
                                trv,
                                cnt,
                            )

            health = self.trv_health.setdefault(trv, {})
            health["ext_temp_feed_mode"] = TRV_CALIB_MODE_OFFSET

            if self._offset_stalled.get(trv):
                return

            delta_c = master_curr_f - trv_curr_f
            if abs(delta_c) < self._offset_deadband_c:
                return

            last_ts = self._last_offset_write_ts.get(trv)
            if last_ts is not None and (now_mono - last_ts) < self._offset_min_interval_s:
                return

            c_unit = (
                calib_state.attributes.get("unit_of_measurement")
                if (calib_state and getattr(calib_state, "attributes", None))
                else None
            )
            if c_unit is not None and str(c_unit).strip().lower() in ("°f", "f", "fahrenheit"):
                delta_out = delta_c * 9.0 / 5.0
            else:
                delta_out = delta_c

            offset = round(effective_base_calib + delta_out, 1)
            if calib_state:
                c_min = calib_state.attributes.get("min")
                c_max = calib_state.attributes.get("max")
                if c_min is not None:
                    try:
                        offset = max(float(c_min), offset)
                    except (ValueError, TypeError):
                        pass
                if c_max is not None:
                    try:
                        offset = min(float(c_max), offset)
                    except (ValueError, TypeError):
                        pass

            if not calib_state_valid or abs(offset - current_calib_value) >= 0.1:
                domain = "number" if not calib_entity.startswith("input_number.") else "input_number"
                await self.hass.services.async_call(
                    domain,
                    "set_value",
                    {"entity_id": calib_entity, "value": offset},
                    blocking=True,
                    context=self._internal_context,
                )
                self._last_offset_write_ts[trv] = now_mono
                self._last_written_calib[trv] = offset
                self._pending_calib[trv] = (
                    offset,
                    trv_curr_f,
                    effective_base_calib,
                    delta_c,
                    now_mono,
                )
        except Exception as calib_err:
            _LOGGER.warning(
                "Failed to update calibration entity %s for TRV %s: %s",
                calib_entity,
                trv,
                calib_err,
            )

    @property
    def demand_valve_open(self) -> bool | None:
        """Return the current demand-driven virtual valve open state, if active."""
        return self._demand_valve_open

    def _read_zone_demand_and_master(
        self, explicit_demand: float | None = None
    ) -> tuple[float, bool, bool]:
        """Safely read zone demand (0-100), master active flag, and bypass status."""
        demand_val = 0.0
        raw_demand = explicit_demand
        if raw_demand is None and hasattr(self._coordinator, "get_zone_demand"):
            raw_demand = self._coordinator.get_zone_demand(self._entity_id)
        if (
            isinstance(raw_demand, (int, float))
            and not isinstance(raw_demand, bool)
            and math.isfinite(float(raw_demand))
        ):
            demand_val = max(0.0, min(100.0, float(raw_demand)))

        master_on = True
        if hasattr(self._coordinator, "get_master_state"):
            raw_master = self._coordinator.get_master_state()
            if isinstance(raw_master, bool):
                master_on = raw_master

        is_bypassed = False
        if hasattr(self._coordinator, "get_zone_mode"):
            raw_mode = self._coordinator.get_zone_mode(self._entity_id)
            if isinstance(raw_mode, str) and raw_mode == "bypass":
                is_bypassed = True

        return demand_val, master_on, is_bypassed

    def _evaluate_demand_valve_state(
        self,
        demand: float,
        master_on: bool,
        is_bypassed: bool,
        target_hvac_mode: HVACMode,
    ) -> bool:
        """Evaluate demand-driven open/close state with hysteresis and debounce."""
        now_mono = time.monotonic()
        if target_hvac_mode == HVACMode.OFF or not master_on or is_bypassed:
            self._demand_valve_open = False
            self._last_demand_switch_mono = None
            return False

        if demand >= self._trv_demand_open_threshold:
            desired = True
        elif demand <= 0.0:
            desired = False
        else:
            desired = bool(self._demand_valve_open)

        if self._demand_valve_open is None:
            self._demand_valve_open = desired
            if desired:
                self._last_demand_switch_mono = now_mono
            return desired

        if desired != self._demand_valve_open:
            last_ts = self._last_demand_switch_mono
            if last_ts is None or (now_mono - last_ts) >= self._trv_demand_debounce_s:
                self._demand_valve_open = desired
                self._last_demand_switch_mono = now_mono

        return self._demand_valve_open

    async def async_demand_driven_tick(
        self,
        master_hvac_mode: HVACMode,
        master_target_temp: float | None,
        master_current_temp: float | None,
        safety_fallback_active: bool,
        has_external_sensor: bool,
        zone_demand: float | None = None,
    ) -> None:
        """Periodic 10s check to re-evaluate demand-driven TRV valve targets."""
        if self._trv_control_mode != TRV_CONTROL_MODE_DEMAND_DRIVEN or not self._climates:
            return
        await self.async_sync_trvs(
            master_hvac_mode=master_hvac_mode,
            master_target_temp=master_target_temp,
            master_current_temp=master_current_temp,
            safety_fallback_active=safety_fallback_active,
            has_external_sensor=has_external_sensor,
            zone_demand=zone_demand,
        )

    async def async_sync_trvs(
        self,
        master_hvac_mode: HVACMode,
        master_target_temp: float | None,
        master_current_temp: float | None,
        safety_fallback_active: bool,
        has_external_sensor: bool,
        zone_demand: float | None = None,
    ) -> None:
        """Sync target temperature and mode to all sub-slave TRVs."""
        if not self._climates:
            return

        async with self._sync_lock:
            if master_hvac_mode in (HVACMode.OFF, HVACMode.COOL, "off", "cool"):
                target_hvac_mode = HVACMode.OFF
            else:
                target_hvac_mode = HVACMode.HEAT

            effective_demand_driven = (
                self._trv_control_mode == TRV_CONTROL_MODE_DEMAND_DRIVEN
                and not safety_fallback_active
                and target_hvac_mode == HVACMode.HEAT
                and master_current_temp is not None
            )
            demand_valve_open = False
            if self._trv_control_mode == TRV_CONTROL_MODE_DEMAND_DRIVEN:
                if safety_fallback_active:
                    self._demand_valve_open = None
                    self._last_demand_switch_mono = None
                else:
                    demand_val, master_on, is_bypassed = self._read_zone_demand_and_master(zone_demand)
                    demand_valve_open = self._evaluate_demand_valve_state(
                        demand_val, master_on, is_bypassed, target_hvac_mode
                    )

            for trv in self._climates:
                try:
                    st = self.hass.states.get(trv)
                    if not st or st.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                        continue

                    mode_changed = (st.state != target_hvac_mode)
                    # Sync HVAC Mode if supported by the TRV
                    if mode_changed:
                        supported_modes = st.attributes.get("hvac_modes")
                        if not supported_modes or target_hvac_mode in supported_modes:
                            await self.hass.services.async_call(
                                "climate",
                                "set_hvac_mode",
                                {"entity_id": trv, "hvac_mode": target_hvac_mode},
                                blocking=True,
                                context=self._internal_context,
                            )

                    if self._calibration_mode == TRV_CALIB_MODE_DISABLED:
                        calib_entity = None
                        calib_state = None
                        resolved_calib_mode = TRV_CALIB_MODE_DISABLED
                        self.trv_health.setdefault(trv, {})["ext_temp_feed_mode"] = TRV_CALIB_MODE_DISABLED
                    else:
                        calib_entity = self._calibrations.get(trv)
                        calib_state = self.hass.states.get(calib_entity) if calib_entity else None
                        resolved_calib_mode = (
                            self.resolve_calibration_mode(calib_entity, calib_state)
                            if calib_entity
                            else None
                        )
                    if (
                        has_external_sensor
                        and calib_entity
                        and resolved_calib_mode == TRV_CALIB_MODE_EXTERNAL
                    ):
                        if safety_fallback_active:
                            self._last_ext_temp_push.pop(trv, None)
                            await self._async_set_trv_sensor_source(trv, use_remote=False)
                        elif master_current_temp is not None:
                            await self._async_push_external_temp(
                                trv, calib_entity, float(master_current_temp)
                            )

                    # When syncing OFF, update last_known so delta is correct on resume
                    if target_hvac_mode == HVACMode.OFF:
                        device_target = st.attributes.get(ATTR_TEMPERATURE)
                        if device_target is not None:
                            try:
                                dt_val = to_celsius(float(device_target), get_state_temp_unit(st), self.hass)
                                if dt_val > 7.0 and not self._authoritative_sync:
                                    self._last_known_trv_targets[trv] = dt_val
                            except (ValueError, TypeError):
                                pass
                        continue

                    # Sync Target Temp & Calibration
                    if master_target_temp is not None:
                        trv_target = float(master_target_temp)
                        trv_current = st.attributes.get("current_temperature")
                        trv_curr_f: float | None = None
                        if trv_current is not None:
                            try:
                                trv_attrs = st.attributes if isinstance(getattr(st, "attributes", None), Mapping) else {}
                                trv_unit = trv_attrs.get("temperature_unit") or trv_attrs.get("unit_of_measurement")
                                trv_curr_f = to_celsius(float(trv_current), trv_unit, self.hass)
                            except (ValueError, TypeError):
                                trv_curr_f = None

                        if has_external_sensor and not safety_fallback_active and master_current_temp is not None and trv_curr_f is not None:
                            try:
                                master_curr_f = float(master_current_temp)
                            except (ValueError, TypeError):
                                master_curr_f = None

                            if master_curr_f is not None:
                                if calib_entity:
                                    if resolved_calib_mode == TRV_CALIB_MODE_EXTERNAL:
                                        pass  # Already handled via absolute external temperature push
                                    else:
                                        await self._async_sync_trv_offset(
                                            trv,
                                            calib_entity,
                                            calib_state,
                                            master_curr_f,
                                            trv_curr_f,
                                        )
                                else:
                                    if not effective_demand_driven:
                                        temp_offset = max(-3.0, min(3.0, trv_curr_f - master_curr_f))
                                        trv_target = master_target_temp + temp_offset
                                        trv_target = max(5.0, min(35.0, trv_target))

                        idle_closed_limit_c: float | None = None
                        if effective_demand_driven and master_current_temp is not None:
                            room_c = float(master_current_temp)
                            sensor_comp = 0.0
                            if not calib_entity and has_external_sensor and trv_curr_f is not None:
                                sensor_comp = max(-3.0, min(3.0, trv_curr_f - room_c))
                            eff_room = room_c + sensor_comp
                            eff_target = float(master_target_temp) + sensor_comp
                            if demand_valve_open:
                                trv_target = min(
                                    eff_room + self._trv_open_boost,
                                    eff_target + self._trv_open_boost,
                                )
                            else:
                                idle_closed_limit_c = max(5.0, min(35.0, eff_room - self._trv_close_offset))
                                trv_target = min(
                                    eff_target,
                                    eff_room - self._trv_close_offset,
                                )
                            trv_target = max(5.0, min(35.0, trv_target))
                        
                        out_target = from_celsius(trv_target, self.hass)
                        step = st.attributes.get("target_temp_step")
                        try:
                            step_val = float(step) if step is not None else 0.5
                        except (ValueError, TypeError):
                            step_val = 0.5
                        if step_val > 0:
                            out_target = round(out_target / step_val) * step_val

                        trv_min = st.attributes.get("min_temp")
                        trv_max = st.attributes.get("max_temp")
                        try:
                            min_val = float(trv_min) if trv_min is not None else from_celsius(5.0, self.hass)
                        except (ValueError, TypeError):
                            min_val = from_celsius(5.0, self.hass)
                        try:
                            max_val = float(trv_max) if trv_max is not None else from_celsius(35.0, self.hass)
                        except (ValueError, TypeError):
                            max_val = from_celsius(35.0, self.hass)
                        out_target = round(max(min_val, min(max_val, out_target)), 2)
                        sent_c = round(to_celsius(out_target, None, self.hass), 2)

                        idle_closed_limit: float | None = None
                        if idle_closed_limit_c is not None:
                            idle_closed_limit = from_celsius(idle_closed_limit_c, self.hass)
                            if step_val > 0:
                                idle_closed_limit = round(idle_closed_limit / step_val) * step_val
                            idle_closed_limit = round(max(min_val, min(max_val, idle_closed_limit)), 2)

                        current_device_target = st.attributes.get(ATTR_TEMPERATURE)
                        try:
                            curr_dev_target_f = float(current_device_target) if current_device_target is not None else None
                        except (ValueError, TypeError):
                            curr_dev_target_f = None

                        health = self.trv_health.setdefault(trv, {})
                        if self._trv_control_mode == TRV_CONTROL_MODE_DEMAND_DRIVEN:
                            health["trv_control_mode"] = (
                                TRV_CONTROL_MODE_DEMAND_DRIVEN
                                if effective_demand_driven
                                else f"{TRV_CONTROL_MODE_STANDARD}_fallback"
                            )
                            health["demand_valve_open"] = (
                                demand_valve_open if effective_demand_driven else None
                            )
                        else:
                            health["trv_control_mode"] = TRV_CONTROL_MODE_STANDARD

                        skip_idle_chatter = (
                            effective_demand_driven
                            and not demand_valve_open
                            and not mode_changed
                            and curr_dev_target_f is not None
                            and curr_dev_target_f >= min_val
                            and (
                                out_target >= curr_dev_target_f
                                or (idle_closed_limit is not None and curr_dev_target_f <= idle_closed_limit)
                            )
                        )

                        if not skip_idle_chatter and (mode_changed or curr_dev_target_f != out_target):
                            try:
                                await self.hass.services.async_call(
                                    "climate",
                                    "set_temperature",
                                    {"entity_id": trv, "temperature": out_target},
                                    blocking=True,
                                    context=self._internal_context,
                                )
                                health["last_command_target"] = sent_c
                                health["last_command_mode"] = str(target_hvac_mode)
                                health["last_command_time"] = dt_util.now().isoformat()
                                health["last_command_time_monotonic"] = time.monotonic()
                                health["sync_status"] = "PENDING_CONFIRMATION"

                                self._pending_trv_targets[trv] = sent_c
                                self._last_known_trv_targets[trv] = sent_c
                                self._coordinator.record_diagnostic_event("TRV_COMMAND_SENT", {
                                    "zone": self._zone_name,
                                    "trv": trv,
                                    "target": sent_c,
                                    "mode": str(target_hvac_mode),
                                })
                            except Exception as err:
                                _LOGGER.error("Failed to send temperature to TRV %s: %s", trv, err)
                                health["sync_status"] = "FAILED"
                                health["consecutive_timeouts"] = health.get("consecutive_timeouts", 0) + 1
                                health["last_error"] = str(err)
                                self._coordinator.record_diagnostic_event("TRV_COMMAND_FAILED", {
                                    "zone": self._zone_name,
                                    "trv": trv,
                                    "error": str(err),
                                })
                                self._pending_trv_targets.pop(trv, None)
                        elif not skip_idle_chatter:
                            self._last_known_trv_targets[trv] = sent_c
                except Exception as err:
                    _LOGGER.error("Error syncing TRV %s in zone %s: %s", trv, self._zone_name, err)

    async def async_pwm_tick(self, master_hvac_mode: HVACMode) -> bool:
        """Evaluate local PWM for switches. Returns True if state changed."""
        if not self._switches:
            return False

        min_on_s = float(getattr(self._coordinator, "_min_cycle_on", DEFAULT_MIN_CYCLE_ON)) * 60.0
        min_off_s = float(getattr(self._coordinator, "_min_cycle_off", DEFAULT_MIN_CYCLE_OFF)) * 60.0
        self._local_pwm.set_params(min_on=min_on_s, min_off=min_off_s)

        now = time.monotonic()
        master_on = self._coordinator.get_master_state() if hasattr(self._coordinator, "get_master_state") else True
        zone_mode = self._coordinator.get_zone_mode(self._entity_id) if hasattr(self._coordinator, "get_zone_mode") else None
        is_cooling = master_hvac_mode in (HVACMode.COOL, "cool")
        hp_cooling_allowed = bool(getattr(self._coordinator, "enable_heat_pump", False) and getattr(self._coordinator, "heat_pump_cooling", True))

        if (
            not master_on
            or master_hvac_mode in (HVACMode.OFF, "off")
            or zone_mode == "bypass"
            or (is_cooling and (not hp_cooling_allowed or self._emitter_type == EMITTER_TYPE_RADIATOR))
        ):
            new_pwm_state = False
        else:
            demand = self._coordinator.get_zone_demand(self._entity_id)
            wanted_state = self._local_pwm.calculate(demand)
            new_pwm_state = wanted_state

            # Protect direct valve switches against short cycling across fluctuating demand
            if wanted_state != self._local_pwm_state:
                elapsed = now - self._last_pwm_change
                if self._local_pwm_state is True and not wanted_state:
                    if demand > 0.0 and min_on_s > 0.0 and elapsed < min_on_s:
                        new_pwm_state = True
                elif self._local_pwm_state is False and wanted_state:
                    if demand < 99.0 and min_off_s > 0.0 and elapsed < min_off_s:
                        new_pwm_state = False

        changed = new_pwm_state != self._local_pwm_state
        if changed:
            self._local_pwm_state = new_pwm_state
            self._last_pwm_change = now
        await self.async_sync_switches()
        return changed

    async def async_sync_switches(self) -> None:
        """Turn local switches ON or OFF based on PWM state."""
        if not self._switches:
            return

        is_active = not self._local_pwm_state if self._invert_switch else self._local_pwm_state
        service = SERVICE_TURN_ON if is_active else SERVICE_TURN_OFF
        expected_state = STATE_ON if is_active else "off"

        for switch in self._switches:
            st = self.hass.states.get(switch)
            if not st or st.state == STATE_UNAVAILABLE:
                continue
            if st.state != expected_state:
                await self.hass.services.async_call(
                    "switch",
                    service,
                    {ATTR_ENTITY_ID: switch},
                    context=self._internal_context,
                )

    async def async_sync_proportional_valves(self, master_hvac_mode: HVACMode) -> None:
        """Synchronize proportional and 0-10V valves to current zone demand."""
        if not self._valves:
            return

        master_on = self._coordinator.get_master_state() if hasattr(self._coordinator, "get_master_state") else True
        zone_mode = self._coordinator.get_zone_mode(self._entity_id) if hasattr(self._coordinator, "get_zone_mode") else None
        is_cooling = master_hvac_mode in (HVACMode.COOL, "cool")
        hp_cooling_allowed = bool(getattr(self._coordinator, "enable_heat_pump", False) and getattr(self._coordinator, "heat_pump_cooling", True))

        if (
            not master_on
            or master_hvac_mode in (HVACMode.OFF, "off")
            or zone_mode == "bypass"
            or (is_cooling and (not hp_cooling_allowed or self._emitter_type == EMITTER_TYPE_RADIATOR))
        ):
            target_pct = 0.0
        else:
            target_pct = float(self._coordinator.get_zone_demand(self._entity_id))

        target_pct = max(0.0, min(100.0, target_pct))
        effective_pct = (100.0 - target_pct) if self._invert_valve else target_pct

        for valve_entity in self._valves:
            st = self.hass.states.get(valve_entity)
            if not st or st.state == STATE_UNAVAILABLE:
                continue
            target_val = round(effective_pct / 10.0, 1) if self._valve_scale == VALVE_SCALE_VOLT else round(effective_pct, 1)
            last_val = self._last_valve_positions.get(valve_entity)
            domain = valve_entity.split(".", 1)[0]

            curr_val: float | None = None
            raw_state = getattr(st, "state", None)
            if domain in ("number", "input_number") and isinstance(raw_state, (str, int, float)) and not isinstance(raw_state, bool):
                try:
                    parsed = float(raw_state)
                    if math.isfinite(parsed):
                        curr_val = parsed
                except (ValueError, TypeError):
                    curr_val = None
            elif domain == "valve":
                v_attrs = getattr(st, "attributes", None)
                pos_raw = (
                    (v_attrs.get("current_position") if "current_position" in v_attrs else v_attrs.get("position"))
                    if isinstance(v_attrs, Mapping)
                    else None
                )
                if isinstance(pos_raw, (str, int, float)) and not isinstance(pos_raw, bool):
                    try:
                        parsed = float(pos_raw)
                        if math.isfinite(parsed):
                            curr_val = parsed
                    except (ValueError, TypeError):
                        curr_val = None
                elif isinstance(raw_state, str) and raw_state == "closed":
                    curr_val = 0.0

            if curr_val is not None and abs(curr_val - target_val) < 0.05:
                self._last_valve_positions[valve_entity] = target_val
                continue

            # Deadband: only update if change is significant (>= 0.5% or 0.05V) or when going to 0 / 100
            if last_val is not None:
                threshold = 0.05 if self._valve_scale == VALVE_SCALE_VOLT else 0.5
                if abs(target_val - last_val) < threshold and target_val not in (0.0, 100.0, 10.0):
                    continue

            try:
                if domain == "valve":
                    await self.hass.services.async_call(
                        "valve",
                        "set_valve_position",
                        {ATTR_ENTITY_ID: valve_entity, "position": int(round(effective_pct))},
                        context=self._internal_context,
                    )
                elif domain in ("number", "input_number"):
                    await self.hass.services.async_call(
                        domain,
                        "set_value",
                        {ATTR_ENTITY_ID: valve_entity, "value": target_val},
                        context=self._internal_context,
                    )
                self._last_valve_positions[valve_entity] = target_val
            except Exception as err:
                _LOGGER.error("Failed to set proportional valve position for %s: %s", valve_entity, err)

    async_sync_valves = async_sync_proportional_valves

    async def process_trv_change(
        self,
        event: Event,
        master_context_id: str | None,
        master_hvac_mode: HVACMode,
        master_min_temp: float,
        master_max_temp: float
    ) -> tuple[HVACMode | None, float | None]:
        """
        Handle a physical TRV change.
        Returns (new_hvac_mode, delta_target_temp) if the master needs to update.
        """
        async with self._trv_event_lock:
            entity_id = event.data.get("entity_id")
            new_state: State | None = event.data.get("new_state")
            old_state: State | None = event.data.get("old_state")

            if not new_state or not old_state:
                return None, None

            raw_new_temp = new_state.attributes.get(ATTR_TEMPERATURE)
            try:
                new_temp = (
                    to_celsius(float(raw_new_temp), get_state_temp_unit(new_state), self.hass)
                    if raw_new_temp is not None
                    else None
                )
            except (ValueError, TypeError):
                new_temp = None

            raw_old_state_temp = old_state.attributes.get(ATTR_TEMPERATURE)
            try:
                old_state_temp = (
                    to_celsius(float(raw_old_state_temp), get_state_temp_unit(old_state), self.hass)
                    if raw_old_state_temp is not None
                    else None
                )
            except (ValueError, TypeError):
                old_state_temp = None

            # 1. Check pending command confirmation FIRST (even if event carries _internal_context!)
            if entity_id in self._pending_trv_targets:
                pending = self._pending_trv_targets[entity_id]
                if new_temp is not None and abs(new_temp - pending) <= 0.55:
                    self._pending_trv_targets.pop(entity_id, None)
                    self._last_known_trv_targets[entity_id] = new_temp
                    health = self.trv_health.setdefault(entity_id, {})
                    sent_mono = health.get("last_command_time_monotonic")
                    latency = round(time.monotonic() - sent_mono, 2) if sent_mono else None
                    health["sync_status"] = "IN_SYNC"
                    health["latency_s"] = latency
                    health["last_ack_time"] = dt_util.now().isoformat()
                    health["last_reported_temp"] = new_temp
                    health["consecutive_timeouts"] = 0
                    self._coordinator.record_diagnostic_event("TRV_CONFIRMED", {
                        "zone": self._zone_name,
                        "trv": entity_id,
                        "target": new_temp,
                        "latency_s": latency,
                    })
                    return None, None

            # 2. Ignore self-generated events that were not pending target confirmations
            event_ctx = getattr(event, "context", None)
            if event_ctx and getattr(event_ctx, "id", None) in (master_context_id, self._internal_context.id):
                return None, None

            if new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                return None, None

            # 3. If still in _pending_trv_targets on an external event:
            #    If target temperature did not change in this state update (e.g. current_temperature report)
            #    and command was sent recently (<30s), keep waiting; otherwise clear pending so physical knob works.
            if entity_id in self._pending_trv_targets:
                health = self.trv_health.get(entity_id, {})
                sent_mono = health.get("last_command_time_monotonic")
                is_recent = sent_mono is not None and (time.monotonic() - sent_mono) < 30.0
                if is_recent and new_temp == old_state_temp:
                    return None, None
                self._pending_trv_targets.pop(entity_id, None)

            raw_old_temp = self._last_known_trv_targets.get(entity_id)
            try:
                old_temp = float(raw_old_temp) if raw_old_temp is not None else old_state_temp
            except (ValueError, TypeError):
                old_temp = old_state_temp

            physical_sync_enabled = self._coordinator.get_persistent_data(self._sync_switch_key, True)

            # Filter network reconnection from unavailable/unknown
            if old_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                if self._authoritative_sync and physical_sync_enabled:
                    if new_state.state == HVACMode.OFF and master_hvac_mode != HVACMode.OFF:
                        if new_temp is not None and new_temp > 7.0:
                            self._last_known_trv_targets[entity_id] = new_temp
                        return HVACMode.OFF, None
                    if new_state.state in (HVACMode.HEAT, "idle", "auto") and master_hvac_mode == HVACMode.OFF:
                        if new_temp is not None and new_temp > 7.0:
                            self._last_known_trv_targets[entity_id] = new_temp
                        if master_hvac_mode in (HVACMode.COOL, "cool"):
                            return None, None
                        return HVACMode.HEAT, None
                if new_temp is not None and new_temp > 7.0:
                    self._last_known_trv_targets[entity_id] = new_temp
                return None, None

            # Normalize "idle" as active heating sub-state (equivalent to HVACMode.HEAT for mode transitions)
            eff_new_mode = HVACMode.HEAT if new_state.state == "idle" else new_state.state
            eff_old_mode = HVACMode.HEAT if old_state.state == "idle" else old_state.state

            if eff_new_mode == HVACMode.OFF and eff_old_mode != HVACMode.OFF:
                if new_temp is not None and new_temp > 7.0 and not self._authoritative_sync:
                    self._last_known_trv_targets[entity_id] = new_temp
                if physical_sync_enabled or self._authoritative_sync:
                    return (HVACMode.OFF if master_hvac_mode != HVACMode.OFF else None), None
                return None, None

            if eff_new_mode == HVACMode.HEAT and eff_old_mode == HVACMode.OFF:
                if new_temp is not None and new_temp > 7.0:
                    self._last_known_trv_targets[entity_id] = new_temp
                if master_hvac_mode in (HVACMode.COOL, "cool"):
                    # TRV turned on during cooling season: force it back to OFF and never switch zone to heat
                    try:
                        await self.hass.services.async_call(
                            "climate",
                            "set_hvac_mode",
                            {"entity_id": entity_id, "hvac_mode": HVACMode.OFF},
                            context=self._internal_context,
                        )
                    except Exception as err:
                        _LOGGER.debug("Failed to force TRV %s to OFF during cooling: %s", entity_id, err)
                    return None, None
                if (physical_sync_enabled or self._authoritative_sync) and master_hvac_mode != HVACMode.HEAT:
                    return HVACMode.HEAT, None
                return None, None

            if not (physical_sync_enabled or self._authoritative_sync) or master_hvac_mode == HVACMode.OFF or eff_new_mode == HVACMode.OFF or eff_old_mode == HVACMode.OFF:
                if new_temp is not None and new_temp > 7.0:
                    self._last_known_trv_targets[entity_id] = new_temp
                return None, None

            if new_temp is not None and old_temp is not None:
                if abs(new_temp - old_temp) > 0.01:
                    delta = new_temp - old_temp
                    self._last_known_trv_targets[entity_id] = new_temp
                    if master_hvac_mode in (HVACMode.COOL, "cool"):
                        # In cooling season, TRV knob delta must not change heating setpoint or turn on heat
                        if eff_new_mode != HVACMode.OFF:
                            try:
                                await self.hass.services.async_call(
                                    "climate",
                                    "set_hvac_mode",
                                    {"entity_id": entity_id, "hvac_mode": HVACMode.OFF},
                                    context=self._internal_context,
                                )
                            except Exception as err:
                                _LOGGER.debug("Failed to force TRV %s to OFF during cooling knob delta: %s", entity_id, err)
                        return None, None
                    self._coordinator.record_diagnostic_event("TRV_KNOB_DELTA", {
                        "zone": self._zone_name,
                        "trv": entity_id,
                        "delta": round(delta, 1),
                        "old_temp": old_temp,
                        "new_temp": new_temp,
                    })
                    return None, delta

            return None, None

    @property
    def local_pwm_state(self) -> bool:
        """Return the current local PWM state."""
        return self._local_pwm_state
