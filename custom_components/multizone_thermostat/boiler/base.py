"""Base interface for boiler backends."""
from abc import ABC, abstractmethod

class BoilerBackend(ABC):
    """Abstract base class for boiler generators."""

    @abstractmethod
    async def async_update(self, demand: float, peak_zone: str | None, frost_emergency: bool) -> None:
        """Update the boiler state based on heat demand (0.0 to 100.0)."""
        pass

    @abstractmethod
    async def async_emergency_off(self) -> None:
        """Force the boiler off immediately (emergency/master off)."""
        pass

    @property
    @abstractmethod
    def status_reason(self) -> str:
        """Return the current status reason."""
        pass
