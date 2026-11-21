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
    resolve_zone_id_safe,
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
        climate_id = resolve_zone_id_safe(self.coordinator, climate_id)
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

    @staticmethod
    def _resolve(obs: Any) -> float:
        """Prefer active cooling rate when learned; fall back to passive cooling rate."""
        active = float(getattr(obs, "active_cooling_rate", 0.0) or 0.0)
        if active > 0.0:
            return active
        return float(getattr(obs, "cooling_rate", 0.0) or 0.0)

    def get_zone_cooling_rate(self, climate_id: str) -> float:
        """Return cooling rate for a zone preferring active cooling rate over passive rate."""
        climate_id = resolve_zone_id_safe(self.coordinator, climate_id)
        for container_name, attr_name in (("zone_controller", "thermal_models"), (None, "_thermal_models")):
            root = getattr(self.coordinator, container_name, None) if container_name else self.coordinator
            models = getattr(root, attr_name, None) if root else None
            obs = models.get(climate_id) if isinstance(models, dict) else None
            if obs:
                active = float(getattr(obs, "active_cooling_rate", 0.0) or 0.0)
                if active > 0.0:
                    return active
        sched = getattr(self.coordinator, "schedule_manager", None)
        if sched and hasattr(sched, "_get_zone_cooling_rate"):
            rate = float(sched._get_zone_cooling_rate(climate_id) or 0.0)
            if rate > 0.0:
                return rate
        for container_name, attr_name in (("zone_controller", "thermal_models"), (None, "_thermal_models")):
            root = getattr(self.coordinator, container_name, None) if container_name else self.coordinator
            models = getattr(root, attr_name, None) if root else None
            obs = models.get(climate_id) if isinstance(models, dict) else None
            if obs:
                val = self._resolve(obs)
                if val > 0.0:
                    return val
        return 0.0
