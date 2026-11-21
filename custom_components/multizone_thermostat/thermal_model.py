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
        self._is_cooling_active = False
        self._last_hvac_mode: str | None = None
        
        # Inertia tracking
        self._temp_at_shutdown = None
        self._shutdown_time = None
        self._max_temp_after_shutdown = None
        
        # Learned metrics (Exponential Moving Average)
        self.heating_rate = 0.0  # °C / hour
        self.cooling_rate = 0.0  # °C / hour (passive dispersion heat loss)
        self.active_cooling_rate = 0.0  # °C / hour (active cooling in COOL mode)
        self.thermal_inertia = 0.0  # °C overshoot

    def update(
        self,
        current_temp: float,
        is_heating: bool,
        hvac_mode: str | None = None,
        demand: float | None = None,
    ):
        """Update the observer with the latest temperature and state."""
        now = time.monotonic()
        mode_lower = str(hvac_mode).lower() if hvac_mode is not None else None

        if mode_lower == "cool":
            self._shutdown_time = None
            self._is_heating = False
            is_cooling_active = bool((demand is not None and demand > 0.0) or is_heating)
            if (
                self._last_temp is None
                or self._last_hvac_mode != "cool"
                or self._is_cooling_active != is_cooling_active
            ):
                self._last_temp = current_temp
                self._last_temp_time = now
                self._last_hvac_mode = "cool"
                self._is_cooling_active = is_cooling_active
                return

            delta_temp = current_temp - self._last_temp
            if abs(delta_temp) >= self.temp_delta_threshold:
                time_elapsed_hours = (now - self._last_temp_time) / 3600.0
                if time_elapsed_hours > 0.01 and is_cooling_active and delta_temp < 0:
                    if demand is None or demand >= 30.0:
                        duty = max(0.30, min(1.0, float(demand) / 100.0)) if demand is not None else 1.0
                        effective_rate = (abs(delta_temp) / time_elapsed_hours) / duty
                        self._update_ema('active_cooling_rate', effective_rate, alpha=0.1)
                        _LOGGER.debug("[%s] Active cooling rate updated: %.2f °C/hr", self.zone_id, self.active_cooling_rate)
                self._last_temp = current_temp
                self._last_temp_time = now
            return

        effective_heating = bool(is_heating and (demand is None or demand >= 10.0))

        if self._last_temp is None or self._last_hvac_mode == "cool":
            self._last_temp = current_temp
            self._last_temp_time = now
            self._is_heating = effective_heating
            self._is_cooling_active = False
            self._last_hvac_mode = mode_lower
            return

        self._last_hvac_mode = mode_lower

        if effective_heating:
            self._shutdown_time = None
        elif self._is_heating:
            # Transitioned from active heating to coast-down / low-demand shutdown
            self._temp_at_shutdown = current_temp
            self._shutdown_time = now
            self._max_temp_after_shutdown = current_temp
            _LOGGER.debug("[%s] Heating stopped. Tracking inertia starting from %.2f°C", self.zone_id, current_temp)

        # Update max temp after shutdown (only valid for 60 minutes after shutdown)
        if not effective_heating and self._shutdown_time is not None:
            if now - self._shutdown_time <= 3600:
                if current_temp > self._max_temp_after_shutdown:
                    self._max_temp_after_shutdown = current_temp
                elif current_temp <= self._max_temp_after_shutdown - 0.1:
                    # Peak reached (temperature started dropping)
                    inertia = max(0.0, self._max_temp_after_shutdown - self._temp_at_shutdown)
                    self._update_ema('thermal_inertia', inertia, alpha=0.1)
                    _LOGGER.debug("[%s] Inertia peak reached: +%.2f°C", self.zone_id, inertia)
                    self._shutdown_time = None
            else:
                inertia = max(0.0, self._max_temp_after_shutdown - self._temp_at_shutdown)
                self._update_ema('thermal_inertia', inertia, alpha=0.1)
                _LOGGER.debug("[%s] Inertia window closed: +%.2f°C", self.zone_id, inertia)
                self._shutdown_time = None  # Stop tracking inertia after 1 hour

        # Reset rate baseline when switching between heating and cooling so durations are not mixed
        if self._is_heating != effective_heating:
            self._last_temp = current_temp
            self._last_temp_time = now
            self._is_heating = effective_heating
            return

        # Calculate Rates (dT/dt) if temperature changed enough
        delta_temp = current_temp - self._last_temp
        
        if abs(delta_temp) >= self.temp_delta_threshold:
            time_elapsed_hours = (now - self._last_temp_time) / 3600.0
            
            if time_elapsed_hours > 0.01: # Ignore super rapid spikes (< 36 seconds)
                rate = abs(delta_temp) / time_elapsed_hours
                
                if self._is_heating and effective_heating and delta_temp > 0:
                    if demand is None or demand >= 30.0:
                        duty = max(0.30, min(1.0, float(demand) / 100.0)) if demand is not None else 1.0
                        effective_rate = rate / duty
                        self._update_ema('heating_rate', effective_rate, alpha=0.1)
                        _LOGGER.debug("[%s] Heating rate updated: %.2f °C/hr", self.zone_id, self.heating_rate)
                elif not self._is_heating and not is_heating and delta_temp < 0:
                    self._update_ema('cooling_rate', rate, alpha=0.1)
                    _LOGGER.debug("[%s] Cooling rate updated: %.2f °C/hr", self.zone_id, self.cooling_rate)

            # Reset tracking point
            self._last_temp = current_temp
            self._last_temp_time = now
            
        self._is_heating = effective_heating

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
            "active_cooling_rate": self.active_cooling_rate,
            "thermal_inertia": self.thermal_inertia
        }

    def load_state(self, state: dict):
        """Load learned metrics from storage."""
        self.heating_rate = state.get("heating_rate", 0.0)
        self.cooling_rate = state.get("cooling_rate", 0.0)
        self.active_cooling_rate = state.get("active_cooling_rate", 0.0)
        self.thermal_inertia = state.get("thermal_inertia", 0.0)

    def get_weather_multiplier(self, manual_base_curve: float = 0.0) -> float:
        """
        Calculate the weather compensation multiplier (Ke) based on thermal metrics.
        Returns 0.0 when weather compensation is disabled (manual_base_curve <= 0).
        """
        if manual_base_curve <= 0.0:
            return 0.0

        if self.heating_rate > 0.1 and self.cooling_rate > 0.01:
            # Dispersion ratio normalized around typical baseline (~0.15) to bend +/- 50%
            adaptive_curve = self.cooling_rate / self.heating_rate
            bend_factor = max(0.5, min(1.5, adaptive_curve / 0.15))
            return manual_base_curve * bend_factor
            
        return manual_base_curve
