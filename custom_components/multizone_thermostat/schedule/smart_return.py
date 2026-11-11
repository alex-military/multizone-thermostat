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

    def _resolve_preset_temp(
        self,
        preset: str,
        hvac_mode: str = "heat",
        climate_id: str | None = None,
    ) -> float:
        """Resolve preset temperature for a preset and hvac_mode."""
        actual_hvac_mode = hvac_mode
        actual_cid = climate_id
        if actual_hvac_mode not in ("heat", "cool", "off") and actual_cid is None:
            actual_cid = actual_hvac_mode
            actual_hvac_mode = "heat"

        if self._resolve_preset_temp_fn:
            try:
                if actual_cid is not None:
                    return float(self._resolve_preset_temp_fn(preset, actual_cid))
                return float(self._resolve_preset_temp_fn(preset, actual_hvac_mode))
            except TypeError:
                try:
                    return float(self._resolve_preset_temp_fn(preset))
                except Exception:
                    pass

        if hasattr(self.coordinator, "get_DynamicPresets") and callable(self.coordinator.get_DynamicPresets):
            dyn = self.coordinator.get_DynamicPresets()
            if isinstance(dyn, dict):
                if actual_hvac_mode == "cool":
                    if f"{preset}_cool" in dyn:
                        val = dyn[f"{preset}_cool"]
                        if isinstance(val, (int, float)):
                            return float(val)
                    if preset in dyn:
                        val = dyn[preset]
                        if isinstance(val, (int, float)):
                            return float(val)
                else:
                    if preset in dyn:
                        val = dyn[preset]
                        if isinstance(val, (int, float)):
                            return float(val)

        zm = getattr(self.coordinator, "zone_manager", None)
        if zm is not None and hasattr(zm, "get_preset_temperature") and actual_cid:
            try:
                val = zm.get_preset_temperature(preset, actual_cid, hvac_mode=actual_hvac_mode)
            except TypeError:
                val = zm.get_preset_temperature(preset, actual_cid)
            if val is not None:
                return float(val)

        return 24.0 if actual_hvac_mode == "cool" else 20.0

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

    def get_zone_cooling_rate(self, climate_id: str) -> float:
        """Get zone cooling rate from thermal model or default fallback."""
        models = getattr(self.coordinator, "_thermal_models", None)
        if isinstance(models, dict):
            model = models.get(climate_id)
            if model is not None:
                rate = getattr(model, "cooling_rate", None)
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
        hvac_mode: str | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Calculate the Thermal Radar plan with staggered preheating or precooling start times."""
        now = self._as_local(now)
        arrival_dt = self.parse_arrival_time(arrival_time, now)

        norm_filter = None
        if zones:
            norm_filter = {z if z.startswith("climate.") else make_zone_entity_id(z) for z in zones}

        plan: dict[str, dict[str, Any]] = {}
        all_zones = getattr(self.coordinator, "zones", [])

        if hvac_mode is not None:
            active_hvac_mode = str(hvac_mode).lower()
        else:
            active_hvac_mode = str(getattr(self.coordinator, "master_hvac_mode", "heat")).lower()

        target_preset = preset
        for zone in all_zones:
            zone_name = zone.get(CONF_ZONE_NAME, "")
            climate_id = zone.get("climate_id") or make_zone_entity_id(zone_name)
            if norm_filter and climate_id not in norm_filter:
                continue

            if active_hvac_mode == "cool" and hasattr(self.coordinator, "can_zone_cool") and not self.coordinator.can_zone_cool(climate_id):
                continue

            current_temp = self.get_zone_current_temp(climate_id)
            target_temp = self._resolve_preset_temp(target_preset, active_hvac_mode, climate_id=climate_id)

            if active_hvac_mode == "cool":
                rate = self.get_zone_cooling_rate(climate_id)
                if current_temp is not None and current_temp > target_temp:
                    hours_needed = min(
                        MAX_SMART_START_HOURS, (current_temp - target_temp) / rate
                    )
                else:
                    hours_needed = 0.0
                already_at_target = bool(
                    current_temp is not None and current_temp <= target_temp
                )
            else:
                rate = self.get_zone_heating_rate(climate_id)
                if current_temp is not None and current_temp < target_temp:
                    hours_needed = min(
                        MAX_SMART_START_HOURS, (target_temp - current_temp) / rate
                    )
                else:
                    hours_needed = 0.0
                already_at_target = bool(
                    current_temp is not None and current_temp >= target_temp
                )

            ignition_dt = arrival_dt - timedelta(hours=hours_needed)
            plan[climate_id] = {
                "zone_name": zone_name or climate_id,
                "climate_id": climate_id,
                "current_temp": current_temp,
                "target_temp": target_temp,
                "heating_rate": round(rate, 2),
                "cooling_rate": round(rate, 2),
                "minutes_needed": int(round(hours_needed * 60)),
                "ignition_time": ignition_dt.isoformat(),
                "arrival_time": arrival_dt.isoformat(),
                "already_at_target": already_at_target,
            }

        return plan

    evaluate = calculate_plan

    def evaluate_predictive_smart_start(
        self,
        climate_id: str,
        slot: dict,
        future_blocks: list[dict],
        active_ss: dict | None,
        now: datetime,
        is_cool: bool = False,
        get_current_temp_fn: Any = None,
        get_heating_rate_fn: Any = None,
        get_cooling_rate_fn: Any = None,
    ) -> dict | None:
        """Evaluate if upcoming blocks require predictive pre-heating or pre-cooling."""
        for next_b in future_blocks:
            block_start_iso = next_b["start_dt"].isoformat()

            is_already_preheating = (
                active_ss is not None
                and active_ss.get("block_start") == block_start_iso
                and now < next_b["start_dt"]
            )

            if is_already_preheating:
                return active_ss

            should_precondition = False
            curr_temp = (
                get_current_temp_fn(climate_id)
                if get_current_temp_fn is not None
                else self.get_zone_current_temp(climate_id)
            )

            if is_cool:
                if (
                    next_b["target_temp"] < slot["target_temp"]
                    and curr_temp is not None
                    and curr_temp > next_b["target_temp"]
                ):
                    cooling_rate = (
                        get_cooling_rate_fn(climate_id)
                        if get_cooling_rate_fn is not None
                        else self.get_zone_cooling_rate(climate_id)
                    )
                    hours_needed = min(
                        MAX_SMART_START_HOURS,
                        (curr_temp - next_b["target_temp"]) / cooling_rate,
                    )
                    rate = cooling_rate
                    should_precondition = True
            else:
                if (
                    next_b["target_temp"] > slot["target_temp"]
                    and curr_temp is not None
                    and curr_temp < next_b["target_temp"]
                ):
                    heating_rate = (
                        get_heating_rate_fn(climate_id)
                        if get_heating_rate_fn is not None
                        else self.get_zone_heating_rate(climate_id)
                    )
                    hours_needed = min(
                        MAX_SMART_START_HOURS,
                        (next_b["target_temp"] - curr_temp) / heating_rate,
                    )
                    rate = heating_rate
                    should_precondition = True

            if should_precondition:
                preheat_dt = next_b["start_dt"] - timedelta(hours=hours_needed)
                check_now = now
                if preheat_dt.tzinfo is not None and check_now.tzinfo is None:
                    check_now = check_now.replace(tzinfo=preheat_dt.tzinfo)
                elif preheat_dt.tzinfo is None and check_now.tzinfo is not None:
                    preheat_dt = preheat_dt.replace(tzinfo=check_now.tzinfo)

                if check_now >= preheat_dt:
                    return {
                        "target_temp": float(next_b["target_temp"]),
                        "preset": next_b["preset"],
                        "block_start": block_start_iso,
                        "preheat_start": preheat_dt.isoformat(),
                        "heating_rate": round(rate, 2),
                        "source": "schedule",
                    }

        return None
