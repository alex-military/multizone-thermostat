import logging
import time
from collections import deque
from datetime import datetime

_LOGGER = logging.getLogger(__name__)

class PassiveAutotuneObserver:
    """
    Observes natural ON/OFF cycles (Hysteresis) to calculate PID parameters
    using the Ziegler-Nichols Open-Loop / Reaction Curve method for integrating processes.
    """

    STATE_IDLE = "idle"
    STATE_HEATING = "heating"
    STATE_COOLING = "cooling"
    STATE_COMPLETED = "completed"

    def __init__(self, zone_name: str, required_cycles: int = 3):
        self.zone_name = zone_name
        self.required_cycles = required_cycles
        self.state = self.STATE_IDLE
        
        self.history = deque(maxlen=1000)  # Stores (timestamp, temperature)
        self.completed_cycles = []         # Stores dict of {L, slope, Kp, Ki, Kd}
        
        self.cycle_start_time = None
        self.cycle_start_temp = None
        
        self.kp = 0.0
        self.ki = 0.0
        self.kd = 0.0
        
    def load_state(self, data: dict):
        """Restore state from storage."""
        if not data:
            return
        self.completed_cycles = data.get("completed_cycles", [])
        if len(self.completed_cycles) >= self.required_cycles:
            self.state = self.STATE_COMPLETED
            self._compute_final_pid()
            
    def dump_state(self) -> dict:
        """Dump state for storage."""
        return {
            "completed_cycles": self.completed_cycles
        }
        
    def update(self, current_temp: float, is_heating: bool, now: float = None):
        """Called periodically or on state change."""
        if now is None:
            now = time.time()
        
        
        if self.state == self.STATE_COMPLETED:
            return
            
        if self.state == self.STATE_IDLE:
            if is_heating:
                self._start_heating(now, current_temp)
                
        elif self.state == self.STATE_HEATING:
            self.history.append((now, current_temp))
            if not is_heating:
                self._stop_heating(now, current_temp)
                
        elif self.state == self.STATE_COOLING:
            if is_heating:
                self._start_heating(now, current_temp)

    def _start_heating(self, now: float, temp: float):
        _LOGGER.info("Autotune [%s]: Heating started. Recording cycle.", self.zone_name)
        self.state = self.STATE_HEATING
        self.cycle_start_time = now
        self.cycle_start_temp = temp
        self.history.clear()
        self.history.append((now, temp))
        
    def _stop_heating(self, now: float, temp: float):
        _LOGGER.info("Autotune [%s]: Heating stopped. Analyzing cycle...", self.zone_name)
        self.state = self.STATE_COOLING
        
        # Analyze the collected history
        if len(self.history) < 5:
            _LOGGER.warning("Autotune [%s]: Not enough data points.", self.zone_name)
            return
            
        # Calculate slopes over a sliding window (e.g. 5 minutes)
        max_slope = -999.0
        max_slope_t = None
        max_slope_temp = None
        
        history_list = list(self.history)
        
        for i in range(len(history_list)):
            t1, temp1 = history_list[i]
            # Find a point roughly 3-5 minutes later
            for j in range(i+1, len(history_list)):
                t2, temp2 = history_list[j]
                dt = t2 - t1
                if dt >= 180:  # At least 3 minutes diff to avoid noise
                    slope = (temp2 - temp1) / dt
                    if slope > max_slope:
                        max_slope = slope
                        # We use the midpoint of the interval for the tangent line
                        max_slope_t = t1 + (dt / 2.0)
                        max_slope_temp = temp1 + (temp2 - temp1) / 2.0
                    break # Move to next i once we found a 3+ min window
                    
        # If we didn't find any 3-min window, fallback to overall slope
        if max_slope_t is None:
            t1, temp1 = history_list[0]
            t2, temp2 = history_list[-1]
            dt = t2 - t1
            if dt < 60.0:
                _LOGGER.warning("Autotune [%s]: Fallback slope dt too short (%.1fs). Cycle discarded.", self.zone_name, dt)
                return
            if dt > 0:
                max_slope = (temp2 - temp1) / dt
                max_slope_t = t1 + (dt / 2.0)
                max_slope_temp = temp1 + (temp2 - temp1) / 2.0
                
        if max_slope <= 0.0001:
            _LOGGER.warning("Autotune [%s]: Invalid slope %.4f. Cycle discarded.", self.zone_name, max_slope)
            return
            
        # Find L (Dead Time)
        t0 = (self.cycle_start_temp - max_slope_temp) / max_slope + max_slope_t
        L = t0 - self.cycle_start_time
        
        if L < 60.0:
            _LOGGER.info("Autotune [%s]: Dead time too short (%.1fs), clamping to 60s.", self.zone_name, L)
            L = 60.0
            
        if L > 7200.0:
            _LOGGER.warning("Autotune [%s]: Dead time too long (%.1fs). Cycle discarded.", self.zone_name, L)
            return
            
        kp_calc = 120.0 / (max_slope * L)
        ti_calc = 2.0 * L
        td_calc = 0.5 * L
        
        ki_calc = kp_calc / ti_calc if ti_calc > 0 else 0
        kd_calc = kp_calc * td_calc
        
        # Clamp Kp to reasonable bounds to avoid insane values
        kp_calc = min(max(kp_calc, 10.0), 500.0)
        
        _LOGGER.info("Autotune [%s]: Cycle valid! L=%.1f s, slope=%.6f °C/s. Kp=%.1f, Ki=%.4f, Kd=%.1f", 
                     self.zone_name, L, max_slope, kp_calc, ki_calc, kd_calc)
                     
        self.completed_cycles.append({
            "L": L,
            "slope": max_slope,
            "Kp": kp_calc,
            "Ki": ki_calc,
            "Kd": kd_calc,
            "timestamp": now
        })
        
        if len(self.completed_cycles) >= self.required_cycles:
            _LOGGER.info("Autotune [%s]: Required cycles reached. Learning completed!", self.zone_name)
            self.state = self.STATE_COMPLETED
            self._compute_final_pid()
            
    def _compute_final_pid(self):
        """Average the valid cycles to find final PID parameters."""
        if not self.completed_cycles:
            return
            
        avg_kp = sum(c["Kp"] for c in self.completed_cycles) / len(self.completed_cycles)
        avg_ki = sum(c["Ki"] for c in self.completed_cycles) / len(self.completed_cycles)
        avg_kd = sum(c["Kd"] for c in self.completed_cycles) / len(self.completed_cycles)
        
        self.kp = avg_kp
        self.ki = avg_ki
        self.kd = avg_kd
        
        _LOGGER.info("Autotune [%s]: FINAL PID: Kp=%.1f, Ki=%.4f, Kd=%.1f", self.zone_name, self.kp, self.ki, self.kd)
