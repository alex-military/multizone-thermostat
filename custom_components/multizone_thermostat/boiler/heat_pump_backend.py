from __future__ import annotations
import math

from .flow_curve import (
    create_flow_curve_for_emitter,
    EMITTER_RADIATOR,
    EMITTER_UNDERFLOOR,
    EMITTER_FANCOIL,
)
"""Central Heat Pump (PDC) Backend for Multizone Thermostat (Phase 11).

Single Responsibility: Drives the centralized hydronic Heat Pump (via HA Climate entity,
Switch / SG-Ready relay, or OpenTherm/Number flow temperature modulation) in both
Heating and Reversible Cooling modes.
"""

import logging
import time
from typing import Any

from homeassistant.core import HomeAssistant
from .base import BoilerBackend
from ..const import (
    HP_TYPE_CLIMATE,
    HP_TYPE_SWITCH,
    HP_TYPE_OPENTHERM,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    HVAC_MODE_OFF,
)

HP_TYPE_WATER_HEATER = "water_heater"

_LOGGER = logging.getLogger(__name__)


class CentralHeatPumpBackend(BoilerBackend):
    """Handles centralized hydronic Heat Pump (PDC) actuation."""

    is_modulating: bool = True

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: Any,
        hp_type: str,
        hp_entity: str | None,
        min_temp: float = 25.0,
        max_temp: float = 55.0,
        ch_switch: str | None = None,
        reversible_cooling: bool = True,
        cool_min_temp: float = 7.0,
        cool_max_temp: float = 18.0,
        valve_delay: int = 0,
    ) -> None:
        """Initialize Central Heat Pump backend."""
        self.hass = hass
        self.coordinator = coordinator
        self.hp_type = hp_type or HP_TYPE_CLIMATE
        self.hp_entity = hp_entity
        self.min_temp = float(min_temp if min_temp is not None else 25.0)
        self.max_temp = float(max_temp if max_temp is not None else 55.0)
        self.cool_min_temp = float(cool_min_temp if cool_min_temp is not None else 7.0)
        self.cool_max_temp = float(cool_max_temp if cool_max_temp is not None else 18.0)
        self.valve_delay = int(valve_delay)
        self.ch_switch = ch_switch
        self.reversible_cooling = bool(reversible_cooling)
        self._status_reason = "INIT"
        self._last_state_on: bool | None = None
        self._valve_delay_start: float | None = None
        # Anti-short-cycle guards (L3 / ORACLE-3)
        coord_min_on = getattr(coordinator, "_min_cycle_on", 0.0)
        self.min_cycle_on: float = float(coord_min_on if isinstance(coord_min_on, (int, float)) else 0.0)
        coord_min_off = getattr(coordinator, "_min_cycle_off", 0.0)
        self.min_cycle_off: float = float(coord_min_off if isinstance(coord_min_off, (int, float)) else 0.0)
        self._last_switch_time: float = 0.0
        self._current_running_state: bool = False

    def _is_currently_on(self, entity_id: str | None = None) -> bool:
        """Check if target entity is currently considered ON."""
        ent = entity_id or self.hp_entity
        if not ent or not hasattr(self.hass, "states") or not self.hass.states:
            return False
        st = self.hass.states.get(ent)
        if not st or st.state in ("unavailable", "unknown", "off", None):
            return False
        domain = ent.split(".")[0] if "." in ent else self.hp_type
        if domain == "switch":
            return st.state == "on"
        if domain in ("number", "input_number"):
            try:
                val = float(st.state)
                min_attr = st.attributes.get("min") if getattr(st, "attributes", None) else None
                min_val = float(min_attr) if min_attr is not None else 0.0
                return val > min_val
            except (ValueError, TypeError):
                return False
        if domain == "climate":
            return st.state not in (HVAC_MODE_OFF, "off")
        if domain == "water_heater":
            return st.state != "off"
        return st.state not in ("off", "0", "0.0")

    def set_valve_delay(self, value: int | float) -> None:
        """Set valve delay in seconds."""
        self.valve_delay = int(value)

    @property
    def status_reason(self) -> str:
        """Return the current status reason."""
        return self._status_reason

    async def _async_set_number(self, st: Any, wanted_on: bool, target_temp: float) -> None:
        """Actuate number or input_number entity with min-value protection on turn off."""
        domain = self.hp_entity.split(".")[0] if "." in (self.hp_entity or "") else "number"
        target_domain = domain if domain in ("number", "input_number") else "number"
        if wanted_on:
            val = target_temp
        else:
            val = 0.0
            if st and getattr(st, "attributes", None):
                min_attr = st.attributes.get("min")
                if min_attr is not None:
                    try:
                        min_val = float(min_attr)
                        if min_val > 0.0:
                            val = min_val
                    except (ValueError, TypeError):
                        pass

        current_val = None
        if st and st.state not in ("unavailable", "unknown", None):
            try:
                current_val = float(st.state)
            except (ValueError, TypeError):
                current_val = None
        if current_val != val:
            await self.hass.services.async_call(
                target_domain,
                "set_value",
                {"entity_id": self.hp_entity, "value": val},
                blocking=False,
            )

    async def _async_set_climate_power(
        self, st: Any, wanted_on: bool, target_temp: float, hvac_mode: str
    ) -> None:
        """Actuate climate or water_heater entity with power and setpoint logic."""
        domain = self.hp_entity.split(".")[0] if "." in (self.hp_entity or "") else self.hp_type
        is_water_heater = (domain == "water_heater" or self.hp_type == HP_TYPE_WATER_HEATER)
        svc_domain = "water_heater" if is_water_heater else "climate"

        if is_water_heater:
            if wanted_on:
                current_target = st.attributes.get("temperature") if (st and getattr(st, "attributes", None)) else None
                if current_target != target_temp:
                    await self.hass.services.async_call(
                        "water_heater",
                        "set_temperature",
                        {"entity_id": self.hp_entity, "temperature": target_temp},
                        blocking=False,
                    )
                operation_modes = st.attributes.get("operation_list", []) if (st and getattr(st, "attributes", None)) else []
                current_op = st.state if st else None
                if current_op == "off" and operation_modes:
                    for target_mode in ("heat_pump", "eco", "electric", "performance"):
                        if target_mode in operation_modes:
                            await self.hass.services.async_call(
                                "water_heater",
                                "set_operation_mode",
                                {"entity_id": self.hp_entity, "operation_mode": target_mode},
                                blocking=False,
                            )
                            break
                    else:
                        non_off = [m for m in operation_modes if m != "off"]
                        if non_off:
                            await self.hass.services.async_call(
                                "water_heater",
                                "set_operation_mode",
                                {"entity_id": self.hp_entity, "operation_mode": non_off[0]},
                                blocking=False,
                            )
            else:
                # wanted_on == False: turn off or reduce setpoint
                operation_modes = st.attributes.get("operation_list", []) if (st and getattr(st, "attributes", None)) else []
                if "off" in operation_modes:
                    if st and st.state != "off":
                        await self.hass.services.async_call(
                            "water_heater",
                            "set_operation_mode",
                            {"entity_id": self.hp_entity, "operation_mode": "off"},
                            blocking=False,
                        )
                else:
                    min_t = self.min_temp
                    if st and getattr(st, "attributes", None) and st.attributes.get("min_temp") is not None:
                        try:
                            min_t = float(st.attributes["min_temp"])
                        except (ValueError, TypeError):
                            pass
                    current_target = st.attributes.get("temperature") if (st and getattr(st, "attributes", None)) else None
                    if current_target != min_t:
                        await self.hass.services.async_call(
                            "water_heater",
                            "set_temperature",
                            {"entity_id": self.hp_entity, "temperature": min_t},
                            blocking=False,
                        )
            return

        # Climate domain
        if wanted_on:
            current_target = st.attributes.get("temperature") if (st and getattr(st, "attributes", None)) else None
            if current_target != target_temp:
                await self.hass.services.async_call(
                    "climate",
                    "set_temperature",
                    {"entity_id": self.hp_entity, "temperature": target_temp},
                    blocking=False,
                )
        desired_hvac = (
            HVAC_MODE_OFF
            if not wanted_on
            else (HVAC_MODE_COOL if hvac_mode in (HVAC_MODE_COOL, "cool") else HVAC_MODE_HEAT)
        )
        current_mode = st.state if st else None
        if current_mode != desired_hvac:
            await self.hass.services.async_call(
                "climate",
                "set_hvac_mode",
                {"entity_id": self.hp_entity, "hvac_mode": desired_hvac},
                blocking=False,
            )

    def _get_outdoor_temperature(self) -> float | None:
        """Extract outdoor temperature from configured weather sensor."""
        weather_sensor_id = getattr(self.coordinator, "weather_sensor_id", None)
        if not weather_sensor_id or not isinstance(weather_sensor_id, str) or not hasattr(self.hass, "states") or not self.hass.states:
            return None
        w_state = self.hass.states.get(weather_sensor_id)
        if not w_state or getattr(w_state, "state", None) in (None, "unavailable", "unknown"):
            return None
        if getattr(w_state, "domain", None) == "weather" or str(weather_sensor_id).startswith("weather."):
            raw_t = w_state.attributes.get("temperature") if getattr(w_state, "attributes", None) else None
        else:
            raw_t = w_state.state
        if isinstance(raw_t, (int, float, str)):
            try:
                return float(raw_t)
            except (ValueError, TypeError):
                return None
        return None

    def _get_plant_emitter_type(self, peak_zone: str | None = None) -> str:
        """Determine dominant emitter type."""
        zones = getattr(self.coordinator, "zones", [])
        if peak_zone:
            for z in zones:
                if z.get("name") == peak_zone or z.get("zone_name") == peak_zone:
                    if z.get("emitter_type"):
                        return str(z.get("emitter_type"))
                    if z.get("is_fancoil"):
                        return EMITTER_FANCOIL
        for z in zones:
            if z.get("emitter_type") == EMITTER_UNDERFLOOR:
                return EMITTER_UNDERFLOOR
        for z in zones:
            if z.get("emitter_type") == EMITTER_FANCOIL or z.get("is_fancoil"):
                return EMITTER_FANCOIL
        return EMITTER_RADIATOR

    def _has_mixed_underfloor(self) -> bool:
        """Check if plant has mixed underfloor and high-temp emitters."""
        zones = getattr(self.coordinator, "zones", [])
        has_underfloor = any(z.get("emitter_type") == EMITTER_UNDERFLOOR for z in zones)
        has_high_temp = any(
            z.get("emitter_type") in (EMITTER_RADIATOR, EMITTER_FANCOIL) or z.get("is_fancoil")
            for z in zones
        )
        return has_underfloor and has_high_temp

    def _calculate_safe_cooling_min_temp(self) -> float:
        """Calculate safe minimum cooling water temperature to prevent condensation (L4)."""
        safe_floor = self.cool_min_temp

        # If plant includes underfloor cooling, never drop below 17°C by default
        if self._has_mixed_underfloor() or self._get_plant_emitter_type() == EMITTER_UNDERFLOOR:
            safe_floor = max(safe_floor, 17.0)

        # Check weather or zone humidity sensor for real dew-point calculation (Magnus formula)
        weather_sensor_id = getattr(self.coordinator, "weather_sensor_id", None)
        if weather_sensor_id and hasattr(self.hass, "states") and self.hass.states:
            w_st = self.hass.states.get(weather_sensor_id)
            if w_st and getattr(w_st, "attributes", None):
                rh = w_st.attributes.get("humidity")
                temp = w_st.attributes.get("temperature")
                if isinstance(rh, (int, float)) and isinstance(temp, (int, float)) and float(rh) > 10.0:
                    t = float(temp)
                    h = float(rh)
                    try:
                        a, b = 17.27, 237.7
                        alpha = ((a * t) / (b + t)) + math.log(max(1.0, min(100.0, h)) / 100.0)
                        dew_point = (b * alpha) / (a - alpha)
                        # Water temperature must remain at least 2.0°C above dew point
                        safe_floor = max(safe_floor, round(dew_point + 2.0, 1))
                    except Exception:
                        pass
        return safe_floor

    async def async_update(
        self,
        demand: float,
        peak_zone: str | None,
        frost_emergency: bool,
        hvac_mode: str = HVAC_MODE_HEAT,
    ) -> None:
        """Actuate the central Heat Pump according to aggregate demand and HVAC mode."""
        if not self.hp_entity:
            return

        if (hvac_mode in (HVAC_MODE_COOL, "cool")) and not self.reversible_cooling:
            demand = 0.0

        norm_demand = max(0.0, min(1.0, float(demand) / 100.0))
        wanted_on = norm_demand > 0.0

        domain = self.hp_entity.split(".")[0] if "." in self.hp_entity else self.hp_type
        st = self.hass.states.get(self.hp_entity) if hasattr(self.hass, "states") and self.hass.states else None

        # Anti-short-cycling guard for heat pump compressor (L3 / ORACLE-3)
        now = time.monotonic()
        elapsed = now - self._last_switch_time if self._last_switch_time > 0 else 99999.0

        if wanted_on and not self._current_running_state:
            if elapsed < self.min_cycle_off and not frost_emergency:
                rem = self.min_cycle_off - elapsed
                self._status_reason = f"HOLD_OFF - PDC anti-short-cycle: {rem:.0f}s"
                wanted_on = False
            else:
                self._last_switch_time = now
                self._current_running_state = True
        elif not wanted_on and self._current_running_state:
            if elapsed < self.min_cycle_on and not frost_emergency:
                rem = self.min_cycle_on - elapsed
                self._status_reason = f"HOLD_ON - PDC min run time: {rem:.0f}s"
                wanted_on = True
            else:
                self._last_switch_time = now
                self._current_running_state = False

        if hvac_mode in (HVAC_MODE_COOL, "cool"):
            # In cooling mode: apply dew point condensation protection (L4)
            safe_cool_min = self._calculate_safe_cooling_min_temp()
            target_temp = round(self.cool_max_temp - norm_demand * (self.cool_max_temp - safe_cool_min), 1)
            target_temp = max(target_temp, safe_cool_min)
        else:
            # In heating mode, use FlowCurve with emitter calibration
            raw_curve = (
                self.coordinator.get_persistent_data("weather_curve", 1.0)
                if hasattr(self.coordinator, "get_persistent_data")
                else 1.0
            )
            try:
                curve_val = float(raw_curve) if raw_curve not in (None, "") else 1.0
            except (ValueError, TypeError):
                curve_val = 1.0

            outdoor_temp = self._get_outdoor_temperature()
            emitter = self._get_plant_emitter_type(peak_zone)
            has_mixing = bool(getattr(self.coordinator, "has_mixing_valve", False))

            curve = create_flow_curve_for_emitter(
                emitter_type=emitter,
                t_min=self.min_temp,
                t_max=self.max_temp,
                curve_multiplier=curve_val,
                has_mixing_valve=has_mixing,
                is_mixed_underfloor=self._has_mixed_underfloor(),
            )

            if frost_emergency:
                frost_flow = float(getattr(self.coordinator, "frost_flow_temp", 40.0))
                target_temp = max(self.min_temp, min(curve.t_max, frost_flow))
            elif outdoor_temp is not None:
                target_temp = curve.flow_for_demand(demand, outdoor_temp)
            else:
                target_temp = self.min_temp + norm_demand * (self.max_temp - self.min_temp)
            target_temp = round(target_temp, 1)

        if wanted_on:
            if self.valve_delay > 0 and not self._is_currently_on(self.hp_entity):
                now_mono = time.monotonic()
                if self._valve_delay_start is None:
                    self._valve_delay_start = now_mono
                elapsed = now_mono - self._valve_delay_start
                if elapsed < self.valve_delay:
                    remaining = round(self.valve_delay - elapsed)
                    self._status_reason = f"WAITING_VALVES - Valve delay active ({remaining}s remaining)"
                    _LOGGER.debug(
                        "HeatPump %s: Waiting %ss for valves to open (%.1fs/%ss elapsed)",
                        self.hp_entity,
                        self.valve_delay,
                        elapsed,
                        self.valve_delay,
                    )
                    return
            self._valve_delay_start = None
            if not self._status_reason.startswith("HOLD_"):
                self._status_reason = (
                    f"HP_{hvac_mode.upper()} - Target: {target_temp}°C "
                    f"(Demand: {round(demand, 1)}% from {peak_zone or 'None'})"
                )
        else:
            self._valve_delay_start = None
            if not self._status_reason.startswith("HOLD_"):
                self._status_reason = "OFF - No Demand"

        diag = getattr(self.coordinator, "plant_diagnostics", None)
        confirmed_hp_on = bool(self._current_running_state)
        if diag:
            if hasattr(diag, "record_generator_state"):
                diag.record_generator_state("heat_pump", confirmed_hp_on)
            elif hasattr(diag, "record_boiler_state") and not getattr(self.coordinator, "enable_gas_heater", False):
                diag.record_boiler_state(confirmed_hp_on)

        try:
            if domain == "switch" or self.hp_type == HP_TYPE_SWITCH:
                current_on = (st.state == "on") if st else None
                if current_on != wanted_on:
                    await self.hass.services.async_call(
                        "switch",
                        "turn_on" if wanted_on else "turn_off",
                        {"entity_id": self.hp_entity},
                        blocking=False,
                    )
            elif domain in ("climate", "water_heater") or self.hp_type in (HP_TYPE_CLIMATE, HP_TYPE_WATER_HEATER):
                await self._async_set_climate_power(st, wanted_on, target_temp, hvac_mode)
            elif domain in ("number", "input_number") or self.hp_type == HP_TYPE_OPENTHERM:
                await self._async_set_number(st, wanted_on, target_temp)

            if self.ch_switch:
                sw_st = self.hass.states.get(self.ch_switch) if hasattr(self.hass, "states") and self.hass.states else None
                sw_on = (sw_st.state == "on") if sw_st else None
                if sw_on != wanted_on:
                    await self.hass.services.async_call(
                        "switch",
                        "turn_on" if wanted_on else "turn_off",
                        {"entity_id": self.ch_switch},
                        blocking=False,
                    )
        except Exception as err:
            _LOGGER.error("Failed to update Central Heat Pump entity %s: %s", self.hp_entity, err)

    async def async_emergency_off(self) -> None:
        """Force Central Heat Pump off immediately."""
        self._current_running_state = False
        self._last_switch_time = 0.0
        self._valve_delay_start = None
        self._status_reason = "OFF - Emergency/Master OFF"
        await self.async_update(0.0, None, False, HVAC_MODE_OFF)
