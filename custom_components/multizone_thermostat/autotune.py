import logging
import math
import statistics
import time
from collections import deque, namedtuple
from datetime import datetime

_LOGGER = logging.getLogger(__name__)

class PassiveAutotuneObserver:
    """
    Observes natural ON/OFF cycles (Hysteresis) to calculate PID parameters
    using the Ziegler-Nichols Open-Loop / Reaction Curve method for integrating processes.
    Supports both heating (rising temp) and cooling (falling temp) modes,
    manual parameter overrides, and continuous weekly smoothed EMA tuning.
    """

    STATE_IDLE = "idle"
    STATE_HEATING = "heating"
    STATE_COOLING = "cooling"
    STATE_COMPLETED = "completed"

    HISTORY_MIN_INTERVAL = 30.0
    HISTORY_MIN_TEMP_DELTA = 0.05
    WEEKLY_INTERVAL_SECONDS = 604800.0
    WEEKLY_EMA_ALPHA = 0.15
    WEEKLY_MAX_STEP_PCT = 0.10
    WEEKLY_MIN_CANDIDATES = 3
    WEEKLY_MIN_DEMAND = 85.0
    WEEKLY_MIN_DURATION = 300.0
    WEEKLY_MIN_DT = 0.4

    def __init__(self, zone_name: str, required_cycles: int = 3, mode: str = "heat"):
        self.zone_name = zone_name
        self.required_cycles = required_cycles
        self.mode = mode.lower()  # "heat" or "cool"
        self.state = self.STATE_IDLE

        self.history = deque(maxlen=1000)  # Stores (timestamp, temperature)
        self.completed_cycles = []         # Stores dict of {L, slope, Kp, Ki, Kd}
        self.weekly_candidates = []        # Stores post-completion high-demand ramp candidates
        self.last_weekly_update = 0.0

        self.cycle_start_time = None
        self.cycle_start_temp = None
        self._last_hist_time = None
        self._last_hist_temp = None

        self._ramp_active = False
        self._ramp_start_mono = None
        self._ramp_start_temp = None
        self._ramp_history = deque(maxlen=1000)
        self._ramp_demand_sum = 0.0
        self._ramp_demand_count = 0
        self._last_ramp_hist_time = None
        self._last_ramp_hist_temp = None

        self.kp = 0.0
        self.ki = 0.0
        self.kd = 0.0
        self._learned_kp = 0.0
        self._learned_ki = 0.0
        self._learned_kd = 0.0
        self.manual_overrides: dict[str, float] = {}
        self.weekly_updated_last_tick = False
        self.needs_save = False

    def load_state(self, data: dict):
        """Restore state from storage."""
        if not data:
            return
        self.completed_cycles = list(data.get("completed_cycles", []))
        if "mode" in data:
            self.mode = str(data["mode"]).lower()
        self.weekly_candidates = list(data.get("weekly_candidates", []))
        self.last_weekly_update = float(data.get("last_weekly_update", 0.0) or 0.0)
        raw_overrides = data.get("manual_overrides", {}) or {}
        self.manual_overrides = {}
        for raw_key, raw_val in raw_overrides.items():
            norm = {"kp": "Kp", "ki": "Ki", "kd": "Kd"}.get(str(raw_key).lower())
            if norm and raw_val is not None:
                self.manual_overrides[norm] = float(raw_val)

        if len(self.completed_cycles) >= self.required_cycles:
            self.state = self.STATE_COMPLETED
            learned = data.get("learned_pid")
            if isinstance(learned, dict) and learned.get("Kp"):
                self._learned_kp = float(learned.get("Kp", 0.0))
                self._learned_ki = float(learned.get("Ki", 0.0))
                self._learned_kd = float(learned.get("Kd", 0.0))
                self._sync_effective_pid()
            else:
                self._compute_final_pid()
        else:
            self._sync_effective_pid()

    def dump_state(self) -> dict:
        """Dump state for storage."""
        return {
            "completed_cycles": self.completed_cycles,
            "mode": self.mode,
            "manual_overrides": dict(self.manual_overrides),
            "weekly_candidates": list(self.weekly_candidates),
            "last_weekly_update": self.last_weekly_update,
            "learned_pid": {
                "Kp": self._learned_kp,
                "Ki": self._learned_ki,
                "Kd": self._learned_kd,
            },
        }

    def _sync_effective_pid(self) -> None:
        """Synchronize kp/ki/kd from learned baseline and manual overrides."""
        self.kp = self.manual_overrides.get("Kp", self._learned_kp)
        self.ki = self.manual_overrides.get("Ki", self._learned_ki)
        self.kd = self.manual_overrides.get("Kd", self._learned_kd)

    def set_manual_pid(
        self,
        kp: float | None = None,
        ki: float | None = None,
        kd: float | None = None,
    ) -> None:
        """Apply manual override values for one or more PID parameters."""
        if kp is not None:
            self.manual_overrides["Kp"] = float(kp)
        if ki is not None:
            self.manual_overrides["Ki"] = float(ki)
        if kd is not None:
            self.manual_overrides["Kd"] = float(kd)
        self._sync_effective_pid()

    def lock_param(self, param: str | None = None) -> None:
        """Clear manual override(s) and return parameter(s) to autotuned baseline."""
        if param is None:
            self.manual_overrides.clear()
        else:
            norm = {"kp": "Kp", "ki": "Ki", "kd": "Kd"}.get(param.lower())
            if norm:
                self.manual_overrides.pop(norm, None)
        self._sync_effective_pid()

    def _reset_ramp(self) -> None:
        self._ramp_active = False
        self._ramp_start_mono = None
        self._ramp_start_temp = None
        self._ramp_history.clear()
        self._ramp_demand_sum = 0.0
        self._ramp_demand_count = 0
        self._last_ramp_hist_time = None
        self._last_ramp_hist_temp = None

    def reset(self, keep_manual_overrides: bool = False) -> None:
        """Reset autotuner learning state cleanly."""
        self.state = self.STATE_IDLE
        self.history.clear()
        self.completed_cycles.clear()
        self.weekly_candidates.clear()
        self.last_weekly_update = 0.0
        self.cycle_start_time = None
        self.cycle_start_temp = None
        self._last_hist_time = None
        self._last_hist_temp = None
        self._reset_ramp()
        self._learned_kp = 0.0
        self._learned_ki = 0.0
        self._learned_kd = 0.0
        if not keep_manual_overrides:
            self.manual_overrides.clear()
        self._sync_effective_pid()

    def update(
        self,
        current_temp: float,
        is_heating: bool | None = None,
        now: float = None,
        is_active: bool | None = None,
        demand: float | None = None,
        cooling_rate: float = 0.0,
    ):
        """Called periodically or on state change."""
        self.weekly_updated_last_tick = False
        self.needs_save = False
        active = is_active if is_active is not None else bool(is_heating)
        if now is None:
            now_mono = time.monotonic()
            wall_time = time.time()
        else:
            now_mono = now
            wall_time = now if now > 1e8 else time.time()

        if self.state == self.STATE_COMPLETED:
            self._update_weekly_learning(
                current_temp, active, now_mono, wall_time, demand, cooling_rate
            )
            return

        if self.state == self.STATE_IDLE:
            if active:
                self._start_cycle(now_mono, current_temp)

        elif self.state == self.STATE_HEATING:
            if not active:
                if not self.history or now_mono > self.history[-1][0]:
                    self.history.append((now_mono, current_temp))
                self._stop_cycle(now_mono, current_temp, wall_time=wall_time)
            else:
                if (
                    self._last_hist_time is None
                    or (now_mono - self._last_hist_time) >= self.HISTORY_MIN_INTERVAL
                    or abs(current_temp - self._last_hist_temp) >= self.HISTORY_MIN_TEMP_DELTA
                ):
                    self.history.append((now_mono, current_temp))
                    self._last_hist_time = now_mono
                    self._last_hist_temp = current_temp

        elif self.state == self.STATE_COOLING:
            if active:
                self._start_cycle(now_mono, current_temp)

    def _start_cycle(self, now: float, temp: float):
        action_name = "Heating" if self.mode == "heat" else "Cooling"
        _LOGGER.info("Autotune [%s - %s]: %s started. Recording cycle.", self.zone_name, self.mode, action_name)
        self.state = self.STATE_HEATING
        self.cycle_start_time = now
        self.cycle_start_temp = temp
        self.history.clear()
        self.history.append((now, temp))
        self._last_hist_time = now
        self._last_hist_temp = temp

    def _start_heating(self, now: float, temp: float):
        """Backward-compatible alias."""
        self._start_cycle(now, temp)

    def _analyze_reaction_curve(
        self,
        history_list: list[tuple[float, float]],
        start_time: float,
        start_temp: float,
        wall_time: float | None = None,
        u_avg: float = 1.0,
        cooling_rate_c_per_hr: float = 0.0,
    ) -> dict | None:
        """Analyze heating or cooling reaction curve samples and return ZN PID parameters or None."""
        if len(history_list) < 5:
            _LOGGER.warning("Autotune [%s - %s]: Not enough data points.", self.zone_name, self.mode)
            return None

        max_slope = -999.0
        max_slope_t = None
        max_slope_temp = None

        for i in range(len(history_list)):
            t1, temp1 = history_list[i]
            # Find a point roughly 3-5 minutes later
            for j in range(i + 1, len(history_list)):
                t2, temp2 = history_list[j]
                dt = t2 - t1
                if dt >= 180:  # At least 3 minutes diff to avoid noise
                    slope = ((temp1 - temp2) if self.mode == "cool" else (temp2 - temp1)) / dt
                    if slope > max_slope:
                        max_slope = slope
                        # Midpoint of the interval for the tangent line
                        max_slope_t = t1 + (dt / 2.0)
                        max_slope_temp = temp1 + (temp2 - temp1) / 2.0
                    break

        # Fallback to overall slope if no 3-min window found
        if max_slope_t is None:
            t1, temp1 = history_list[0]
            t2, temp2 = history_list[-1]
            dt = t2 - t1
            if dt < 60.0:
                _LOGGER.warning(
                    "Autotune [%s - %s]: Fallback slope dt too short (%.1fs). Cycle discarded.",
                    self.zone_name,
                    self.mode,
                    dt,
                )
                return None
            if dt > 0:
                max_slope = ((temp1 - temp2) if self.mode == "cool" else (temp2 - temp1)) / dt
                max_slope_t = t1 + (dt / 2.0)
                max_slope_temp = temp1 + (temp2 - temp1) / 2.0

        if max_slope <= 0.0001:
            _LOGGER.warning(
                "Autotune [%s - %s]: Invalid slope %.4f. Cycle discarded.",
                self.zone_name,
                self.mode,
                max_slope,
            )
            return None

        # Find L (Dead Time) before duty/cooling compensation
        if self.mode == "cool":
            t0 = (max_slope_temp - start_temp) / max_slope + max_slope_t
        else:
            t0 = (start_temp - max_slope_temp) / max_slope + max_slope_t
        L = t0 - start_time

        if L < 60.0:
            _LOGGER.info("Autotune [%s - %s]: Dead time too short (%.1fs), clamping to 60s.", self.zone_name, self.mode, L)
            L = 60.0

        if L > 7200.0:
            _LOGGER.warning("Autotune [%s - %s]: Dead time too long (%.1fs). Cycle discarded.", self.zone_name, self.mode, L)
            return None

        # Compensate slope for effective duty ratio and ambient cooling loss (heating mode)
        ambient_loss = max(0.0, cooling_rate_c_per_hr / 3600.0) if self.mode != "cool" else 0.0
        effective_slope = (max_slope / max(0.7, min(1.0, u_avg))) + ambient_loss
        kp_calc = 120.0 / (effective_slope * L)
        # Clamp Kp to reasonable bounds before deriving Ki and Kd so Ti/Td ratios hold
        kp_calc = min(max(kp_calc, 10.0), 500.0)
        ti_calc = 2.0 * L
        td_calc = 0.5 * L

        ki_calc = kp_calc / ti_calc if ti_calc > 0 else 0
        kd_calc = kp_calc * td_calc

        return {
            "L": L,
            "slope": effective_slope,
            "Kp": kp_calc,
            "Ki": ki_calc,
            "Kd": kd_calc,
            "timestamp": wall_time if wall_time is not None else time.time(),
        }

    def _stop_cycle(self, now: float, temp: float, wall_time: float | None = None):
        action_name = "Heating" if self.mode == "heat" else "Cooling"
        _LOGGER.info("Autotune [%s - %s]: %s stopped. Analyzing cycle...", self.zone_name, self.mode, action_name)
        self.state = self.STATE_COOLING

        result = self._analyze_reaction_curve(
            list(self.history),
            self.cycle_start_time,
            self.cycle_start_temp,
            wall_time=wall_time,
        )
        if result is None:
            return

        _LOGGER.info(
            "Autotune [%s - %s]: Cycle valid! L=%.1f s, slope=%.6f °C/s. Kp=%.1f, Ki=%.4f, Kd=%.1f",
            self.zone_name,
            self.mode,
            result["L"],
            result["slope"],
            result["Kp"],
            result["Ki"],
            result["Kd"],
        )

        self.completed_cycles.append(result)
        self.needs_save = True

        if len(self.completed_cycles) >= self.required_cycles:
            _LOGGER.info("Autotune [%s - %s]: Required cycles reached. Learning completed!", self.zone_name, self.mode)
            self.state = self.STATE_COMPLETED
            self.last_weekly_update = wall_time if wall_time is not None else time.time()
            self._compute_final_pid()

    def _stop_heating(self, now: float, temp: float, wall_time: float | None = None):
        """Backward-compatible alias."""
        self._stop_cycle(now, temp, wall_time=wall_time)

    def _update_weekly_learning(
        self,
        current_temp: float,
        is_active: bool,
        now_mono: float,
        wall_time: float,
        demand: float | None,
        cooling_rate: float,
    ) -> None:
        """Continuously observe high-demand ramps and refine PID weekly via smoothed EMA."""
        if demand is not None:
            high_demand = is_active and demand >= self.WEEKLY_MIN_DEMAND
            if high_demand:
                if not self._ramp_active:
                    self._ramp_active = True
                    self._ramp_start_mono = now_mono
                    self._ramp_start_temp = current_temp
                    self._ramp_history.clear()
                    self._ramp_history.append((now_mono, current_temp))
                    self._ramp_demand_sum = float(demand)
                    self._ramp_demand_count = 1
                    self._last_ramp_hist_time = now_mono
                    self._last_ramp_hist_temp = current_temp
                else:
                    self._ramp_demand_sum += float(demand)
                    self._ramp_demand_count += 1
                    if (
                        self._last_ramp_hist_time is None
                        or (now_mono - self._last_ramp_hist_time) >= self.HISTORY_MIN_INTERVAL
                        or abs(current_temp - self._last_ramp_hist_temp) >= self.HISTORY_MIN_TEMP_DELTA
                    ):
                        self._ramp_history.append((now_mono, current_temp))
                        self._last_ramp_hist_time = now_mono
                        self._last_ramp_hist_temp = current_temp
            elif self._ramp_active:
                if not self._ramp_history or now_mono > self._ramp_history[-1][0]:
                    self._ramp_history.append((now_mono, current_temp))
                duration = now_mono - self._ramp_start_mono
                delta_t = (
                    (self._ramp_start_temp - current_temp)
                    if self.mode == "cool"
                    else (current_temp - self._ramp_start_temp)
                )
                if duration >= self.WEEKLY_MIN_DURATION and delta_t >= self.WEEKLY_MIN_DT:
                    u_avg = (self._ramp_demand_sum / max(1, self._ramp_demand_count)) / 100.0
                    candidate = self._analyze_reaction_curve(
                        list(self._ramp_history),
                        self._ramp_start_mono,
                        self._ramp_start_temp,
                        wall_time=wall_time,
                        u_avg=u_avg,
                        cooling_rate_c_per_hr=cooling_rate,
                    )
                    if candidate is not None:
                        self.weekly_candidates.append(candidate)
                        if len(self.weekly_candidates) > 50:
                            self.weekly_candidates = self.weekly_candidates[-50:]
                        self.needs_save = True
                self._reset_ramp()

        if self.last_weekly_update <= 0.0:
            self.last_weekly_update = wall_time

        if (
            len(self.weekly_candidates) >= self.WEEKLY_MIN_CANDIDATES
            and (wall_time - self.last_weekly_update) >= self.WEEKLY_INTERVAL_SECONDS
        ):
            med_kp = statistics.median(c["Kp"] for c in self.weekly_candidates)
            med_ki = statistics.median(c["Ki"] for c in self.weekly_candidates)
            med_kd = statistics.median(c["Kd"] for c in self.weekly_candidates)

            for attr, target in (
                ("_learned_kp", med_kp),
                ("_learned_ki", med_ki),
                ("_learned_kd", med_kd),
            ):
                prev = getattr(self, attr)
                if prev > 0.0:
                    ema = (1.0 - self.WEEKLY_EMA_ALPHA) * prev + self.WEEKLY_EMA_ALPHA * target
                    min_allowed = prev * (1.0 - self.WEEKLY_MAX_STEP_PCT)
                    max_allowed = prev * (1.0 + self.WEEKLY_MAX_STEP_PCT)
                    new_val = min(max(ema, min_allowed), max_allowed)
                else:
                    new_val = target
                if attr == "_learned_kp":
                    new_val = min(max(new_val, 10.0), 500.0)
                setattr(self, attr, new_val)

            self._sync_effective_pid()
            self.weekly_candidates.clear()
            self.last_weekly_update = wall_time
            self.weekly_updated_last_tick = True
            self.needs_save = True
            _LOGGER.info(
                "Autotune [%s - %s]: Weekly smoothed EMA update applied: Kp=%.1f, Ki=%.4f, Kd=%.1f",
                self.zone_name,
                self.mode,
                self.kp,
                self.ki,
                self.kd,
            )

    def _compute_final_pid(self):
        """Average the valid cycles to find final PID parameters."""
        if not self.completed_cycles:
            return

        avg_kp = sum(c["Kp"] for c in self.completed_cycles) / len(self.completed_cycles)
        avg_ki = sum(c["Ki"] for c in self.completed_cycles) / len(self.completed_cycles)
        avg_kd = sum(c["Kd"] for c in self.completed_cycles) / len(self.completed_cycles)

        self._learned_kp = avg_kp
        self._learned_ki = avg_ki
        self._learned_kd = avg_kd
        self._sync_effective_pid()

        _LOGGER.info("Autotune [%s - %s]: FINAL PID: Kp=%.1f, Ki=%.4f, Kd=%.1f", self.zone_name, self.mode, self.kp, self.ki, self.kd)


