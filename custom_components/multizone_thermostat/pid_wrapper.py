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
    
    def __init__(self, kp: float, ki: float, kd: float, out_min: float = 0.0, out_max: float = 100.0, sensor_timeout: float = 7200.0):
        """Initialize the PID wrapper.
        
        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            out_min: Minimum output (default 0%)
            out_max: Maximum output (default 100%)
            sensor_timeout: Seconds before a sensor is considered dead (default 2 hours)
        """
        self._pid = PID(kp, ki, kd, out_min=out_min, out_max=out_max, sampling_period=0)
        self.sensor_timeout = sensor_timeout
        self.last_sensor_update = time.time()
        self._last_demand = 0.0
        
    @property
    def mode(self):
        return self._pid.mode
        
    @mode.setter
    def mode(self, mode):
        self._pid.mode = mode
        
    def set_pid_param(self, kp=None, ki=None, kd=None):
        self._pid.set_pid_param(kp=kp, ki=ki, kd=kd)
        
    def clear_samples(self):
        self._pid.clear_samples()
        
    def update_sensor_timestamp(self):
        """Called externally when the temperature sensor actually reports a new value."""
        self.last_sensor_update = time.time()
        
    def calc(self, current_temp: float, target_temp: float) -> float:
        """Calculate the new demand percentage."""
        now = time.time()
        
        # Dead Sensor Timeout Check
        if self.sensor_timeout > 0 and (now - self.last_sensor_update) > self.sensor_timeout:
            _LOGGER.warning("PID: Dead Sensor Timeout reached (%.1f seconds). Forcing demand to 0%%.", (now - self.last_sensor_update))
            self._last_demand = 0.0
            return self._last_demand
            
        # Calculate PID
        demand, _ = self._pid.calc(current_temp, target_temp, input_time=now)
        self._last_demand = demand
        return self._last_demand
