"""HVAC Plant Diagnostics, Anomaly Detection & Building Energy Efficiency Engine."""
from __future__ import annotations

import logging
import time
from typing import Any
from collections import deque

from .const import CONF_ZONE_NAME, CONF_ZONE_ALLOW_PASSIVE_HEAT, make_zone_entity_id

_LOGGER = logging.getLogger(__name__)

# Anomaly Types
ANOMALY_NONE = "none"
ANOMALY_VALVE_STUCK_CLOSED = "valve_stuck_closed"
ANOMALY_GHOST_HEATING = "ghost_heating"
ANOMALY_AIR_IN_RADIATOR = "air_in_radiator"
ANOMALY_STALE_SENSOR = "stale_sensor"
ANOMALY_OVERSHOOT = "overshoot"

# Human-readable anomaly labels (Italian)
ANOMALY_LABELS = {
    ANOMALY_NONE: "Nessuna anomalia",
    ANOMALY_VALVE_STUCK_CLOSED: "Possibile valvola bloccata chiusa / Nessun apporto termico",
    ANOMALY_GHOST_HEATING: "Possibile trafilamento o valvola aperta (Riscaldamento fantasma)",
    ANOMALY_AIR_IN_RADIATOR: "Calo di resa termica (Possibile aria nel radiatore)",
    ANOMALY_STALE_SENSOR: "Sensore temperatura non aggiornato da oltre 2 ore",
    ANOMALY_OVERSHOOT: "Superamento anomalo temperatura impostata (>1.5°C)",
}


