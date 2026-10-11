"""Building Energy Efficiency & Thermal Metrics."""
from __future__ import annotations

import logging
from typing import Any
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

def get_zone_energy_class(coordinator: Any, hass: HomeAssistant, climate_id: str) -> str:
    """
    Estimate theoretical energy class (A4 to G) based on SAT dispersion metrics.
    """
    try:
        thermal = coordinator.zone_controller.get_thermal_model(climate_id)
        if not thermal or thermal.cooling_rate <= 0.02:
            return "In apprendimento..."

        st = hass.states.get(climate_id)
        current_temp = float(st.attributes.get("current_temperature", 20.0)) if st else 20.0

        # Outdoor temperature lookup
        outdoor_temp = None
        if coordinator.weather_sensor_id:
            w_st = hass.states.get(coordinator.weather_sensor_id)
            if w_st and w_st.state not in ("unavailable", "unknown"):
                try:
                    outdoor_temp = float(w_st.attributes.get("temperature", w_st.state))
                except (ValueError, TypeError):
                    pass

        # If weather is mild (inside - outside < 7.0°C), thermal gradient is too small for reliable calculation
        if outdoor_temp is None:
            return "In apprendimento..."
            
        delta_t = current_temp - outdoor_temp
        if delta_t < 7.0:
            return "In apprendimento..."
        normalized_dispersion = (thermal.cooling_rate / delta_t) * 20.0

        # Scale mapping: European Energy Efficiency Class
        if normalized_dispersion < 0.25:
            return "A4"
        elif normalized_dispersion < 0.40:
            return "A"
        elif normalized_dispersion < 0.60:
            return "B"
        elif normalized_dispersion < 0.85:
            return "C"
        elif normalized_dispersion < 1.15:
            return "D"
        elif normalized_dispersion < 1.50:
            return "E"
        elif normalized_dispersion < 1.90:
            return "F"
        else:
            return "G"

    except Exception as err:
        _LOGGER.debug("Error calculating energy class for %s: %s", climate_id, err)
        return "Non disponibile"

def get_zone_thermal_retention_hours(coordinator: Any, climate_id: str) -> float | None:
    """Calculate how many hours the room takes to lose 1°C."""
    try:
        thermal = coordinator.zone_controller.get_thermal_model(climate_id)
        if not thermal or thermal.cooling_rate < 0.05:
            return None
        return round(1.0 / thermal.cooling_rate, 1)
    except Exception:
        return None

def get_zone_radiator_sizing(coordinator: Any, climate_id: str) -> str:
    """
    Evaluate if the radiator / heating emitter is undersized, optimal, or oversized
    relative to the room's heat loss rate.
    """
    try:
        thermal = coordinator.zone_controller.get_thermal_model(climate_id)
        if not thermal or thermal.heating_rate < 0.1 or thermal.cooling_rate < 0.05:
            return "In apprendimento..."

        ratio = thermal.heating_rate / thermal.cooling_rate
        if ratio < 1.3:
            return "Sottodimensionato"
        elif ratio <= 3.8:
            return "Ottimale"
        else:
            return "Sovradimensionato"
    except Exception:
        return "In apprendimento..."
