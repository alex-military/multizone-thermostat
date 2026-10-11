"""Sensor watchdog module for wireless dropouts and stale sensor fallback."""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import TYPE_CHECKING

from homeassistant.util import dt as dt_util
from ..const import CONF_ZONE_CLIMATES

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class SensorWatchdog:
    """Monitors sensor staleness and coordinates TRV fallback reading."""

    def __init__(self, hass: HomeAssistant | None = None) -> None:
        """Initialize sensor watchdog."""
        self.hass = hass

    def is_sensor_stale(self, last_update: float | datetime, timeout_seconds: float) -> bool:
        """Return True if time elapsed since last update exceeds timeout."""
        if timeout_seconds <= 0:
            return False
        if isinstance(last_update, datetime):
            now_dt = dt_util.utcnow()
            lu = dt_util.as_utc(last_update)
            return (now_dt - lu).total_seconds() > timeout_seconds
        if last_update > 1e8:
            return (time.time() - last_update) > timeout_seconds
        return (time.monotonic() - last_update) > timeout_seconds

    def get_zone_trv_fallback_temp(self, zone: dict, hass: HomeAssistant | None = None) -> float | None:
        """Calculate average temperature from TRV entities as fallback."""
        ha = hass or self.hass
        if not ha:
            return None

        trv_entities = zone.get(CONF_ZONE_CLIMATES, [])
        if not trv_entities:
            return None

        temps: list[float] = []
        for trv in trv_entities:
            st = ha.states.get(trv)
            if st and st.state not in ("unavailable", "unknown"):
                t = st.attributes.get("current_temperature")
                if t is not None:
                    try:
                        temps.append(float(t))
                    except (ValueError, TypeError):
                        pass

        if temps:
            return sum(temps) / len(temps)
        return None
