"""Relay boiler backend with PWM control."""
import logging
import time
import asyncio

from homeassistant.core import HomeAssistant
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_ON, SERVICE_TURN_OFF, STATE_ON

from .base import BoilerBackend
from ..pwm_engine import PWMEngine
from ..const import CONF_ZONE_NAME, CONF_ZONE_CLIMATES, ZONE_MODE_PRIMARY, make_zone_entity_id

_LOGGER = logging.getLogger(__name__)

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
                    await self._force_boiler_on()
                else:
                    await self._force_boiler_off()
            except asyncio.CancelledError:
                pass

        self._pending_boiler_task = self.hass.async_create_task(_delayed_check())

    async def _force_boiler_on(self) -> None:
        """Actually turn the boiler on and set locks."""
        if not self.boiler_switch:
            return

        if self._pending_boiler_task:
            pass

        await self.hass.services.async_call(
            "switch",
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: self.boiler_switch},
            blocking=False,
        )
        self._last_boiler_change = time.monotonic()
        self.coordinator.record_diagnostic_event("BOILER_SWITCH_ON", {"switch": self.boiler_switch, "reason": self._status_reason})
        self.coordinator.plant_diagnostics.record_boiler_state(True)
        _LOGGER.debug("Boiler forced ON")

    async def _force_boiler_off(self) -> None:
        """Actually turn the boiler off and set locks."""
        if not self.boiler_switch:
            return

        if self._pending_boiler_task:
            pass

        await self.hass.services.async_call(
            "switch",
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: self.boiler_switch},
            blocking=False,
        )
        self._last_boiler_change = time.monotonic()
        self.coordinator.record_diagnostic_event("BOILER_SWITCH_OFF", {"switch": self.boiler_switch, "reason": self._status_reason})
        self.coordinator.plant_diagnostics.record_boiler_state(False)
        _LOGGER.debug("Boiler forced OFF")

    async def async_emergency_off(self) -> None:
        """Fallback for emergency off and anti-seize."""
        if self._pending_boiler_task:
            self._pending_boiler_task.cancel()
            self._pending_boiler_task = None
        self._status_reason = "OFF - Emergency/Master OFF"
        await self._force_boiler_off()

    async def async_update(self, demand: float, peak_zone: str | None, frost_emergency: bool) -> None:
        """Feed Peak Load to PWM Engine and control the relay."""
        wanted_state = self._boiler_pwm.calculate(demand)

        boiler_state = self.hass.states.get(self.boiler_switch) if self.boiler_switch else None
        current_boiler_on = boiler_state is not None and boiler_state.state == STATE_ON
        
        # Track start time in diagnostics if it turned on externally
        if current_boiler_on and self.coordinator.plant_diagnostics._current_boiler_start is None:
            self.coordinator.plant_diagnostics.record_boiler_state(True)

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
                    trv_list = zone.get(CONF_ZONE_CLIMATES) or []
                    if not trv_list:
                        # Zone has no TRVs (e.g. relay only). Heat path is fully open by default.
                        trvs_ready = True
                        break
                    
                    for trv in trv_list:
                        trv_state = self.hass.states.get(trv)
                        if trv_state:
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

            if not trvs_ready and any((zone.get(CONF_ZONE_CLIMATES) or []) for zone in self.coordinator.zones) and not frost_emergency:
                self._status_reason = "HOLD_TRV_CLOSED - TRVs not physically open > 10%"
                _LOGGER.warning("PWM Tick: Boiler wants to turn ON, but no TRVs are open > 10%. Delaying boiler ignition.")
                return

            if self._valve_delay > 0:
                if not self._pending_boiler_task:
                    self._status_reason = f"WAITING_VALVES - Valve delay active ({self._valve_delay}s)"
                    _LOGGER.debug("Waiting %s seconds for valves to open...", self._valve_delay)
                    self._schedule_boiler_check(self._valve_delay, True)
            else:
                self._status_reason = f"ON - Demand {round(demand, 1)}% from {peak_zone or 'Zone'}"
                await self._force_boiler_on()
        elif not wanted_state:
            time_since_change = time.monotonic() - self._last_boiler_change
            min_on_sec = self._min_cycle_on * 60
            if current_boiler_on and time_since_change < min_on_sec:
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
