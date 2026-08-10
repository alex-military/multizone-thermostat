"""Advanced Room Thermal Model (SAT) module."""
import time
import logging

_LOGGER = logging.getLogger(__name__)

class ThermalObserver:
    """Observes room temperature to learn thermal capacity, dispersion, and inertia."""

    def __init__(self, zone_id: str, temp_delta_threshold: float = 0.1):
        """Initialize the thermal observer."""
        self.zone_id = zone_id
        self.temp_delta_threshold = temp_delta_threshold
        
        # State tracking
        self._last_temp = None
        self._last_temp_time = None
        self._is_heating = False
        
        # Inertia tracking
        self._temp_at_shutdown = None
        self._shutdown_time = None
        self._max_temp_after_shutdown = None
        
        # Learned metrics (Exponential Moving Average)
        self.heating_rate = 0.0  # °C / hour
        self.cooling_rate = 0.0  # °C / hour
        self.thermal_inertia = 0.0  # °C overshoot

    def update(self, current_temp: float, is_heating: bool):
        """Update the observer with the latest temperature and state."""
        now = time.time()
        
        if self._last_temp is None:
            self._last_temp = current_temp
            self._last_temp_time = now
            self._is_heating = is_heating
            return

        # Track Thermal Inertia when transitioning from HEATING to OFF
        if self._is_heating and not is_heating:
            self._temp_at_shutdown = current_temp
            self._shutdown_time = now
            self._max_temp_after_shutdown = current_temp
            _LOGGER.debug("[%s] Heating stopped. Tracking inertia starting from %.2f°C", self.zone_id, current_temp)
            
        # Update max temp after shutdown (only valid for 60 minutes after shutdown)
        if not is_heating and self._shutdown_time is not None:
            if now - self._shutdown_time <= 3600:
                if current_temp > self._max_temp_after_shutdown:
                    self._max_temp_after_shutdown = current_temp
                    inertia = self._max_temp_after_shutdown - self._temp_at_shutdown
                    self._update_ema('thermal_inertia', inertia, alpha=0.1)
                    _LOGGER.debug("[%s] Inertia peak updated: +%.2f°C", self.zone_id, inertia)
            else:
                self._shutdown_time = None  # Stop tracking inertia after 1 hour

        # Calculate Rates (dT/dt) if temperature changed enough
        delta_temp = current_temp - self._last_temp
        
        if abs(delta_temp) >= self.temp_delta_threshold:
            time_elapsed_hours = (now - self._last_temp_time) / 3600.0
            
            if time_elapsed_hours > 0.01: # Ignore super rapid spikes (< 36 seconds)
                rate = abs(delta_temp) / time_elapsed_hours
                
                if self._is_heating and is_heating and delta_temp > 0:
                    self._update_ema('heating_rate', rate, alpha=0.1)
                    _LOGGER.debug("[%s] Heating rate updated: %.2f °C/hr", self.zone_id, self.heating_rate)
                elif not self._is_heating and not is_heating and delta_temp < 0:
                    self._update_ema('cooling_rate', rate, alpha=0.1)
                    _LOGGER.debug("[%s] Cooling rate updated: %.2f °C/hr", self.zone_id, self.cooling_rate)

            # Reset tracking point
            self._last_temp = current_temp
            self._last_temp_time = now
            
        self._is_heating = is_heating

    def _update_ema(self, attribute: str, new_value: float, alpha: float = 0.1):
        """Update Exponential Moving Average."""
        current_value = getattr(self, attribute)
        if current_value == 0.0:
            setattr(self, attribute, new_value)
        else:
            setattr(self, attribute, (alpha * new_value) + ((1.0 - alpha) * current_value))

    def dump_state(self) -> dict:
        """Dump the learned metrics for storage."""
        return {
            "heating_rate": self.heating_rate,
            "cooling_rate": self.cooling_rate,
            "thermal_inertia": self.thermal_inertia
        }

    def load_state(self, state: dict):
        """Load learned metrics from storage."""
        self.heating_rate = state.get("heating_rate", 0.0)
        self.cooling_rate = state.get("cooling_rate", 0.0)
        self.thermal_inertia = state.get("thermal_inertia", 0.0)
