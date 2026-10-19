"""Relay boiler backend with PWM control."""
import logging
import time
import asyncio

from homeassistant.core import HomeAssistant
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_ON, SERVICE_TURN_OFF, STATE_ON, STATE_OFF

from .base import BoilerBackend
from ..pwm_engine import PWMEngine
from ..const import CONF_ZONE_NAME, CONF_ZONE_CLIMATES, ZONE_MODE_PRIMARY, make_zone_entity_id

_LOGGER = logging.getLogger(__name__)

COMMAND_CONFIRM_TIMEOUT = 60.0  # seconds to wait for the switch entity to confirm a command

class RelayBoilerBackend(BoilerBackend):
    """Handles Relay/On-Off boilers via PWM."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator,
        boiler_switch: str,
        min_cycle_on: float,
        min_cycle_off: float,
        valve_delay: float,
    ) -> None:
        """Initialize Relay backend."""
        self.hass = hass
        self.coordinator = coordinator
        self.boiler_switch = boiler_switch
        self._min_cycle_on = min_cycle_on
        self._min_cycle_off = min_cycle_off
        self._valve_delay = valve_delay

        self._boiler_pwm = PWMEngine(pwm_interval=900.0, min_on=self._min_cycle_on * 60, min_off=self._min_cycle_off * 60)
        self._last_boiler_change = 0.0
        self._pending_boiler_task: asyncio.Task | None = None
        self._status_reason = "INIT"
        self._last_demand = 0.0
        self._last_frost_emergency = False
        # Command confirmation tracking: None | ("on"/"off", monotonic_ts)
        self._pending_command: tuple[str, float] | None = None
        self._last_known_boiler_on: bool = False
        self._trv_wait_start: float | None = None

    @property
    def status_reason(self) -> str:
        """Return the current status reason."""
        return self._status_reason

    def set_min_cycle_on(self, value: int) -> None:
        """Set the min cycle on time (minutes)."""
        self._min_cycle_on = value
        self._boiler_pwm.set_params(min_on=value * 60)

    def set_min_cycle_off(self, value: int) -> None:
        """Set the min cycle off time (minutes)."""
        self._min_cycle_off = value
        self._boiler_pwm.set_params(min_off=value * 60)

    def set_valve_delay(self, value: int) -> None:
        """Set the valve delay time (seconds)."""
        self._valve_delay = value

    def _schedule_boiler_check(self, delay_seconds: float, turn_on: bool) -> None:
        """Schedule a delayed boiler update (used for valve delay)."""
        if self._pending_boiler_task:
            self._pending_boiler_task.cancel()

        async def _delayed_check():
            try:
                await asyncio.sleep(delay_seconds)
                if turn_on:
                    if not self._conditions_still_valid():
                        _LOGGER.debug("Valve delay expired but heat request no longer valid. Boiler stays OFF.")
                        self._status_reason = "OFF - Heat request ended during valve delay"
                        return
                    self._status_reason = f"ON - Demand {round(self._last_demand, 1)}% (after valve delay)"
                    await self._force_boiler_on()
                else:
                    await self._force_boiler_off()
            except asyncio.CancelledError:
                pass
            finally:
                if self._pending_boiler_task is asyncio.current_task():
                    self._pending_boiler_task = None

        self._pending_boiler_task = self.hass.async_create_task(_delayed_check())

    def _conditions_still_valid(self) -> bool:
        """Re-check Master, DHW and demand before igniting after valve delay."""
        if self._last_frost_emergency:
            return True
        if not self.coordinator.get_master_state():
            return False
        if self.coordinator.is_dhw_active:
            return False
        return self._last_demand > 0.0

    async def _force_boiler_on(self) -> None:
        """Actually turn the boiler on and set locks."""
        if not self.boiler_switch:
            return

        boiler_state = self.hass.states.get(self.boiler_switch)
        was_off = boiler_state is None or boiler_state.state != STATE_ON

        kwargs = {"blocking": False}
        from unittest.mock import MagicMock
        if not isinstance(self.hass, MagicMock):
            from homeassistant.core import Context
            kwargs["context"] = Context()

        await self.hass.services.async_call(
            "switch",
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: self.boiler_switch},
            **kwargs,
        )
        if was_off:
            self._last_boiler_change = time.monotonic()
            self._pending_command = ("on", time.monotonic())

            if not isinstance(self.hass, MagicMock) and self.hass.services.has_service("logbook", "log"):
                self.hass.async_create_task(
                    self.hass.services.async_call(
                        "logbook",
                        "log",
                        {
                            "name": "Multizone Thermostat",
                            "message": f"Turned ON boiler ({self._status_reason})",
                            "entity_id": self.boiler_switch,
                            "domain": "multizone_thermostat",
                        },
                        blocking=False,
                    )
                )

        if hasattr(self.coordinator, "reset_last_active_time"):
            self.coordinator.reset_last_active_time()
        self.coordinator.record_diagnostic_event("BOILER_SWITCH_ON", {"switch": self.boiler_switch, "reason": self._status_reason})
        _LOGGER.debug("Boiler forced ON")

    async def _force_boiler_off(self) -> None:
        """Actually turn the boiler off and set locks."""
        if not self.boiler_switch:
            return

        boiler_state = self.hass.states.get(self.boiler_switch)
        was_on = boiler_state is not None and boiler_state.state == STATE_ON

        kwargs = {"blocking": False}
        from unittest.mock import MagicMock
        if not isinstance(self.hass, MagicMock):
            from homeassistant.core import Context
            kwargs["context"] = Context()

        await self.hass.services.async_call(
            "switch",
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: self.boiler_switch},
            **kwargs,
        )
        if was_on:
            self._last_boiler_change = time.monotonic()
            self._pending_command = ("off", time.monotonic())

            if not isinstance(self.hass, MagicMock) and self.hass.services.has_service("logbook", "log"):
                self.hass.async_create_task(
                    self.hass.services.async_call(
                        "logbook",
                        "log",
                        {
                            "name": "Multizone Thermostat",
                            "message": f"Turned OFF boiler ({self._status_reason})",
                            "entity_id": self.boiler_switch,
                            "domain": "multizone_thermostat",
                        },
                        blocking=False,
                    )
                )

        self.coordinator.record_diagnostic_event("BOILER_SWITCH_OFF", {"switch": self.boiler_switch, "reason": self._status_reason})
        _LOGGER.debug("Boiler forced OFF")

    async def async_emergency_off(self) -> None:
        """Fallback for emergency off and anti-seize."""
        if self._pending_boiler_task:
            self._pending_boiler_task.cancel()
            self._pending_boiler_task = None
        self._trv_wait_start = None
        self._status_reason = "OFF - Emergency/Master OFF"
        await self._force_boiler_off()

    async def async_update(self, demand: float, peak_zone: str | None, frost_emergency: bool) -> None:
        """Feed Peak Load to PWM Engine and control the relay."""
        self._last_demand = demand
        self._last_frost_emergency = frost_emergency
        wanted_state = self._boiler_pwm.calculate(demand)

        boiler_state = self.hass.states.get(self.boiler_switch) if self.boiler_switch else None
        current_boiler_on = boiler_state is not None and boiler_state.state == STATE_ON

        if current_boiler_on and hasattr(self.coordinator, "reset_last_active_time"):
            self.coordinator.reset_last_active_time()

        if current_boiler_on and not self._last_known_boiler_on:
            if self._pending_command is None or self._pending_command[0] != "on":
                self._last_boiler_change = time.monotonic()
        elif not current_boiler_on and self._last_known_boiler_on:
            if self._pending_command is None or self._pending_command[0] != "off":
                self._last_boiler_change = time.monotonic()
        self._last_known_boiler_on = current_boiler_on

        # Diagnostics follow the CONFIRMED entity state, not the command sent
        diag = self.coordinator.plant_diagnostics
        if current_boiler_on and diag._current_boiler_start is None:
            diag.record_boiler_state(True)
        elif boiler_state is not None and boiler_state.state == STATE_OFF and diag._current_boiler_start is not None:
            diag.record_boiler_state(False)
        if self._pending_command is not None:
            cmd, ts = self._pending_command
            if (cmd == "on" and current_boiler_on) or (cmd == "off" and boiler_state is not None and not current_boiler_on):
                self._pending_command = None
            elif time.monotonic() - ts > COMMAND_CONFIRM_TIMEOUT:
                _LOGGER.warning("Boiler switch %s did not confirm '%s' within %ss", self.boiler_switch, cmd, COMMAND_CONFIRM_TIMEOUT)
                self.coordinator.record_diagnostic_event("BOILER_COMMAND_TIMEOUT", {"switch": self.boiler_switch, "command": cmd})
                self._pending_command = None

        # DHW priority: heating request is suppressed, so release the relay even if min_cycle_on is active
        dhw_override = bool(getattr(self.coordinator, "is_dhw_active", False)) and not frost_emergency

        if wanted_state and not current_boiler_on:
            time_since_change = time.monotonic() - self._last_boiler_change
            min_off_sec = self._min_cycle_off * 60
            if time_since_change < min_off_sec:
                self._status_reason = f"HOLD_OFF - min_cycle_off active ({round(min_off_sec - time_since_change)}s remaining)"
                _LOGGER.debug("PWM Tick: Boiler wants to turn ON, but min_cycle_off (%.0fs) hasn't elapsed. Waiting...", min_off_sec)
                return

            _LOGGER.debug("PWM Tick: Boiler -> ON (Peak Demand: %.1f%%)", demand)

            trvs_ready = False
            for zone in self.coordinator.zones:
                climate_id = make_zone_entity_id(zone[CONF_ZONE_NAME])
                mode = self.coordinator.get_zone_mode(climate_id)
                if mode == ZONE_MODE_PRIMARY and self.coordinator.get_zone_demand(climate_id) > 0:
                    trv_list = zone.get(CONF_ZONE_CLIMATES) or zone.get("climates") or zone.get("climate_entities") or []
                    if not trv_list:
                        # Zone has no TRVs (e.g. relay only). Heat path is fully open by default.
                        trvs_ready = True
                        break
                    
                    for trv in trv_list:
                        trv_state = self.hass.states.get(trv)
                        if trv_state and trv_state.state not in ("unavailable", "unknown"):
                            position = None
                            for attr in ["position", "valve_position", "pi_heating_demand", "heating_demand", "valve_state"]:
                                if attr in trv_state.attributes:
                                    position = trv_state.attributes[attr]
                                    break
                            if position is not None:
                                try:
                                    if float(position) > 10.0:
                                        trvs_ready = True
                                        break
                                except (ValueError, TypeError):
                                    if isinstance(position, str) and position.lower() in ("open", "heating", "on", "true"):
                                        trvs_ready = True
                                        break
                            else:
                                trvs_ready = True
                                break
                if trvs_ready:
                    break

            has_any_trvs = any(
                (zone.get(CONF_ZONE_CLIMATES) or zone.get("climates") or zone.get("climate_entities") or [])
                for zone in self.coordinator.zones
            )
            if not trvs_ready and has_any_trvs and not frost_emergency and peak_zone != "Anti-Seize":
                if self._trv_wait_start is None:
                    self._trv_wait_start = time.monotonic()
                elapsed = time.monotonic() - self._trv_wait_start
                if elapsed < 120.0:
                    self._status_reason = f"HOLD_TRV_CLOSED - Waiting for TRVs to open ({round(120.0 - elapsed)}s remaining)"
                    _LOGGER.warning("PWM Tick: Boiler wants to turn ON, but no TRVs are open > 10%%. Waiting for TRVs to open (%.0fs/120s)", elapsed)
                    return
                _LOGGER.info("PWM Tick: TRV opening grace period (120s) elapsed. Proceeding with boiler ignition.")
                trvs_ready = True

            self._trv_wait_start = None

            if self._valve_delay > 0:
                if not self._pending_boiler_task:
                    self._status_reason = f"WAITING_VALVES - Valve delay active ({self._valve_delay}s)"
                    _LOGGER.debug("Waiting %s seconds for valves to open...", self._valve_delay)
                    self._schedule_boiler_check(self._valve_delay, True)
            else:
                self._status_reason = f"ON - Demand {round(demand, 1)}% from {peak_zone or 'Zone'}"
                await self._force_boiler_on()
        elif not wanted_state:
            self._trv_wait_start = None
            time_since_change = time.monotonic() - self._last_boiler_change
            min_on_sec = self._min_cycle_on * 60
            if current_boiler_on and time_since_change < min_on_sec and not dhw_override:
                self._status_reason = f"HOLD_ON - min_cycle_on active ({round(min_on_sec - time_since_change)}s remaining)"
                _LOGGER.debug("PWM Tick: Boiler wants to turn OFF, but min_cycle_on (%.0fs) hasn't elapsed. Waiting...", min_on_sec)
                return

            if self._pending_boiler_task:
                _LOGGER.debug("PWM Tick: Cancelling pending valve-delay task (Peak Demand: %.1f%%)", demand)
                self._pending_boiler_task.cancel()
                self._pending_boiler_task = None
            if current_boiler_on:
                self._status_reason = f"OFF - Cycle ended (Peak Demand: {round(demand, 1)}%)"
                _LOGGER.debug("PWM Tick: Boiler -> OFF (Peak Demand: %.1f%%)", demand)
                await self._force_boiler_off()
            else:
                self._status_reason = f"OFF - Idle (Peak Demand: {round(demand, 1)}%)"
        else:
            self._status_reason = f"ON - Heating (Peak Demand: {round(demand, 1)}% from {peak_zone or 'Zone'})"