class PlantDiagnosticsEngine:
    """Evaluates physical heating plant health, detects anomalies and computes building efficiency."""

    def __init__(self, coordinator: Any) -> None:
        """Initialize the plant diagnostics engine."""
        self.coordinator = coordinator
        self.hass = coordinator.hass

        # Boiler tracking
        self._boiler_on_events: deque[float] = deque(maxlen=200) # Timestamps when boiler turned ON
        self._boiler_run_intervals: deque[tuple[float, float]] = deque(maxlen=300) # (start, end)
        self._current_boiler_start: float | None = None

        # Zone tracking state for anomalies
        self._zone_anomaly_state: dict[str, dict[str, Any]] = {}
        for zone in coordinator.zones:
            climate_id = make_zone_entity_id(zone[CONF_ZONE_NAME])
            self._zone_anomaly_state[climate_id] = {
                "active_anomaly": ANOMALY_NONE,
                "anomaly_details": "Nessuna anomalia rilevata",
                "high_demand_start_time": None,
                "high_demand_start_temp": None,
                "ghost_heat_start_temp": None,
                "last_temp_seen": None,
                "last_temp_time": None,
            }

    # ------------------------------------------------------------------
    # Boiler Metrics
    # ------------------------------------------------------------------

    def record_boiler_state(self, is_on: bool) -> None:
        """Record a boiler switch ON or OFF transition."""
        now = time.time()
        try:
            if is_on:
                if self._current_boiler_start is None:
                    self._boiler_on_events.append(now)
                    self._current_boiler_start = now
            else:
                if self._current_boiler_start is not None:
                    self._boiler_run_intervals.append((self._current_boiler_start, now))
                    self._current_boiler_start = None
        except Exception as err:
            _LOGGER.debug("Error recording boiler state in plant diagnostics: %s", err)

    def get_boiler_cycles_per_hour(self) -> int:
        """Calculate boiler ignition cycles in the past 60 minutes."""
        now = time.time()
        one_hour_ago = now - 3600.0
        return sum(1 for t in self._boiler_on_events if t >= one_hour_ago)

    def get_boiler_daily_runtime_hours(self) -> float:
        """Calculate total boiler running hours in the past 24 hours."""
        now = time.time()
        twenty_four_hours_ago = now - 86400.0
        total_seconds = 0.0

        for start, end in self._boiler_run_intervals:
            if end >= twenty_four_hours_ago:
                actual_start = max(start, twenty_four_hours_ago)
                total_seconds += max(0.0, end - actual_start)

        # Include currently active run if any
        if self._current_boiler_start is not None:
            actual_start = max(self._current_boiler_start, twenty_four_hours_ago)
            total_seconds += max(0.0, now - actual_start)

        return round(total_seconds / 3600.0, 1)

    # ------------------------------------------------------------------
    # Zone Anomaly Evaluation
    # ------------------------------------------------------------------

    def evaluate_zone_anomalies(self, climate_id: str) -> tuple[str, str]:
        """
        Evaluate if a zone exhibits mechanical, hydraulic or sensor anomalies.
        Returns: (anomaly_type, human_readable_description)
        """
        try:
            state = self._zone_anomaly_state.setdefault(climate_id, {
                "active_anomaly": ANOMALY_NONE,
                "anomaly_details": "Nessuna anomalia rilevata",
                "high_demand_start_time": None,
                "high_demand_start_temp": None,
                "ghost_heat_start_temp": None,
                "last_temp_seen": None,
                "last_temp_time": None,
            })

            now = time.time()
            st = self.hass.states.get(climate_id)
            if not st:
                return ANOMALY_NONE, "Zona non pronta"

            current_temp = st.attributes.get("current_temperature")
            target_temp = st.attributes.get("temperature")
            demand = self.coordinator.get_zone_demand(climate_id)
            boiler_on = self.coordinator.get_master_state() and (self.get_boiler_cycles_per_hour() > 0 or self._current_boiler_start is not None)

            if current_temp is None:
                return ANOMALY_NONE, "In attesa lettura temperatura"

            current_temp = float(current_temp)

            # 1. Staleness Check: Has the temperature sensor not updated in > 2 hours?
            if state["last_temp_seen"] is None or state["last_temp_seen"] != current_temp:
                state["last_temp_seen"] = current_temp
                state["last_temp_time"] = now
            elif state["last_temp_time"] is not None and (now - state["last_temp_time"]) > 7200:
                # Same exact float value for > 2 hours
                state["active_anomaly"] = ANOMALY_STALE_SENSOR
                state["anomaly_details"] = ANOMALY_LABELS[ANOMALY_STALE_SENSOR]
                return ANOMALY_STALE_SENSOR, state["anomaly_details"]

            # 2. Overshoot Check: Only when heating is active (boiler ON and demand > 0)
            # If the boiler is OFF or demand is 0, warm room temperature is simply natural ambient/solar heat, NOT a heating overshoot!
            if boiler_on and demand > 0.0 and target_temp is not None and current_temp > (float(target_temp) + 1.5):
                state["active_anomaly"] = ANOMALY_OVERSHOOT
                state["anomaly_details"] = f"Temperatura attuale ({current_temp}°C) supera il target ({target_temp}°C) di oltre 1.5°C durante il riscaldamento"
                return ANOMALY_OVERSHOOT, state["anomaly_details"]

            # 3. Stuck Closed Valve: Demand == 100% for > 75 min, but temperature did not rise >= 0.2°C
            if demand >= 99.0 and boiler_on:
                if state["high_demand_start_time"] is None:
                    state["high_demand_start_time"] = now
                    state["high_demand_start_temp"] = current_temp
                elif (now - state["high_demand_start_time"]) > 4500:  # 75 minutes
                    start_t = state["high_demand_start_temp"]
                    if start_t is not None and (current_temp - start_t) < 0.2:
                        state["active_anomaly"] = ANOMALY_VALVE_STUCK_CLOSED
                        state["anomaly_details"] = f"Riscaldamento attivo al 100% da oltre 75 min ma la temperatura non sale ({start_t}°C → {current_temp}°C)"
                        return ANOMALY_VALVE_STUCK_CLOSED, state["anomaly_details"]
            else:
                # Reset stuck-closed tracker if demand dropped below 99%
                state["high_demand_start_time"] = None
                state["high_demand_start_temp"] = None

            # Lookup zone configuration to check if passive heat is expected
            allow_passive_heat = False
            for z in getattr(self.coordinator, "zones", []):
                if make_zone_entity_id(z.get(CONF_ZONE_NAME, "")) == climate_id:
                    allow_passive_heat = bool(z.get(CONF_ZONE_ALLOW_PASSIVE_HEAT, False))
                    break

            # 4. Ghost Heating / Stuck Open: Zone is OFF or demand is 0, but room temp rose > 0.8°C while boiler running
            if demand <= 0.0 and boiler_on:
                if allow_passive_heat:
                    # Passive heat allowed (fan coil without shut-off valve, open mezzanine, etc.)
                    state["ghost_heat_start_temp"] = None
                elif state["ghost_heat_start_temp"] is None:
                    state["ghost_heat_start_temp"] = current_temp
                elif (current_temp - state["ghost_heat_start_temp"]) > 0.8:
                    state["active_anomaly"] = ANOMALY_GHOST_HEATING
                    state["anomaly_details"] = f"Temperatura salita da {state['ghost_heat_start_temp']}°C a {current_temp}°C con zona a 0% richiesta"
                    return ANOMALY_GHOST_HEATING, state["anomaly_details"]
            else:
                state["ghost_heat_start_temp"] = None

            # No active anomaly
            state["active_anomaly"] = ANOMALY_NONE
            state["anomaly_details"] = ANOMALY_LABELS[ANOMALY_NONE]
            return ANOMALY_NONE, state["anomaly_details"]

        except Exception as err:
            _LOGGER.debug("Error in evaluate_zone_anomalies for %s: %s", climate_id, err)
            return ANOMALY_NONE, "Errore valutazione"

    # ------------------------------------------------------------------
    # Building Energy Efficiency & Thermal Metrics
    # ------------------------------------------------------------------

    def get_zone_energy_class(self, climate_id: str) -> str:
        """
        Estimate theoretical energy class (A4 to G) based on SAT dispersion metrics.
        """
        try:
            thermal = self.coordinator.get_thermal_model(climate_id)
            if not thermal or thermal.cooling_rate <= 0.02:
                return "In apprendimento..."

            st = self.hass.states.get(climate_id)
            current_temp = float(st.attributes.get("current_temperature", 20.0)) if st else 20.0

            # Outdoor temperature lookup
            outdoor_temp = None
            if self.coordinator.weather_sensor_id:
                w_st = self.hass.states.get(self.coordinator.weather_sensor_id)
                if w_st and w_st.state not in ("unavailable", "unknown"):
                    try:
                        outdoor_temp = float(w_st.attributes.get("temperature", w_st.state))
                    except (ValueError, TypeError):
                        pass

            # If weather is mild (inside - outside < 7.0°C), thermal gradient is too small for reliable calculation
            if outdoor_temp is not None:
                delta_t = current_temp - outdoor_temp
                if delta_t < 7.0:
                    return "In apprendimento..."
                normalized_dispersion = (thermal.cooling_rate / delta_t) * 20.0
            else:
                normalized_dispersion = thermal.cooling_rate

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

    def get_zone_thermal_retention_hours(self, climate_id: str) -> float | None:
        """Calculate how many hours the room takes to lose 1°C."""
        try:
            thermal = self.coordinator.get_thermal_model(climate_id)
            if not thermal or thermal.cooling_rate < 0.05:
                return None
            return round(1.0 / thermal.cooling_rate, 1)
        except Exception:
            return None

    def get_zone_radiator_sizing(self, climate_id: str) -> str:
        """
        Evaluate if the radiator / heating emitter is undersized, optimal, or oversized
        relative to the room's heat loss rate.
        """
        try:
            thermal = self.coordinator.get_thermal_model(climate_id)
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

    def get_plant_health_summary(self) -> dict[str, Any]:
        """
        Return the overall plant health rating, active anomaly count, and status details.
        """
        anomalies_found = []
        for zone in self.coordinator.zones:
            climate_id = make_zone_entity_id(zone[CONF_ZONE_NAME])
            anomaly_type, desc = self.evaluate_zone_anomalies(climate_id)
            if anomaly_type != ANOMALY_NONE:
                anomalies_found.append({
                    "zone": zone["name"],
                    "climate_id": climate_id,
                    "type": anomaly_type,
                    "description": desc,
                })

        # Check boiler short-cycling (> 5 cycles / hour)
        cycles = self.get_boiler_cycles_per_hour()
        if cycles > 5:
            anomalies_found.append({
                "zone": "Caldaia",
                "climate_id": "boiler",
                "type": "short_cycling",
                "description": f"Frequenza accensioni elevata: {cycles} cicli/ora (possibile usura o sovradimensionamento)",
            })

        if not anomalies_found:
            status = "optimal"
            label = "Ottimale"
        elif any(a["type"] in (ANOMALY_VALVE_STUCK_CLOSED, ANOMALY_GHOST_HEATING, ANOMALY_STALE_SENSOR) for a in anomalies_found):
            status = "critical"
            label = "Critico"
        else:
            status = "warning"
            label = "Attenzione"

        return {
            "status": status,
            "label": label,
            "anomalies_count": len(anomalies_found),
            "anomalies": anomalies_found,
            "cycles_per_hour": cycles,
            "daily_runtime_hours": self.get_boiler_daily_runtime_hours(),
        }
