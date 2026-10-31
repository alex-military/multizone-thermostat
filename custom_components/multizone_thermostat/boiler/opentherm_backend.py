"""OpenTherm boiler backend."""
import logging
import time

from homeassistant.core import HomeAssistant
from .base import BoilerBackend

_LOGGER = logging.getLogger(__name__)

COMMAND_CONFIRM_TIMEOUT = 60.0  # seconds to wait for entity confirmation

class OpenThermBoilerBackend(BoilerBackend):
    """Handles OpenTherm modulating boilers."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator,
        opentherm_entity: str,
        min_temp: float,
        max_temp: float,
        ch_switch: str | None = None,
    ) -> None:
        """Initialize OpenTherm backend."""
        self.hass = hass
        self.coordinator = coordinator
        self.opentherm_entity = opentherm_entity
        self.opentherm_min_temp = min_temp
        self.opentherm_max_temp = max_temp
        self.ch_switch = ch_switch
        self._status_reason = "INIT"
        self._pending_command: tuple[str, float] | None = None

    @property
    def status_reason(self) -> str:
        """Return the current status reason."""
        return self._status_reason

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
        wanted_on = norm_demand > 0.0

        target_temp = self.opentherm_min_temp + (norm_demand * (self.opentherm_max_temp - self.opentherm_min_temp))

        if norm_demand > 0.0 and not frost_emergency:
            weather_sensor_id = getattr(self.coordinator, "weather_sensor_id", None)
            if isinstance(weather_sensor_id, str) and weather_sensor_id and hasattr(self.coordinator, "get_persistent_data"):
                raw_curve = self.coordinator.get_persistent_data("weather_curve", 0.0)
                try:
                    curve_val = float(raw_curve) if isinstance(raw_curve, (int, float, str)) and raw_curve != "" else 0.0
                except (ValueError, TypeError):
                    curve_val = 0.0
                if curve_val > 0.0:
                    w_state = self.hass.states.get(weather_sensor_id)
                    outdoor_temp = None
                    if w_state and getattr(w_state, "state", None) not in (None, "unavailable", "unknown"):
                        if getattr(w_state, "domain", None) == "weather" or str(weather_sensor_id).startswith("weather."):
                            raw_t = w_state.attributes.get("temperature") if getattr(w_state, "attributes", None) else None
                        else:
                            raw_t = w_state.state
                        if isinstance(raw_t, (int, float, str)):
                            try:
                                outdoor_temp = float(raw_t)
                            except (ValueError, TypeError):
                                outdoor_temp = None
                    if outdoor_temp is not None and outdoor_temp < 15.0:
                        delta_ext = 15.0 - outdoor_temp
                        thermal_models = getattr(self.coordinator, "_thermal_models", {})
                        valid_rates = []
                        if isinstance(thermal_models, dict):
                            for m in thermal_models.values():
                                cr = getattr(m, "cooling_rate", None)
                                if isinstance(cr, (int, float)) and float(cr) > 0.05:
                                    valid_rates.append(float(cr))
                        if valid_rates:
                            avg_cooling_rate = sum(valid_rates) / len(valid_rates)
                            retention_factor = min(1.5, max(0.8, 1.0 + (avg_cooling_rate - 0.2)))
                        else:
                            retention_factor = 1.0
                        weather_flow_offset = min(15.0, max(0.0, delta_ext * curve_val * 0.5 * retention_factor))
                        target_temp = max(
                            self.opentherm_min_temp,
                            min(self.opentherm_max_temp, target_temp + weather_flow_offset),
                        )

        target_temp = round(target_temp, 1)

        domain = self.opentherm_entity.split(".")[0]

        _LOGGER.debug("OpenTherm: Demand %.1f%% -> Target Water Temp: %.1f°C", norm_demand * 100, target_temp)

        # Diagnostics follow the CONFIRMED entity/flame state, not the commanded demand
        diag = getattr(self.coordinator, "plant_diagnostics", None)
        confirmed_on = False
        ot_diag = diag.get_opentherm_diagnostics() if diag else {}
        if ot_diag.get("flame_active") is not None:
            confirmed_on = bool(ot_diag["flame_active"])
        elif self.ch_switch:
            sw_st = self.hass.states.get(self.ch_switch)
            confirmed_on = sw_st is not None and sw_st.state == "on"
        else:
            st_check = self.hass.states.get(self.opentherm_entity)
            if domain == "climate":
                confirmed_on = st_check is not None and st_check.state == "heat"
            elif domain == "number":
                if st_check is not None and st_check.state not in ("unavailable", "unknown"):
                    try:
                        val = float(st_check.state)
                        m = float(st_check.attributes.get("min", 0.0)) if st_check.attributes.get("min") is not None else 0.0
                        confirmed_on = val > m
                    except (ValueError, TypeError):
                        confirmed_on = False
            else:
                confirmed_on = st_check is not None and st_check.state not in ("unavailable", "unknown", "off")

        if (confirmed_on or wanted_on) and hasattr(self.coordinator, "reset_last_active_time"):
            self.coordinator.reset_last_active_time()

        if diag:
            if confirmed_on and diag._current_boiler_start is None:
                diag.record_boiler_state(True)
            elif not confirmed_on and diag._current_boiler_start is not None:
                diag.record_boiler_state(False)

        if self._pending_command is not None:
            cmd, ts = self._pending_command
            if (cmd == "on" and confirmed_on) or (cmd == "off" and not confirmed_on):
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

        if norm_demand > 0.0:
            self._status_reason = f"MODULATING - Target water: {target_temp}°C (Demand: {round(demand, 1)}% from {peak_zone or 'None'})"
        elif self._status_reason != "OFF - Emergency/Master OFF":
            self._status_reason = "OFF - No Demand"

        try:
            st = self.hass.states.get(self.opentherm_entity)
            if domain in ["climate", "water_heater"]:
                current_target = st.attributes.get("temperature") if st else None
                if current_target != target_temp:
                    await self.hass.services.async_call(
                        domain,
                        "set_temperature",
                        {"entity_id": self.opentherm_entity, "temperature": target_temp},
                        blocking=False,
                    )

                # Turn OFF if demand is 0, otherwise HEAT / ON
                if domain == "climate":
                    hvac_mode = "off" if norm_demand <= 0.0 else "heat"
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
                    if norm_demand <= 0.0 and current_state not in ("off", None):
                        self._pending_command = ("off", time.monotonic())
                        await self.hass.services.async_call(
                            "water_heater",
                            "turn_off",
                            {"entity_id": self.opentherm_entity},
                            blocking=False,
                        )
                    elif norm_demand > 0.0 and current_state == "off":
                        self._pending_command = ("on", time.monotonic())
                        await self.hass.services.async_call(
                            "water_heater",
                            "turn_on",
                            {"entity_id": self.opentherm_entity},
                            blocking=False,
                        )
            elif domain == "number":
                heat_enabled = norm_demand > 0.0
                value = target_temp
                if not heat_enabled and not self.ch_switch:
                    # A bare number entity has no OFF command: write the lowest value the
                    # entity accepts (normally 0 = CH disabled) instead of the min flow temp.
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

            await self._async_set_ch_enabled(norm_demand > 0.0)
        except Exception as err:
            _LOGGER.error("Failed to update OpenTherm entity %s: %s", self.opentherm_entity, err)

    async def _async_set_ch_enabled(self, enabled: bool) -> None:
        """Drive the optional CH-enable switch (true OFF), only when its state differs."""
        if not self.ch_switch:
            return
        st = self.hass.states.get(self.ch_switch)
        if st is None or st.state in ("unavailable", "unknown"):
            _LOGGER.debug("CH switch %s is not available yet, skipping command", self.ch_switch)
            return
        current_on = st.state == "on" if st else None
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
        self._status_reason = "OFF - Emergency/Master OFF"
        await self.async_update(0.0, None, False)
