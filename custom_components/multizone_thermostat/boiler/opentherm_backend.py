
from .flow_curve import (
    create_flow_curve_for_emitter,
    EMITTER_RADIATOR,
    EMITTER_UNDERFLOOR,
    EMITTER_FANCOIL,
    UNDERFLOOR_MAX_FLOW_TEMP,
)
"""OpenTherm boiler backend."""
import logging
import time

from homeassistant.core import HomeAssistant
from .base import BoilerBackend
from .valve_readiness import evaluate_trvs_ready
from ..const import DEFAULT_FROST_FLOW_TEMP, KEY_FROST_FLOW_TEMP, to_celsius, from_celsius

_LOGGER = logging.getLogger(__name__)

COMMAND_CONFIRM_TIMEOUT = 60.0  # seconds to wait for entity confirmation

class OpenThermBoilerBackend(BoilerBackend):
    """Handles OpenTherm modulating boilers."""

    is_modulating: bool = True

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator,
        opentherm_entity: str,
        min_temp: float,
        max_temp: float,
        ch_switch: str | None = None,
        valve_delay: int = 0,
    ) -> None:
        """Initialize OpenTherm backend."""
        self.hass = hass
        self.coordinator = coordinator
        self.opentherm_entity = opentherm_entity
        self.opentherm_min_temp = min_temp
        self.opentherm_max_temp = max_temp
        self.ch_switch = ch_switch
        self._valve_delay = int(valve_delay)
        self._trv_wait_start: float | None = None
        self._valve_delay_start: float | None = None
        self._status_reason = "INIT"
        self._pending_command: tuple[str, float] | None = None

    def set_valve_delay(self, value: int) -> None:
        """Set the valve delay time (seconds)."""
        self._valve_delay = int(value)

    @property
    def status_reason(self) -> str:
        """Return the current status reason."""
        return self._status_reason

    def _get_outdoor_temperature(self) -> float | None:
        """Extract outdoor temperature from configured weather sensor."""
        weather_sensor_id = getattr(self.coordinator, "weather_sensor_id", None)
        if not weather_sensor_id or not hasattr(self.hass, "states") or not self.hass.states:
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
                attrs = getattr(w_state, "attributes", None) or {}
                w_unit = (attrs.get("temperature_unit") or attrs.get("unit_of_measurement")) if hasattr(attrs, "get") else None
                return to_celsius(float(raw_t), w_unit, self.hass)
            except (ValueError, TypeError):
                return None
        return None

    def _get_plant_emitter_type(self, peak_zone: str | None = None) -> str:
        """Determine dominant emitter type for water flow calculation."""
        zones = getattr(self.coordinator, "zones", None)
        if not isinstance(zones, list):
            zones = []
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
        """Check if plant has mixed underfloor and high-temperature emitters."""
        zones = getattr(self.coordinator, "zones", None)
        if not isinstance(zones, list):
            return False
        has_underfloor = any(isinstance(z, dict) and z.get("emitter_type") == EMITTER_UNDERFLOOR for z in zones)
        has_high_temp = any(
            isinstance(z, dict) and (z.get("emitter_type") in (EMITTER_RADIATOR, EMITTER_FANCOIL) or z.get("is_fancoil"))
            for z in zones
        )
        return bool(has_underfloor and has_high_temp)

    async def async_update(self, demand: float, peak_zone: str | None, frost_emergency: bool) -> None:
        """Map demand to OpenTherm target temperature."""
        if not self.opentherm_entity:
            return

        st = self.hass.states.get(self.opentherm_entity)
        if st is None or st.state in ("unavailable", "unknown"):
            _LOGGER.debug("OpenTherm entity %s is not available yet, skipping update", self.opentherm_entity)
            return

        # Normalize demand from 0-100 to 0.0-1.0 and clamp
        norm_demand = max(0.0, min(1.0, demand / 100.0))
        wanted_on = norm_demand > 0.0 or frost_emergency

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
        has_mixing = getattr(self.coordinator, "has_mixing_valve", False) is True

        target_temp = self.opentherm_min_temp + (norm_demand * (self.opentherm_max_temp - self.opentherm_min_temp))

        if frost_emergency:
            p_val = self.coordinator.get_persistent_data(KEY_FROST_FLOW_TEMP, None) if hasattr(self.coordinator, "get_persistent_data") else None
            if isinstance(p_val, (int, float)) and not isinstance(p_val, bool):
                frost_flow = float(p_val)
            else:
                raw_ff = getattr(self.coordinator, "frost_flow_temp", None)
                frost_flow = (
                    float(raw_ff)
                    if isinstance(raw_ff, (int, float)) and not isinstance(raw_ff, bool)
                    else DEFAULT_FROST_FLOW_TEMP
                )
            target_temp = max(self.opentherm_min_temp, min(self.opentherm_max_temp, frost_flow))
        elif norm_demand > 0.0 and outdoor_temp is not None and curve_val > 0.0:
            curve = create_flow_curve_for_emitter(
                emitter_type=emitter,
                t_min=self.opentherm_min_temp,
                t_max=self.opentherm_max_temp,
                curve_multiplier=curve_val,
                has_mixing_valve=has_mixing,
                is_mixed_underfloor=self._has_mixed_underfloor(),
            )
            target_temp = curve.flow_for_demand(demand, outdoor_temp)

        if (emitter == EMITTER_UNDERFLOOR or self._has_mixed_underfloor()) and not has_mixing:
            target_temp = min(target_temp, UNDERFLOOR_MAX_FLOW_TEMP)

        target_temp = round(target_temp, 1)

        domain = self.opentherm_entity.split(".")[0]

        _LOGGER.debug("OpenTherm: Demand %.1f%% -> Target Water Temp: %.1f°C", norm_demand * 100, target_temp)

        # Diagnostics track burner flame telemetry; command confirmation tracks entity/switch state
        diag = getattr(self.coordinator, "plant_diagnostics", None)
        entity_confirmed_on = False
        if self.ch_switch:
            sw_st = self.hass.states.get(self.ch_switch)
            entity_confirmed_on = sw_st is not None and sw_st.state == "on"
        else:
            st_check = self.hass.states.get(self.opentherm_entity)
            if domain == "climate":
                entity_confirmed_on = st_check is not None and st_check.state == "heat"
            elif domain == "number":
                if st_check is not None and st_check.state not in ("unavailable", "unknown"):
                    try:
                        val = float(st_check.state)
                        m = float(st_check.attributes.get("min", 0.0)) if st_check.attributes.get("min") is not None else 0.0
                        entity_confirmed_on = val > m
                    except (ValueError, TypeError):
                        entity_confirmed_on = False
            else:
                entity_confirmed_on = st_check is not None and st_check.state not in ("unavailable", "unknown", "off")

        ot_diag = diag.get_opentherm_diagnostics() if diag else {}
        if isinstance(ot_diag, dict) and ot_diag.get("flame_active") is not None:
            burner_on = bool(ot_diag["flame_active"])
        else:
            burner_on = entity_confirmed_on

        if (entity_confirmed_on or burner_on or wanted_on) and hasattr(self.coordinator, "reset_last_active_time"):
            self.coordinator.reset_last_active_time()

        if diag and hasattr(diag, "record_boiler_state"):
            if burner_on and diag._current_boiler_start is None:
                diag.record_boiler_state(True)
            elif not burner_on and diag._current_boiler_start is not None:
                diag.record_boiler_state(False)

        if self._pending_command is not None:
            cmd, ts = self._pending_command
            if (cmd == "on" and entity_confirmed_on) or (cmd == "off" and not entity_confirmed_on):
                self._pending_command = None
            elif time.monotonic() - ts > COMMAND_CONFIRM_TIMEOUT:
                _LOGGER.warning(
                    "OpenTherm entity %s did not confirm '%s' within %ss",
                    self.opentherm_entity,
                    cmd,
                    COMMAND_CONFIRM_TIMEOUT,
                )
                if hasattr(self.coordinator, "record_diagnostic_event"):
                    self.coordinator.record_diagnostic_event(
                        "BOILER_COMMAND_TIMEOUT",
                        {"entity": self.opentherm_entity, "command": cmd},
                    )
                self._pending_command = None

        if wanted_on:
            cold_start = (not entity_confirmed_on and not burner_on)
            if cold_start and not frost_emergency and peak_zone != "Anti-Seize":
                trvs_ready, has_any_trvs = evaluate_trvs_ready(self.hass, self.coordinator)
                if not trvs_ready and has_any_trvs:
                    self._valve_delay_start = None
                    now_mono = time.monotonic()
                    if self._trv_wait_start is None:
                        self._trv_wait_start = now_mono
                    elapsed = now_mono - self._trv_wait_start
                    if elapsed < 120.0:
                        self._status_reason = (
                            f"HOLD_TRV_CLOSED - Waiting for TRVs to open ({round(120.0 - elapsed)}s remaining)"
                        )
                        _LOGGER.warning(
                            "OpenTherm %s: Boiler wants cold start, but demanding TRVs are closed. Waiting (%.0fs/120s)",
                            self.opentherm_entity,
                            elapsed,
                        )
                        return
                    _LOGGER.info(
                        "OpenTherm %s: TRV opening grace period (120s) elapsed. Proceeding with boiler ignition.",
                        self.opentherm_entity,
                    )
                self._trv_wait_start = None

                if self._valve_delay > 0:
                    now_mono = time.monotonic()
                    if self._valve_delay_start is None:
                        self._valve_delay_start = now_mono
                    vd_elapsed = now_mono - self._valve_delay_start
                    if vd_elapsed < self._valve_delay:
                        remaining = round(self._valve_delay - vd_elapsed)
                        self._status_reason = (
                            f"WAITING_VALVES - Valve delay active ({remaining}s remaining)"
                        )
                        _LOGGER.debug(
                            "OpenTherm %s: Waiting %ss for valves to open (%ss remaining)",
                            self.opentherm_entity,
                            self._valve_delay,
                            remaining,
                        )
                        return
                self._valve_delay_start = None
            else:
                self._trv_wait_start = None
                self._valve_delay_start = None

            self._status_reason = f"MODULATING - Target water: {target_temp}°C (Demand: {round(demand, 1)}% from {peak_zone or 'None'})"
        else:
            self._trv_wait_start = None
            self._valve_delay_start = None
            if self._status_reason != "OFF - Emergency/Master OFF":
                self._status_reason = "OFF - No Demand"

        try:
            st = self.hass.states.get(self.opentherm_entity)
            if domain in ["climate", "water_heater"]:
                out_target = round(from_celsius(target_temp, self.hass), 1)
                current_target = st.attributes.get("temperature") if st else None
                if current_target != out_target:
                    await self.hass.services.async_call(
                        domain,
                        "set_temperature",
                        {"entity_id": self.opentherm_entity, "temperature": out_target},
                        blocking=False,
                    )

                # Turn OFF if demand is 0, otherwise HEAT / ON
                if domain == "climate":
                    hvac_mode = "heat" if wanted_on else "off"
                    current_mode = st.state if st else None
                    if current_mode != hvac_mode:
                        self._pending_command = ("off" if hvac_mode == "off" else "on", time.monotonic())
                        await self.hass.services.async_call(
                            "climate",
                            "set_hvac_mode",
                            {"entity_id": self.opentherm_entity, "hvac_mode": hvac_mode},
                            blocking=False,
                        )
                elif domain == "water_heater":
                    current_state = st.state if st else None
                    if not wanted_on and current_state not in ("off", None):
                        self._pending_command = ("off", time.monotonic())
                        await self.hass.services.async_call(
                            "water_heater",
                            "turn_off",
                            {"entity_id": self.opentherm_entity},
                            blocking=False,
                        )
                    elif wanted_on and current_state == "off":
                        self._pending_command = ("on", time.monotonic())
                        await self.hass.services.async_call(
                            "water_heater",
                            "turn_on",
                            {"entity_id": self.opentherm_entity},
                            blocking=False,
                        )
            elif domain == "number":
                heat_enabled = wanted_on
                num_unit = st.attributes.get("unit_of_measurement") if (st and getattr(st, "attributes", None)) else None
                value = target_temp
                if num_unit is not None and str(num_unit).strip().lower() in ("°f", "f", "fahrenheit"):
                    value = round(from_celsius(target_temp, unit=num_unit), 1)
                ch_st = (
                    self.hass.states.get(self.ch_switch)
                    if (self.ch_switch and hasattr(self.hass, "states") and self.hass.states)
                    else None
                )
                ch_unavailable = bool(
                    self.ch_switch
                    and (ch_st is None or getattr(ch_st, "state", None) in (None, "unavailable", "unknown"))
                )
                if not heat_enabled and (not self.ch_switch or ch_unavailable):
                    # Drop flow setpoint to minimum whenever CH switch is absent or unavailable
                    entity_min = st.attributes.get("min") if st else None
                    try:
                        value = float(entity_min) if entity_min is not None else 0.0
                    except (ValueError, TypeError):
                        value = 0.0
                    value = min(value, target_temp)
                    self._status_reason = f"OFF - Heating request disabled (setpoint {value}°C)"
                try:
                    current_val = float(st.state) if st and st.state not in ("unknown", "unavailable") else None
                except (ValueError, TypeError):
                    current_val = None
                target_temp = value
                if current_val != target_temp:
                    self._pending_command = ("on" if heat_enabled else "off", time.monotonic())
                    await self.hass.services.async_call(
                        "number",
                        "set_value",
                        {"entity_id": self.opentherm_entity, "value": target_temp},
                        blocking=False,
                    )

            await self._async_set_ch_enabled(wanted_on)
        except Exception as err:
            _LOGGER.error("Failed to update OpenTherm entity %s: %s", self.opentherm_entity, err)

    async def _async_set_ch_enabled(self, enabled: bool) -> None:
        """Drive the optional CH-enable switch (true OFF), only when its state differs."""
        if not self.ch_switch:
            return
        st = self.hass.states.get(self.ch_switch)
        st_val = getattr(st, "state", None) if st is not None else None
        if enabled and (st is None or st_val in ("unavailable", "unknown")):
            _LOGGER.debug("CH switch %s is not available yet, skipping command", self.ch_switch)
            return
        current_on = (st_val == "on") if (st is not None and st_val not in ("unavailable", "unknown")) else None
        if current_on == enabled:
            return
        self._pending_command = ("on" if enabled else "off", time.monotonic())
        await self.hass.services.async_call(
            "switch",
            "turn_on" if enabled else "turn_off",
            {"entity_id": self.ch_switch},
            blocking=False,
        )
        if not enabled:
            self._status_reason = "OFF - Heating request disabled (CH switch off)"

    async def async_emergency_off(self) -> None:
        """Force OpenTherm boiler off immediately."""
        self._trv_wait_start = None
        self._valve_delay_start = None
        self._status_reason = "OFF - Emergency/Master OFF"
        await self.async_update(0.0, None, False)
