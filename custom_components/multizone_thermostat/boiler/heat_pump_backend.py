"""Central Heat Pump (PDC) Backend for Multizone Thermostat (Phase 11).

Single Responsibility: Drives the centralized hydronic Heat Pump (via HA Climate entity,
Switch / SG-Ready relay, or OpenTherm/Number flow temperature modulation) in both
Heating and Reversible Cooling modes.
"""
from __future__ import annotations

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

        if hvac_mode in (HVAC_MODE_COOL, "cool"):
            # In cooling mode, higher demand lowers water temp toward cool_min_temp
            target_temp = round(self.cool_max_temp - norm_demand * (self.cool_max_temp - self.cool_min_temp), 1)
        else:
            # In heating mode, higher demand raises water temp toward max_temp
            target_temp = round(self.min_temp + norm_demand * (self.max_temp - self.min_temp), 1)

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
            self._status_reason = (
                f"HP_{hvac_mode.upper()} - Target: {target_temp}°C "
                f"(Demand: {round(demand, 1)}% from {peak_zone or 'None'})"
            )
        else:
            self._valve_delay_start = None
            self._status_reason = "OFF - No Demand"

        diag = getattr(self.coordinator, "plant_diagnostics", None)
        if diag and hasattr(diag, "record_boiler_state"):
            if wanted_on and getattr(diag, "_current_boiler_start", None) is None:
                diag.record_boiler_state(True)
            elif not wanted_on and getattr(diag, "_current_boiler_start", None) is not None:
                diag.record_boiler_state(False)

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
        self._valve_delay_start = None
        self._status_reason = "OFF - Emergency/Master OFF"
        await self.async_update(0.0, None, False, HVAC_MODE_OFF)
