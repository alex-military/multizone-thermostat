"""Smart Return and Thermal Radar preheating engine for Multizone Thermostat."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
import homeassistant.util.dt as dt_util

from ..const import (
    CONF_ZONE_NAME,
    DEFAULT_SMART_START_HEATING_RATE,
    MAX_SMART_START_HOURS,
    make_zone_entity_id,
)

_LOGGER = logging.getLogger(__name__)


class SmartReturnPlanner:
    """Calculates thermal preheating horizons and dynamic arrival plans."""

    def __init__(
        self,
        coordinator: Any,
        hass: HomeAssistant | None = None,
        as_local_fn: Any = None,
        resolve_preset_temp_fn: Any = None,
    ) -> None:
        """Initialize the Smart Return planner."""
        self.coordinator = coordinator
        self.hass = hass
        self._as_local_fn = as_local_fn
        self._resolve_preset_temp_fn = resolve_preset_temp_fn

    def _as_local(self, dt: datetime | None) -> datetime:
        """Ensure datetime is in local timezone."""
        if self._as_local_fn:
            return self._as_local_fn(dt)
        if dt is None:
            return dt_util.now()
        if dt.tzinfo is None:
            local_tz = dt_util.get_time_zone(
                getattr(getattr(self.hass, "config", None), "time_zone", "UTC")
            )
            return dt.replace(tzinfo=local_tz)
        return dt_util.as_local(dt)

    def _resolve_preset_temp(self, preset: str, climate_id: str) -> float:
        """Resolve preset temperature for a zone."""
        if self._resolve_preset_temp_fn:
            return float(self._resolve_preset_temp_fn(preset, climate_id))
        zm = getattr(self.coordinator, "zone_manager", None)
        if zm is not None and hasattr(zm, "get_preset_temperature"):
            return float(zm.get_preset_temperature(preset, climate_id))
        return 21.0 if preset == "comfort" else 18.0

    def get_zone_current_temp(self, climate_id: str) -> float | None:
        """Get current temperature for zone from climate entity or HA state."""
        entities = getattr(self.coordinator, "_climate_entities", None)
        if isinstance(entities, dict):
            climate_ent = entities.get(climate_id)
            if climate_ent is not None:
                cur = getattr(climate_ent, "current_temperature", None)
                if isinstance(cur, (int, float)):
                    return float(cur)
        if self.hass and hasattr(self.hass, "states") and self.hass.states:
            st = self.hass.states.get(climate_id)
            if st and hasattr(st, "attributes") and isinstance(st.attributes, dict):
                cur = st.attributes.get("current_temperature")
                if isinstance(cur, (int, float)):
                    return float(cur)
        return None

    def get_zone_heating_rate(self, climate_id: str) -> float:
        """Get zone heating rate from thermal model or default fallback."""
        models = getattr(self.coordinator, "_thermal_models", None)
        if isinstance(models, dict):
            model = models.get(climate_id)
            if model is not None:
                rate = getattr(model, "heating_rate", None)
                if isinstance(rate, (int, float)) and rate > 0.05:
                    return float(rate)
        return float(DEFAULT_SMART_START_HEATING_RATE)

    def parse_arrival_time(self, arrival_time: str | datetime, now: datetime) -> datetime:
        """Parse arrival time string ('HH:MM' or ISO) or datetime relative to now."""
        if isinstance(arrival_time, datetime):
            target_dt = arrival_time
            if target_dt.tzinfo is not None and now.tzinfo is None:
                target_dt = target_dt.replace(tzinfo=None)
            elif target_dt.tzinfo is None and now.tzinfo is not None:
                target_dt = target_dt.replace(tzinfo=now.tzinfo)
            return target_dt

        val = str(arrival_time).strip()
        if ":" in val and len(val) <= 5:
            h, m = map(int, val.split(":"))
            target_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if target_dt <= now:
                target_dt += timedelta(days=1)
            return target_dt

        parsed = dt_util.parse_datetime(val)
        if parsed is None:
            parsed = datetime.fromisoformat(val)
        if parsed.tzinfo is not None and now.tzinfo is None:
            parsed = parsed.replace(tzinfo=None)
        elif parsed.tzinfo is None and now.tzinfo is not None:
            parsed = parsed.replace(tzinfo=now.tzinfo)
        return parsed

    def calculate_plan(
        self,
        arrival_time: str | datetime,
        preset: str = "comfort",
        zones: list[str] | None = None,
        now: datetime | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Calculate the Thermal Radar plan with staggered preheating start times."""
        now = self._as_local(now)
        arrival_dt = self.parse_arrival_time(arrival_time, now)

        norm_filter = None
        if zones:
            norm_filter = {z if z.startswith("climate.") else make_zone_entity_id(z) for z in zones}

        plan: dict[str, dict[str, Any]] = {}
        all_zones = getattr(self.coordinator, "zones", [])

        for zone in all_zones:
            zone_name = zone.get(CONF_ZONE_NAME, "")
            climate_id = zone.get("climate_id") or make_zone_entity_id(zone_name)
            if norm_filter and climate_id not in norm_filter:
                continue

            current_temp = self.get_zone_current_temp(climate_id)
            target_temp = self._resolve_preset_temp(preset, climate_id)
            heating_rate = self.get_zone_heating_rate(climate_id)

            if current_temp is not None and current_temp < target_temp:
                hours_needed = min(
                    MAX_SMART_START_HOURS, (target_temp - current_temp) / heating_rate
                )
            else:
                hours_needed = 0.0

            ignition_dt = arrival_dt - timedelta(hours=hours_needed)
            plan[climate_id] = {
                "zone_name": zone_name or climate_id,
                "climate_id": climate_id,
                "current_temp": current_temp,
                "target_temp": target_temp,
                "heating_rate": round(heating_rate, 2),
                "minutes_needed": int(round(hours_needed * 60)),
                "ignition_time": ignition_dt.isoformat(),
                "arrival_time": arrival_dt.isoformat(),
                "already_at_target": bool(
                    current_temp is not None and current_temp >= target_temp
                ),
            }

        return plan
