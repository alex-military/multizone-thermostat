"""PWM Engine for translating 0-100% demand into ON/OFF states with Proportional Dilatation."""
import time
import logging

_LOGGER = logging.getLogger(__name__)

class PWMEngine:
    """A PWM engine that handles min_cycle_on and min_cycle_off dilatation."""
    
    def __init__(self, pwm_interval: float, min_on: float = 0.0, min_off: float = 0.0):
        """
        Args:
            pwm_interval: The base PWM cycle duration in seconds (e.g. 900 for 15 mins).
            min_on: Minimum ON time in seconds.
            min_off: Minimum OFF time in seconds.
        """
        self.pwm_interval = pwm_interval
        self.min_on = min_on
        self.min_off = min_off
        
        self.cycle_start_time = time.time()
        self.current_state = False
        self.time_on = 0.0
        self.time_off = pwm_interval
        
    def set_params(self, pwm_interval=None, min_on=None, min_off=None):
        if pwm_interval is not None: self.pwm_interval = pwm_interval
        if min_on is not None: self.min_on = min_on
        if min_off is not None: self.min_off = min_off
        
    def calculate(self, demand: float) -> bool:
        """Calculate the current ON/OFF state based on demand (0-100)."""
        now = time.time()
        time_passed = now - self.cycle_start_time
        
        # Calculate raw times
        # If demand is 0 or 100, we skip dilatation
        if demand <= 0.0:
            self.time_on = 0.0
            self.time_off = self.pwm_interval
        elif demand >= 100.0:
            self.time_on = self.pwm_interval
            self.time_off = 0.0
        else:
            self.time_on = self.pwm_interval * (demand / 100.0)
            self.time_off = self.pwm_interval - self.time_on
            
            # Proportional Dilatation (HASmartThermostat logic)
            if 0 < self.time_on < self.min_on:
                # time_on is too short, increase time_off proportionally
                self.time_off *= self.min_on / self.time_on
                self.time_on = self.min_on
            
            if 0 < self.time_off < self.min_off:
                # time_off is too short, increase time_on proportionally
                self.time_on *= self.min_off / self.time_off
                self.time_off = self.min_off

            # Safety cap: never let dilatation stretch beyond 4x the base cycle
            max_cycle = self.pwm_interval * 4
            if self.time_on + self.time_off > max_cycle:
                # Demand is too low to be meaningful with min_on/min_off constraints
                self.time_on = 0.0
                self.time_off = self.pwm_interval

        total_cycle = self.time_on + self.time_off
        
        # If we exceeded the cycle duration, start a new cycle
        if time_passed >= total_cycle:
            self.cycle_start_time = now
            time_passed = 0.0
            
        # Determine state
        # In a PWM cycle, we start with ON, then go OFF
        if demand <= 0.0:
            self.current_state = False
        elif demand >= 100.0:
            self.current_state = True
        else:
            if time_passed < self.time_on:
                self.current_state = True
            else:
                self.current_state = False
                
        return self.current_state
