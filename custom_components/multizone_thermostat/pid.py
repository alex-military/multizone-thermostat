"""
PID Controller module (Vendorized).
Source: https://github.com/ScratMan/HASmartThermostat/tree/master/custom_components/smart_thermostat/pid_controller
Original Author: ScratMan / hacker-cb
This file contains the pure mathematical PID calculations.
It uses Time-Proportional dt calculation to natively support irregular sensor updates.
"""
import math
import logging
from time import monotonic
from collections import deque, namedtuple

_LOGGER = logging.getLogger(__name__)


# Based on Arduino PID Library
# See https://github.com/br3ttb/Arduino-PID-Library
class PID:
    # Defaults for least-squares derivative over a 15-minute window, bounded to +/-15%
    DEFAULT_DERIVATIVE_WINDOW = 900.0
    MAX_DERIVATIVE = 15.0
    MIN_DERIVATIVE_SAMPLES = 3
    MIN_SPAN_FRACTION = 1.0 / 3.0
    MIN_DERIVATIVE_TEMP_SPAN = 0.105
    error: float

    def __init__(self, kp, ki, kd, ke=0, out_min=float('-inf'), out_max=float('+inf'),
                 sampling_period=0, cold_tolerance=0.3, hot_tolerance=0.3, max_dt=600.0,
                 derivative_window=DEFAULT_DERIVATIVE_WINDOW, derivative_limit=MAX_DERIVATIVE):
        """A proportional-integral-derivative controller.
            :param kp: Proportional coefficient.
            :type kp: float
            :param ki: Integral coefficient.
            :type ki: float
            :param kd: Derivative coefficient.
            :type kd: float
            :param ke: Outdoor temperature compensation coefficient.
            :type ke: float
            :param out_min: Lower output limit.
            :type out_max: Upper output limit.
            :type out_max: float
            :param sampling_period: time period between two PID calculations in seconds
            :type sampling_period: float
            :param cold_tolerance: time period between two PID calculations in seconds
            :type cold_tolerance: float
            :param hot_tolerance: time period between two PID calculations in seconds
            :type hot_tolerance: float
            :param max_dt: Upper bound on dt for integral accumulation in seconds
            :type max_dt: float
            :param derivative_window: Seconds of history used for least-squares derivative slope
            :type derivative_window: float
            :param derivative_limit: Max absolute derivative contribution in output units
            :type derivative_limit: float
        """
        if kp is None:
            raise ValueError('kp must be specified')
        if ki is None:
            raise ValueError('ki must be specified')
        if kd is None:
            raise ValueError('kd must be specified')
        if out_min >= out_max:
            raise ValueError('out_min must be less than out_max')

        self._Kp = kp
        self._Ki = ki
        self._Kd = kd
        self._Ke = ke
        self._out_min = out_min
        self._out_max = out_max
        self._max_dt = float(max_dt)
        self._proportional = 0.0
        self._integral = 0.0
        self._derivative = 0.0
        self._last_set_point = 0
        self._set_point = 0
        self._input = None
        self._input_time = None
        self._last_input = None
        self._last_input_time = None
        self._error = 0
        self._input_diff = 0
        self._dext = 0
        self._dt = 0
        self._last_output = 0
        self._output = 0
        self._raw_output = 0.0
        self._external = 0
        self._mode = 'AUTO'
        self._sampling_period = sampling_period
        self._cold_tolerance = cold_tolerance
        self._hot_tolerance = hot_tolerance
        self._derivative_window = 0.0
        self._derivative_limit = 0.0
        self._history: deque[tuple[float, float]] = deque()
        self.set_derivative_params(window=derivative_window, limit=derivative_limit)

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, mode):
        if not isinstance(mode, str) or mode.upper() not in ("AUTO", "OFF"):
            raise ValueError(f"Invalid PID mode: {mode}")
        self._mode = mode.upper()

    @property
    def out_max(self):
        return self._out_max

    @out_max.setter
    def out_max(self, out_max):
        self._out_max = out_max

    @property
    def out_min(self):
        return self._out_min

    @out_min.setter
    def out_min(self, out_min):
        self._out_min = out_min

    @property
    def sampling_period(self):
        return self._sampling_period

    @property
    def error(self):
        return self._error

    @property
    def proportional(self):
        return self._proportional

    @property
    def integral(self):
        return self._integral

    @integral.setter
    def integral(self, i):
        if not isinstance(i, (int, float)):
            raise TypeError("integral must be int or float")
        self._integral = float(i)

    @property
    def derivative(self):
        return self._derivative

    @property
    def external(self):
        return self._external

    @property
    def dt(self):
        return self._dt

    @property
    def output(self):
        return self._output

    @property
    def raw_output(self):
        return self._raw_output

    @property
    def set_point(self):
        return self._set_point

    @property
    def derivative_window(self):
        """Seconds of history used for the least-squares derivative slope (0 disables D)."""
        return self._derivative_window

    @property
    def derivative_limit(self):
        """Maximum absolute derivative contribution in output units (0 disables D)."""
        return self._derivative_limit

    def set_derivative_params(self, window=None, limit=None):
        """Configure derivative window (seconds) and output limit; ignore invalid values."""
        if isinstance(window, (int, float)) and not isinstance(window, bool) and math.isfinite(window):
            self._derivative_window = max(0.0, float(window))
        if isinstance(limit, (int, float)) and not isinstance(limit, bool) and math.isfinite(limit):
            self._derivative_limit = max(0.0, float(limit))

    def _temperature_slope(self, now):
        """Least-squares slope (input units per second) over the derivative window."""
        window = self._derivative_window
        if window <= 0.0 or now is None or not isinstance(now, (int, float)) or isinstance(now, bool) or not math.isfinite(now):
            return None
        now = float(now)
        history = self._history
        if history and now <= history[-1][0]:
            history[-1] = (now, float(self._input))
        else:
            history.append((now, float(self._input)))
        while history and history[0][0] < now - window:
            history.popleft()
        if len(history) < self.MIN_DERIVATIVE_SAMPLES:
            return None
        if history[-1][0] - history[0][0] < window * self.MIN_SPAN_FRACTION:
            return None
        vals = [v for _, v in history]
        if (max(vals) - min(vals)) <= self.MIN_DERIVATIVE_TEMP_SPAN:
            return 0.0
        n = len(history)
        mean_t = sum(t for t, _ in history) / n
        mean_v = sum(vals) / n
        den = sum((t - mean_t) ** 2 for t, _ in history)
        if den <= 0.0:
            return None
        return sum((t - mean_t) * (v - mean_v) for t, v in history) / den

    @property
    def max_dt(self):
        return self._max_dt

    @max_dt.setter
    def max_dt(self, val):
        self._max_dt = float(val)

    def set_pid_param(self, kp=None, ki=None, kd=None, ke=None):
        """Set PID parameters."""
        if kp is not None and isinstance(kp, (int, float)):
            self._Kp = kp
        if ki is not None and isinstance(ki, (int, float)):
            self._Ki = ki
        if kd is not None and isinstance(kd, (int, float)):
            self._Kd = kd
        if ke is not None and isinstance(ke, (int, float)):
            self._Ke = ke

    def clear_samples(self):
        """Clear the samples values and timestamp to restart PID from clean state after
        a switch off of the thermostat"""
        self._input = None
        self._input_time = None
        self._last_input = None
        self._last_input_time = None
        self._derivative = 0.0
        self._history.clear()
        
    def calc(self, input_val, set_point, input_time=None, last_input_time=None, ext_temp=None):
        """Adjusts and holds the given setpoint.

        Args:
            input_val (float): The input value.
            set_point (float): The target value.
            input_time (float): The timestamp in seconds of the input value to compute dt
            last_input_time (float): The timestamp in seconds of the previous input value to
            compute dt
            ext_temp (float): The outdoor temperature value.

        Returns:
            A value between `out_min` and `out_max`.
        """
        if not math.isfinite(input_val) or not math.isfinite(set_point):
            return self._output, False

        if self._sampling_period != 0 and self._input_time is not None and \
                monotonic() - self._input_time < self._sampling_period:
            return self._output, False  # If last sample is too young, keep last output value

        self._last_input = self._input
        if self._sampling_period == 0:
            self._last_input_time = last_input_time
        else:
            self._last_input_time = self._input_time
        self._last_output = self._output

        # Refresh with actual values
        self._input = input_val
        if self._sampling_period == 0:
            self._input_time = input_time
        else:
            self._input_time = monotonic()
        self._last_set_point = self._set_point
        self._set_point = set_point

        if self.mode == 'OFF':  # If PID is off, simply switch between min and max output
            if input_val <= set_point - self._cold_tolerance:
                self._output = self._out_max
                self._raw_output = self._output
                _LOGGER.debug("PID is off and input lower than set point: heater ON")
                return self._output, True
            elif input_val >= set_point + self._hot_tolerance:
                self._output = self._out_min
                self._raw_output = self._output
                _LOGGER.debug("PID is off and input higher than set point: heater OFF")
                return self._output, True
            else:
                return self._output, False

        # Compute all the working error variables
        self._error = set_point - input_val
        if self._last_input is not None:
            self._input_diff = self._input - self._last_input
        else:
            self._input_diff = 0
        if self._last_input_time is not None:
            self._dt = self._input_time - self._last_input_time
        else:
            self._dt = 0
        if ext_temp is not None and math.isfinite(ext_temp):
            self._dext = set_point - ext_temp
        else:
            self._dext = 0

        # Compensate losses due to external temperature
        self._external = self._Ke * self._dext

        # Compute P and D before integral update for conditional anti-windup
        self._proportional = self._Kp * self._error
        slope = self._temperature_slope(self._input_time)
        if slope is None or self._derivative_limit <= 0.0 or (self._last_input is not None and self._dt < 1.0):
            self._derivative = 0.0
        else:
            raw_d = -self._Kd * slope
            self._derivative = max(-self._derivative_limit, min(self._derivative_limit, raw_d))

        # Anti-windup: conditional integration + back-calculation clamp
        # Reset integral only on large setpoint drop (>= 1.5°C, or rise in cool mode)
        # while preserving steady-state integral on warm-up steps and minor inertia shifts.
        if self._last_set_point is not None and (self._last_set_point - self._set_point) >= 1.5:
            self._integral = 0.0
            pre_backcalc_total = self._proportional + self._integral + self._derivative + self._external
        else:
            dt_int = max(0.0, min(self._dt, self._max_dt))
            delta_i = self._Ki * self._error * dt_int
            pre_output = self._proportional + self._integral + self._derivative + self._external
            if not ((pre_output >= self._out_max and delta_i > 0) or
                    (pre_output <= self._out_min and delta_i < 0)):
                self._integral += delta_i

            # Clamp integral to hard output bounds (accounting for external compensation)
            min_i = self._out_min - self._external
            max_i = self._out_max - self._external
            self._integral = max(min(self._integral, max_i), min_i)

            pre_backcalc_total = self._proportional + self._integral + self._derivative + self._external

            # Back-calculation clamp to prevent residual P+I+D+ext overshoot without inverting sign
            if self._integral > 0.0 and pre_backcalc_total > self._out_max:
                back_max = max(0.0, self._out_max - self._proportional - self._derivative - self._external)
                self._integral = max(min(self._integral, back_max), min_i)
            elif self._integral < 0.0 and pre_backcalc_total < self._out_min:
                back_min = min(0.0, self._out_min - self._proportional - self._derivative - self._external)
                self._integral = min(max(self._integral, back_min), max_i)

        # Compute PID Output
        self._raw_output = pre_backcalc_total
        output = self._proportional + self._integral + self._derivative + self._external
        self._output = max(min(output, self._out_max), self._out_min)
        return self._output, True


PIDController = PID

from .autotune import PIDAutotune, PIDAutotuner