# Based on a fork of Arduino PID AutoTune Library
# See https://github.com/t0mpr1c3/Arduino-PID-AutoTune-Library
class PIDAutotune:
    """Determines viable parameters for a PID controller.

    Args:
        setpoint (float): The target value.
        out_step (float): The value by which the output will be
            increased/decreased when stepping up/down.
        sampletime (float): The interval between run() calls.
        loockback (float): The reference period for local minima/maxima.
        out_min (float): Lower output limit.
        out_max (float): Upper output limit.
        noiseband (float): Determines by how much the input value must
            overshoot/undershoot the setpoint before the state changes.
        time (function): A function which returns the current time in seconds.
    """
    PIDParams = namedtuple('PIDParams', ['Kp', 'Ki', 'Kd'])

    PEAK_AMPLITUDE_TOLERANCE = 0.05
    STATE_OFF = 'off'
    STATE_RELAY_STEP_UP = 'relay step up'
    STATE_RELAY_STEP_DOWN = 'relay step down'
    STATE_SUCCEEDED = 'succeeded'
    STATE_FAILED = 'failed'

    _tuning_rules = {
        # rule: [Kp_divisor, Ki_divisor, Kd_divisor]
        "ziegler-nichols": [34, 40, 160],
        "tyreus-luyben": [44,  9, 126],
        "ciancone-marlin": [66, 88, 162],
        "pessen-integral": [28, 50, 133],
        "some-overshoot": [60, 40,  60],
        "no-overshoot": [100, 40,  60],
        "brewing": [2.5, 6, 380]
    }

    def __init__(self, out_step=10, lookback=60,
                 out_min=float('-inf'), out_max=float('inf'), noiseband=0.5, time_func=time.time):
        if out_step < 1:
            raise ValueError('out_step must be greater or equal to 1')
        if out_min >= out_max:
            raise ValueError('out_min must be less than out_max')

        self._time = time_func
        self._sampletime = None
        self._last_sample_time = None
        self._sample_time_calc = []
        self._lookback = lookback
        self._inputs = deque(maxlen=10)
        self._inputs_timestamps = deque(maxlen=10)
        self._setpoint = None
        self._outputstep = out_step
        self._noiseband = noiseband
        self._out_min = out_min
        self._out_max = out_max
        self._state = PIDAutotune.STATE_OFF
        self._peak_timestamps = deque(maxlen=5)
        self._peaks = deque(maxlen=5)
        self._output = 0
        self._last_run_timestamp = 0
        self._peak_type = 0
        self._peak_count = 0
        self._initial_output = 0
        self._induced_amplitude = 0
        self._Ku = 0
        self._Pu = 0

    @property
    def state(self):
        """Get the current state."""
        return self._state

    @property
    def output(self):
        """Get the last output value."""
        return self._output

    @property
    def tuning_rules(self):
        """Get a list of all available tuning rules."""
        return self._tuning_rules.keys()

    @property
    def set_point(self):
        """Get the reference set point"""
        return self._setpoint

    @property
    def sample_time(self):
        """Get the sample time considered"""
        return self._sampletime

    @property
    def peak_count(self):
        """Get the number of peaks found"""
        return self._peak_count

    @property
    def buffer_full(self):
        """Get the filling percentage of the buffer"""
        if self._inputs is None or float(self._inputs.maxlen) == 0:
            return 0
        return len(self._inputs) / float(self._inputs.maxlen)

    @property
    def buffer_length(self):
        """Get the total length of buffer"""
        if self._inputs is None:
            return 0
        return self._inputs.maxlen

    def get_pid_parameters(self, tuning_rule='ziegler-nichols'):
        """Get PID parameters.

        Args:
            tuning_rule (str): Sets the rule which should be used to calculate
                the parameters.
        """
        divisors = self._tuning_rules[tuning_rule]
        kp = self._Ku / divisors[0]
        ki = kp / (max(self._Pu, 0.001) / divisors[1])
        kd = kp * (max(self._Pu, 0.001) / divisors[2])
        return PIDAutotune.PIDParams(kp, ki, kd)

    def run(self, input_val, set_point, now=None):
        """To autotune a system, this method must be called periodically.

        Args:
            input_val (float): The input value.
            set_point (float): The target value to be considered.

        Returns:
            `true` if tuning is finished, otherwise `false`.
        """
        if now is None:
            now = self._time()
        if self._sampletime is None:
            # sample time is not defined, use first 5 temperature samples to measure it.
            if self._last_sample_time is None:
                self._last_sample_time = now
                return False
            self._sample_time_calc.append(now - self._last_sample_time)
            self._last_sample_time = now
            if len(self._sample_time_calc) <= 5 or len(self._sample_time_calc) < self._inputs.maxlen:
                return False
            self._sampletime = sum(self._sample_time_calc[5::]) / len(self._sample_time_calc[5::])
            if self._sampletime <= 0:
                return False
            self._setpoint = set_point
            self._inputs = deque(maxlen=round(self._lookback / self._sampletime))
            self._inputs_timestamps = deque(maxlen=round(self._lookback / self._sampletime))

        if self._state in [PIDAutotune.STATE_OFF, PIDAutotune.STATE_SUCCEEDED,
                           PIDAutotune.STATE_FAILED]:
            self._initTuner(input_val, now)
        elif (now - self._last_run_timestamp) < self._sampletime - 0.90:  # keep a 10% margin
            return False

        # check input and change relay state if necessary
        if (self._state == PIDAutotune.STATE_RELAY_STEP_UP
                and input_val > self._setpoint + self._noiseband):
            self._state = PIDAutotune.STATE_RELAY_STEP_DOWN
            _LOGGER.debug('switched state: %s', self._state)
            _LOGGER.debug('input: %.1f', input_val)
        elif (self._state == PIDAutotune.STATE_RELAY_STEP_DOWN
                and input_val < self._setpoint - self._noiseband):
            self._state = PIDAutotune.STATE_RELAY_STEP_UP
            _LOGGER.debug('switched state: %s', self._state)
            _LOGGER.debug('input: %.1f', input_val)

        # set output
        if (self._state == PIDAutotune.STATE_RELAY_STEP_UP):
            self._output = self._initial_output + self._outputstep
        elif self._state == PIDAutotune.STATE_RELAY_STEP_DOWN:
            self._output = self._initial_output - self._outputstep

        # respect output limits
        self._output = min(self._output, self._out_max)
        self._output = max(self._output, self._out_min)

        # identify peaks
        is_max = True
        is_min = True

        for val in self._inputs:
            is_max = is_max and (input_val >= val)
            is_min = is_min and (input_val <= val)

        self._inputs.append(input_val)
        self._inputs_timestamps.append(now)
        self._last_run_timestamp = now

        # we don't want to trust the maxes or mins until the input array is full
        if len(self._inputs) < self._inputs.maxlen:
            return False

        return self.analysis()

    def _initTuner(self, inputValue, timestamp):
        self._peak_type = 0
        self._peak_count = 0
        self._output = 0
        self._initial_output = 0
        self._Ku = 0
        self._Pu = 0
        self._inputs.clear()
        self._peaks.clear()
        self._peak_timestamps.clear()
        self._state = PIDAutotune.STATE_RELAY_STEP_UP

    def analysis(self):
        self._peak_count = 0
        self._peak_type = 0
        self._peaks.clear()
        self._peak_timestamps.clear()
        for index in range(self._inputs.maxlen):
            input_val = self._inputs[index]
            now = self._inputs_timestamps[index]
            # identify peaks
            is_max = True
            is_min = True

            for val in self._inputs:
                is_max = is_max and (input_val >= val)
                is_min = is_min and (input_val <= val)

            # increment peak count and record peak time for maxima and minima
            inflection = False

            # peak types:
            # -1: minimum
            # +1: maximum
            if is_max:
                if self._peak_type == -1:
                    inflection = True
                self._peak_type = 1
            elif is_min:
                if self._peak_type == 1:
                    inflection = True
                self._peak_type = -1

            # update peak times and values
            if inflection:
                self._peak_count += 1
                self._peaks.append(input_val)
                self._peak_timestamps.append(now)
                _LOGGER.debug('found peak: %.1f', input_val)
                _LOGGER.debug('peak count: %i', self._peak_count)

            # check for convergence of induced oscillation
            # convergence of amplitude assessed on last 4 peaks (1.5 cycles)
            self._induced_amplitude = 0

            if inflection and (self._peak_count > 4):
                abs_max = self._peaks[-2]
                abs_min = self._peaks[-2]
                for i in range(0, len(self._peaks) - 2):
                    self._induced_amplitude += abs(self._peaks[i] - self._peaks[i+1])
                    abs_max = max(self._peaks[i], abs_max)
                    abs_min = min(self._peaks[i], abs_min)

                self._induced_amplitude /= 6.0

                # check convergence criterion for amplitude of induced oscillation
                if self._induced_amplitude < 0.0001:
                    self._induced_amplitude = 0.0001
                
                amplitude_dev = ((0.5 * (abs_max - abs_min) - self._induced_amplitude)
                                 / self._induced_amplitude)

                _LOGGER.debug('amplitude: %.2f', self._induced_amplitude)
                _LOGGER.debug('amplitude deviation: %.2f', amplitude_dev)

                if amplitude_dev < PIDAutotune.PEAK_AMPLITUDE_TOLERANCE:
                    self._state = PIDAutotune.STATE_SUCCEEDED

            # if the autotune has not already converged
            # terminate after 10 cycles
            if self._peak_count >= 20:
                self._output = 0
                self._state = PIDAutotune.STATE_FAILED
                return True

            if self._state == PIDAutotune.STATE_SUCCEEDED:
                self._output = 0

                # calculate ultimate gain
                self._Ku = 4.0 * self._outputstep / (self._induced_amplitude * math.pi)

                # calculate ultimate period in seconds
                period1 = self._peak_timestamps[3] - self._peak_timestamps[1]
                period2 = self._peak_timestamps[4] - self._peak_timestamps[2]
                self._Pu = 0.5 * (period1 + period2)
                return True
        return False


PIDAutotuner = PIDAutotune
