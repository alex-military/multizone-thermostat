"""PWM Engine for translating 0-100% demand into ON/OFF states with Proportional Dilatation."""
import time
import logging

_LOGGER = logging.getLogger(__name__)


class PWMEngine:
    """A PWM engine that handles min_cycle_on and min_cycle_off dilatation."""

    CONTINUOUS_ON_THRESHOLD = 95.0

    def __init__(self, pwm_interval: float, min_on: float = 0.0, min_off: float = 0.0, phase_locked: bool = False):
        """
        Args:
            pwm_interval: The base PWM cycle duration in seconds (e.g. 900 for 15 mins).
            min_on: Minimum ON time in seconds.
            min_off: Minimum OFF time in seconds.
            phase_locked: Align cycle starts to common epoch grid (now - now % pwm_interval).
        """
        self.pwm_interval = pwm_interval
        self.min_on = min_on
        self.min_off = min_off
        self.phase_locked = bool(phase_locked)

        self.cycle_start_time = self._aligned_cycle_start(time.monotonic())
        self.current_state = False
        self.time_on = 0.0
        self.time_off = pwm_interval
        self._prev_demand = 0.0
        self._in_off_phase = False
        self._last_cycle_on = 0.0

    def _aligned_cycle_start(self, now: float) -> float:
        """Return phase-locked grid start or raw monotonic timestamp."""
        if self.phase_locked and self.pwm_interval > 0.0:
            return now - (now % self.pwm_interval)
        return now

    def set_params(self, pwm_interval=None, min_on=None, min_off=None):
        if pwm_interval is not None:
            self.pwm_interval = pwm_interval
        if min_on is not None:
            self.min_on = min_on
        if min_off is not None:
            self.min_off = min_off

    def calculate(self, demand: float) -> bool:
        """Calculate the current ON/OFF state based on demand (0-100)."""
        now = time.monotonic()
        max_cycle = self.pwm_interval * 4

        # Zero out negligible trickle demand far below achievable min_on duty cycle
        if 0.0 < demand < self.CONTINUOUS_ON_THRESHOLD and self.min_on > 0.0 and max_cycle > 0.0:
            min_effective_demand = (100.0 * self.min_on / max_cycle) * 0.25
            if demand < min_effective_demand:
                demand = 0.0

        prev_demand = getattr(self, "_prev_demand", 0.0)
        rising_from_idle = prev_demand <= 0.0 and demand > 0.0
        self._prev_demand = demand

        # High-demand continuous ON to avoid forced off-pulses when zones actively call for heat
        if demand >= self.CONTINUOUS_ON_THRESHOLD:
            self.time_on = self.pwm_interval
            self.time_off = 0.0
            if rising_from_idle:
                self.cycle_start_time = now
            elif now - self.cycle_start_time >= self.pwm_interval:
                self.cycle_start_time = now
            self._in_off_phase = False
            self._last_cycle_on = self.time_on
            self.current_state = True
            return self.current_state

        prev_state = self.current_state

        # Calculate raw times
        if demand <= 0.0:
            self.time_on = 0.0
            self.time_off = self.pwm_interval
            self._in_off_phase = False
            self._last_cycle_on = 0.0
        else:
            self.time_on = self.pwm_interval * (demand / 100.0)
            self.time_off = self.pwm_interval - self.time_on

            # Proportional Dilatation (HASmartThermostat logic)
            if 0 < self.time_on < self.min_on:
                self.time_off *= self.min_on / self.time_on
                self.time_on = self.min_on

            if 0 < self.time_off < self.min_off:
                self.time_on *= self.min_off / self.time_off
                self.time_off = self.min_off

            # Safety cap: never let dilatation stretch beyond 4x the base cycle
            if self.time_on + self.time_off > max_cycle:
                if demand >= 50.0:
                    self.time_off = min(self.min_off, max_cycle)
                    self.time_on = max(0.0, max_cycle - self.time_off)
                else:
                    self.time_on = min(self.min_on, max_cycle)
                    self.time_off = max(0.0, max_cycle - self.time_on)

        new_time_on = self.time_on
        new_time_off = self.time_off

        if rising_from_idle:
            aligned = self._aligned_cycle_start(now)
            # Only snap cold-start onto the phase-locked grid if still inside the ON window;
            # otherwise start immediately at `now` so a fresh heat call is never skipped.
            self.cycle_start_time = aligned if (now - aligned) < new_time_on else now
            self._in_off_phase = False
            self._last_cycle_on = 0.0

        time_passed = now - self.cycle_start_time

        # Anti-phase-jump latch: never re-ignite inside the OFF phase of the current cycle
        last_cycle_on = getattr(self, "_last_cycle_on", 0.0)
        in_off_phase = getattr(self, "_in_off_phase", False)
        if in_off_phase and last_cycle_on > 0.0 and demand > 0.0:
            self.time_on = last_cycle_on
            floor_cycle = min(max_cycle, last_cycle_on / (demand / 100.0)) if max_cycle > 0.0 else last_cycle_on / (demand / 100.0)
            self.time_off = max(self.min_off, max(0.0, floor_cycle - self.time_on))

        total_cycle = self.time_on + self.time_off

        # If we exceeded the cycle duration, start a new cycle with the fresh timings
        if time_passed >= total_cycle:
            if total_cycle <= self.pwm_interval + 1e-6:
                self.cycle_start_time = self._aligned_cycle_start(now)
                time_passed = max(0.0, now - self.cycle_start_time)
            else:
                self.cycle_start_time = now
                time_passed = 0.0
            self.time_on = new_time_on
            self.time_off = new_time_off
            self._in_off_phase = False
            self._last_cycle_on = 0.0
            in_off_phase = False

        # Determine state
        if demand <= 0.0:
            self.current_state = False
        elif in_off_phase:
            self.current_state = False
        else:
            self.current_state = time_passed < self.time_on

        if self.current_state:
            self._in_off_phase = False
            self._last_cycle_on = self.time_on
        elif prev_state and demand > 0.0:
            self._in_off_phase = True
            self._last_cycle_on = min(self.time_on, time_passed) if time_passed > 0.0 else self.time_on

        return self.current_state
