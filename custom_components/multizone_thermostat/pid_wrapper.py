"""Wrapper for PID controller to handle Home Assistant specific logic like dead sensor timeout."""
import logging
import time
try:
    from .pid import PID
except ImportError:
    from pid import PID

_LOGGER = logging.getLogger(__name__)

class MultizonePID:
    """A wrapper around the mathematical PID controller."""
    
    def __init__(
        self,
        kp: float,
        ki: float,
        kd: float,
        out_min: float = 0.0,
        out_max: float = 100.0,
        sensor_timeout: float = 7200.0,
        zone_id: str = '',
        action: str = 'heat',
    ):
        """Initialize the PID wrapper.
        
        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            out_min: Minimum output (default 0%)
            out_max: Maximum output (default 100%)
            sensor_timeout: Seconds before a sensor is considered dead (default 2 hours)
            zone_id: Identifier of zone
            action: 'heat' for heating (reverse action) or 'cool' for cooling (direct action)
        """
        self._pid = PID(kp, ki, kd, out_min=out_min, out_max=out_max, sampling_period=0)
        self.sensor_timeout = sensor_timeout
        self.zone_id = zone_id
        self.action = action.lower()
        self.update_sensor_timestamp()
        self.last_sensor_update = time.monotonic()
        self._last_input_time: float | None = None
        self._last_demand = 0.0
        
    @property
    def mode(self):
        return self._pid.mode

    @property
    def last_input_time(self) -> float | None:
        """Return monotonic timestamp of the last PID evaluation."""
        return self._last_input_time

    @property
    def has_evaluated(self) -> bool:
        """Return True if the PID has evaluated at least one sample."""
        return self._last_input_time is not None
        
    @mode.setter
    def mode(self, mode):
        self._pid.mode = mode
        
    def set_pid_param(self, kp=None, ki=None, kd=None):
        self._pid.set_pid_param(kp=kp, ki=ki, kd=kd)
        
    def clear_samples(self, reset_sensor_timer: bool = False):
        """Clear samples, dt tracking and integral; optionally refresh sensor timestamp."""
        self._last_input_time = None
        self._pid.clear_samples()
        self._pid.integral = 0.0
        if reset_sensor_timer:
            self.update_sensor_timestamp()
        
    def update_sensor_timestamp(self):
        """Called externally when the temperature sensor actually reports a new value."""
        self.last_sensor_update = time.monotonic()
        
    def calc(self, current_temp: float, target_temp: float) -> float:
        """Calculate the new demand percentage."""
        now = time.monotonic()
        
        # Dead Sensor Timeout Check
        if self.sensor_timeout > 0 and (now - self.last_sensor_update) > self.sensor_timeout:
            zone_desc = f" for zone '{self.zone_id}'" if self.zone_id else ""
            _LOGGER.warning("PID: Dead Sensor Timeout reached (%.1f seconds)%s. Forcing demand to 0%%.", (now - self.last_sensor_update), zone_desc)
            self._last_input_time = None
            self._pid.clear_samples()
            self._pid.integral = 0.0
            self._last_demand = 0.0
            return self._last_demand
            
        # In cooling mode, mirror input and setpoint so positive error (room hotter than target)
        # produces positive output, and temperature drop acts as negative rate for braking derivative.
        if self.action == 'cool':
            input_val = -current_temp
            set_point = -target_temp
        else:
            input_val = current_temp
            set_point = target_temp

        # Calculate PID with tracked last_input_time to ensure proper dt calculation without jumps
        demand, updated = self._pid.calc(input_val, set_point, input_time=now, last_input_time=self._last_input_time)
        if updated:
            self._last_input_time = now
        self._last_demand = demand
        return self._last_demand

    def get_diagnostics(self) -> dict[str, float | None]:
        """Return live internal PID breakdown for Home Assistant diagnostics."""
        sp = self._pid.set_point
        if sp is not None and self.action == "cool":
            sp = -sp
        return {
            "kp": round(float(self._pid._Kp), 4),
            "ki": round(float(self._pid._Ki), 6),
            "kd": round(float(self._pid._Kd), 2),
            "p_contribution": round(float(self._pid.proportional), 4),
            "i_contribution": round(float(self._pid.integral), 4),
            "d_contribution": round(float(self._pid.derivative), 4),
            "integral_accumulator": round(float(self._pid.integral), 4),
            "pid_raw_output": round(float(self._pid.raw_output), 4),
            "pid_clamped_output": round(float(self._pid.output), 4),
            "pid_error": round(float(self._pid.error), 4),
            "pid_target": round(float(sp), 4) if sp is not None else None,
            "dt_seconds": round(float(self._pid.dt), 2),
        }
