"""Protocol definitions for Multizone Thermostat subsystems."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class BoilerBackendProtocol(Protocol):
    """Contract for all heating/cooling generator backends."""

    is_modulating: bool

    @property
    def status_reason(self) -> str:
        """Return current human-readable status reason."""
        ...

    async def async_update(
        self, demand: float, peak_zone: str | None, frost_emergency: bool, *args: Any, **kwargs: Any
    ) -> None:
        """Apply aggregated plant demand to the generator."""
        ...

    async def async_emergency_off(self) -> None:
        """Force generator off immediately."""
        ...

    def cancel_pending_tasks(self) -> None:
        """Cancel any scheduled delayed tasks."""
        ...


@runtime_checkable
class PlantOrchestratorProtocol(Protocol):
    """Contract for central plant orchestration."""

    @property
    def is_modulating_plant(self) -> bool:
        """Return True if the active plant modulates."""
        ...

    @property
    def is_dhw_active(self) -> bool:
        """Return True if DHW production is currently active."""
        ...

    @property
    def boiler_status_reason(self) -> str:
        """Return current plant status reason."""
        ...

    async def async_tick(self, now: datetime) -> None:
        """Periodic plant tick."""
        ...

    async def async_refresh(self, force_refresh_zones: bool = False) -> None:
        """Immediately refresh plant demand and generator state."""
        ...


@runtime_checkable
class ZoneControllerProtocol(Protocol):
    """Contract for per-zone PID/autotune management."""

    def get_pid(self, climate_id: str, mode: str = "heat") -> Any | None:
        """Return PID wrapper for a zone and mode."""
        ...

    def get_autotuner(self, climate_id: str, mode: str = "heat") -> Any | None:
        """Return autotuner for a zone and mode."""
        ...

    def get_thermal_model(self, climate_id: str) -> Any | None:
        """Return thermal observer model for a zone."""
        ...

    async def async_update_zone(self, entity_id: str, new_state: Any) -> float:
        """Recalculate zone demand."""
        ...


@runtime_checkable
class CoordinatorProtocol(Protocol):
    """Contract for MultizoneCoordinator exposed to subsystems."""

    hass: Any
    entry_id: str
    zones: list[Any]
    boiler_mode: str
    master_hvac_mode: str
    enable_heat_pump: bool
    heat_pump_cooling: bool
    weather_sensor_id: str | None
    boiler_backend: BoilerBackendProtocol | None
    heat_pump_backend: Any | None
    plant_orchestrator: PlantOrchestratorProtocol | None
    zone_controller: ZoneControllerProtocol | None

    @property
    def climate_entities(self) -> dict[str, Any]:
        """Return registered climate entities."""
        ...

    @property
    def zone_demands(self) -> dict[str, float]:
        """Return current zone demands."""
        ...

    def get_master_state(self) -> bool:
        """Return True when heating master is ON."""
        ...

    def get_zone_mode(self, climate_id: str) -> str:
        """Return current mode (primary/secondary/bypass) for a zone."""
        ...

    def get_zone_demand(self, climate_id: str) -> float:
        """Return current demand (0-100%) for a zone."""
        ...

    def set_zone_demand(self, climate_id: str, demand: float) -> None:
        """Update current demand (0-100%) for a zone."""
        ...

    def resolve_zone_id(self, entity_id: str) -> str:
        """Resolve an alias or entity_id to canonical zone id."""
        ...
