"""HVAC Plant Diagnostics, Anomaly Detection & Building Energy Efficiency Engine."""
from __future__ import annotations

import logging
import time
from typing import Any
from collections import deque

from ..const import CONF_ZONE_NAME, make_zone_entity_id
from .const import (
    ANOMALY_NONE,
    ANOMALY_VALVE_STUCK_CLOSED,
    ANOMALY_GHOST_HEATING,
    ANOMALY_STALE_SENSOR,
    ANOMALY_BOILER_FAULT,
    ANOMALY_BOILER_LOW_PRESSURE,
    ANOMALY_LOW_BATTERY,
    ANOMALY_SENSOR_FAULT,
    ANOMALY_SENSOR_TIMEOUT,
)

from .anomalies import (
    get_battery_level,
    get_zone_battery_level,
    get_opentherm_diagnostics,
    evaluate_zone_anomalies,
)
from .efficiency import (
    get_zone_energy_class,
    get_zone_thermal_retention_hours,
    get_zone_radiator_sizing,
)

_LOGGER = logging.getLogger(__name__)


class PlantDiagnosticsEngine:
    """Evaluates physical heating plant health, detects anomalies and computes building efficiency."""

    def __init__(self, coordinator: Any) -> None:
        """Initialize the plant diagnostics engine."""
        self.coordinator = coordinator
        self.hass = coordinator.hass

        # Boiler tracking
        self._boiler_on_events: deque[float] = deque(maxlen=200) # Timestamps when boiler turned ON
        self._boiler_run_intervals: deque[tuple[float, float]] = deque(maxlen=1000) # (start, end)
        self._current_boiler_start: float | None = None

        # Zone tracking state for anomalies
        self._zone_anomaly_state: dict[str, dict[str, Any]] = {}
        for zone in coordinator.zones:
            climate_id = make_zone_entity_id(zone[CONF_ZONE_NAME])
            self._zone_anomaly_state[climate_id] = {
                "active_anomaly": ANOMALY_NONE,
                "anomaly_details": "No anomaly detected",
                "high_demand_start_time": None,
                "high_demand_start_temp": None,
                "ghost_heat_start_temp": None,
                "last_temp_seen": None,
                "last_temp_time": None,
                "last_heating_time": None,
            }

    # ------------------------------------------------------------------
    # Boiler Metrics
    # ------------------------------------------------------------------

    def record_boiler_state(self, is_on: bool) -> None:
        """Record a boiler switch ON or OFF transition."""
        now = time.monotonic()
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
        now = time.monotonic()
        one_hour_ago = now - 3600.0
        return sum(1 for t in self._boiler_on_events if t >= one_hour_ago)

    def get_boiler_daily_runtime_hours(self) -> float:
        """Calculate total boiler running hours in the past 24 hours."""
        now = time.monotonic()
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
    # Delegation to Modules
    # ------------------------------------------------------------------

    def get_battery_level(self, entity_id: str) -> int | None:
        return get_battery_level(self.hass, entity_id)

    def get_zone_battery_level(self, climate_id: str) -> int | None:
        return get_zone_battery_level(self.coordinator, self.hass, climate_id)

    def get_opentherm_diagnostics(self) -> dict[str, Any]:
        return get_opentherm_diagnostics(self.coordinator, self.hass)

    def evaluate_zone_anomalies(self, climate_id: str) -> tuple[str, str]:
        state = self._zone_anomaly_state.setdefault(climate_id, {
            "active_anomaly": ANOMALY_NONE,
            "anomaly_details": "No anomaly detected",
            "high_demand_start_time": None,
            "high_demand_start_temp": None,
            "ghost_heat_start_temp": None,
            "last_temp_seen": None,
            "last_temp_time": None,
            "last_heating_time": None,
        })
        boiler_on = self.coordinator.get_master_state() and self._current_boiler_start is not None
        return evaluate_zone_anomalies(self.coordinator, self.hass, climate_id, state, boiler_on)

    def get_zone_energy_class(self, climate_id: str) -> str:
        return get_zone_energy_class(self.coordinator, self.hass, climate_id)

    def get_zone_thermal_retention_hours(self, climate_id: str) -> float | None:
        return get_zone_thermal_retention_hours(self.coordinator, climate_id)

    def get_zone_radiator_sizing(self, climate_id: str) -> str:
        return get_zone_radiator_sizing(self.coordinator, climate_id)

    def has_critical_sensor_fault(self, climate_id: str) -> bool:
        """Return True if the zone sensor has a low battery, implausible reading, or watchdog timeout."""
        state = self._zone_anomaly_state.get(climate_id)
        if not state:
            return False
        anomaly = state.get("active_anomaly")
        if anomaly == ANOMALY_SENSOR_TIMEOUT and state.get("fallback_ok"):
            # Degraded: a valid TRV fallback measurement exists, keep heating.
            return False
        return anomaly in (ANOMALY_LOW_BATTERY, ANOMALY_SENSOR_FAULT, ANOMALY_SENSOR_TIMEOUT)

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
                "zone": "Boiler",
                "climate_id": "boiler",
                "type": "short_cycling",
                "description": f"High cycle frequency: {cycles} cycles/hour (possible wear or oversizing)",
            })

        # OpenTherm Diagnostics & Anomalies
        ot_diag = self.get_opentherm_diagnostics()
        if ot_diag.get("enabled"):
            # Check Low Pressure
            press = ot_diag.get("water_pressure")
            if press is not None and press < 0.8:
                anomalies_found.append({
                    "zone": "Boiler Plant",
                    "climate_id": "boiler_pressure",
                    "type": ANOMALY_BOILER_LOW_PRESSURE,
                    "description": f"Low circuit pressure ({press:.1f} bar). Refill circuit to 1.2 - 1.5 bar",
                })
            # Check Boiler Fault
            if ot_diag.get("fault_active"):
                code = ot_diag.get("fault_code", "Active")
                anomalies_found.append({
                    "zone": "Boiler Plant",
                    "climate_id": "boiler_fault",
                    "type": ANOMALY_BOILER_FAULT,
                    "description": f"OpenTherm generator fault alarm (Code: {code})",
                })

        if not anomalies_found:
            status = "optimal"
            label = "Optimal"
        elif any(a["type"] in (ANOMALY_VALVE_STUCK_CLOSED, ANOMALY_GHOST_HEATING, ANOMALY_STALE_SENSOR, ANOMALY_BOILER_FAULT) for a in anomalies_found):
            status = "critical"
            label = "Critical"
        else:
            status = "warning"
            label = "Warning"

        return {
            "status": status,
            "label": label,
            "anomalies_count": len(anomalies_found),
            "anomalies": anomalies_found,
            "cycles_per_hour": cycles,
            "daily_runtime_hours": self.get_boiler_daily_runtime_hours(),
            "opentherm": ot_diag,
        }
