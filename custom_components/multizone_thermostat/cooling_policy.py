"""Cooling capability policy for Multizone Thermostat."""
from __future__ import annotations

import logging
from typing import Any

from .const import (
    CONF_ZONE_NAME,
    CONF_ZONE_CLIMATES,
    CONF_ZONE_SWITCHES,
    CONF_ZONE_VALVES,
    CONF_ZONE_TRV_SYNC,
    DEFAULT_SPLIT_ROLE,
    SPLIT_ROLE_HEAT_COOL,
    SPLIT_ROLE_COOLING_ONLY,
    make_zone_entity_id,
)
from .plant_config import get_zone_name

_LOGGER = logging.getLogger(__name__)


class CoolingPolicy:
    """Manages cooling capability rules for central plant and individual zones."""

    def __init__(self, coordinator: Any) -> None:
        """Initialize the cooling policy with coordinator reference."""
        self.coordinator = coordinator

    def can_central_cool(self) -> bool:
        """Return True if central plant supports cooling (Heat pump with cooling enabled)."""
        hp_enabled = bool(getattr(self.coordinator, "enable_heat_pump", False))
        hp_cooling = bool(getattr(self.coordinator, "heat_pump_cooling", True))
        return hp_enabled and hp_cooling

    def can_zone_cool(self, climate_id: str) -> bool:
        """Return True if zone has cooling capabilities (Split AC or Central Heat Pump Cooling)."""
        if hasattr(self.coordinator, "split_manager") and self.coordinator.split_manager.has_split(climate_id):
            split_info = self.coordinator.split_manager.get_split_info(climate_id)
            if split_info:
                role = split_info.get("split_role", DEFAULT_SPLIT_ROLE)
                if role in (SPLIT_ROLE_HEAT_COOL, SPLIT_ROLE_COOLING_ONLY):
                    return True

        if not self.can_central_cool():
            return False

        zone_conf = None
        for z in getattr(self.coordinator, "zones", []):
            if make_zone_entity_id(get_zone_name(z)) == climate_id or z.get("climate_id") == climate_id:
                zone_conf = z
                break

        if not zone_conf:
            # If zone configuration is not found in central coordinator, it cannot be safely cooled
            return False

        if zone_conf.get("allow_cooling") is True:
            return True
        if zone_conf.get("allow_cooling") is False:
            return False

        emitter = zone_conf.get("emitter_type")
        if emitter == "radiator":
            return False
        if emitter in ("underfloor", "fancoil"):
            return True

        is_fancoil = bool(
            zone_conf.get("fancoil")
            or zone_conf.get("is_fancoil")
        )
        if is_fancoil:
            return True

        climates = zone_conf.get(CONF_ZONE_CLIMATES, []) or zone_conf.get("climate_entities", []) or zone_conf.get("climates", [])
        switches = zone_conf.get(CONF_ZONE_SWITCHES, []) or zone_conf.get("switch_entities", []) or zone_conf.get("switches", [])
        valves = zone_conf.get(CONF_ZONE_VALVES, []) or zone_conf.get("valve_entities", []) or zone_conf.get("valves", [])
        has_trv_sync = bool(zone_conf.get(CONF_ZONE_TRV_SYNC, zone_conf.get("trv_preset_sync", False)))

        if switches or valves:
            return True

        if climates and has_trv_sync:
            return False

        return True

    def get_zone_cooling_rate(self, climate_id: str) -> float:
        """Return cooling rate for a zone from schedule_manager or thermal observer."""
        if hasattr(self.coordinator, "schedule_manager") and hasattr(self.coordinator.schedule_manager, "_get_zone_cooling_rate"):
            return float(self.coordinator.schedule_manager._get_zone_cooling_rate(climate_id) or 0.0)
        if hasattr(self.coordinator, "zone_controller") and hasattr(self.coordinator.zone_controller, "thermal_models"):
            obs = self.coordinator.zone_controller.thermal_models.get(climate_id)
            if obs:
                return float(getattr(obs, "cooling_rate", 0.0))
        if hasattr(self.coordinator, "_thermal_models"):
            obs = self.coordinator._thermal_models.get(climate_id)
            if obs:
                return float(getattr(obs, "cooling_rate", 0.0))
        return 0.0
