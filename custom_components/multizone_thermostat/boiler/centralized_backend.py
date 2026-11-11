"""Centralized / condo heating backend (no master boiler hardware)."""
from __future__ import annotations

from typing import Any
from .base import BoilerBackend


class CentralizedBoilerBackend(BoilerBackend):
    """Handles centralized/condo installations without local boiler/heater."""

    def __init__(self, hass: Any = None, coordinator: Any = None) -> None:
        """Initialize centralized backend."""
        self.hass = hass
        self.coordinator = coordinator
        self._status_reason = "CENTRALIZED - Idle"
        self._last_demand = 0.0

    async def async_update(
        self, demand: float, peak_zone: str | None, frost_emergency: bool
    ) -> None:
        """Update centralized state based on total demand."""
        self._last_demand = float(demand or 0.0)
        if self._last_demand > 0:
            self._status_reason = f"CENTRALIZED - Active (Demand: {self._last_demand:.1f}%)"
        else:
            self._status_reason = "CENTRALIZED - Idle"

    async def async_emergency_off(self) -> None:
        """Handle emergency off."""
        self._last_demand = 0.0
        self._status_reason = "CENTRALIZED - Off"

    @property
    def status_reason(self) -> str:
        """Return current status reason."""
        return self._status_reason

    @property
    def is_on(self) -> bool:
        """Return whether centralized heat is actively demanded."""
        return self._last_demand > 0
