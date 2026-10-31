"""Schedule Profile Manager for Multizone Thermostat (Phase 6)."""
from __future__ import annotations

import copy
from datetime import datetime, timedelta
import inspect
import logging
from typing import Any

from homeassistant.components.climate.const import HVACMode
import homeassistant.util.dt as dt_util

from .const import (
    CONF_ZONE_NAME,
    DEFAULT_BASELINE_PRESET,
    DEFAULT_PRESET_TEMPS,
    DEFAULT_SCHEDULE_PROFILE,
    DEFAULT_SMART_START_HEATING_RATE,
    KEY_ACTIVE_PROFILE,
    KEY_FALLBACK_PROFILE,
    KEY_MANUAL_OVERRIDES,
    KEY_PROFILE_EXPIRES_AT,
    KEY_SCHEDULE_PROFILES,
    KEY_SCHEDULER_ENABLED,
    KEY_SMART_RETURN,
    MAX_SMART_START_HOURS,
    SCHEDULE_DAYS,
    ZONE_MODE_BYPASS,
    make_zone_entity_id,
)

_LOGGER = logging.getLogger(__name__)


def _default_profiles_dict() -> dict[str, dict[str, Any]]:
    """Return default dictionary of base profiles."""
    return {
        "standard": {
            "name": "Standard",
            "baseline_preset": DEFAULT_BASELINE_PRESET,
            "days": {day: {} for day in SCHEDULE_DAYS},
        },
        "smart_working": {
            "name": "Smart Working",
            "baseline_preset": DEFAULT_BASELINE_PRESET,
            "days": {day: {} for day in SCHEDULE_DAYS},
        },
        "holiday": {
            "name": "Festivo",
            "baseline_preset": DEFAULT_BASELINE_PRESET,
            "days": {day: {} for day in SCHEDULE_DAYS},
        },
    }


class ScheduleProfileManager:
    """Manages multi-profile weekly scheduling, smart start and smart return per zone."""

    def __init__(self, coordinator: Any) -> None:
        """Initialize the schedule profile manager."""
        self.coordinator = coordinator
        self.scheduler_enabled: bool = False
        self.active_profile: str = DEFAULT_SCHEDULE_PROFILE
        self.profile_expires_at: str | None = None
        self.fallback_profile: str = DEFAULT_SCHEDULE_PROFILE
        self.profiles: dict[str, dict[str, Any]] = _default_profiles_dict()
        self.manual_overrides: dict[str, dict[str, Any]] = {}
        self.schedule_overrides: dict[str, float] = {}
        self.smart_start_info: dict[str, dict[str, Any]] = {}
        self.smart_return: dict[str, Any] | None = None

    @property
    def hass(self):
        """Get Home Assistant instance from coordinator."""
        return self.coordinator.hass

    def load_from_storage(self) -> None:
        """Load schedule state from coordinator persistent settings."""
        self.scheduler_enabled = bool(
            self.coordinator.get_persistent_data(KEY_SCHEDULER_ENABLED, False)
        )
        self.active_profile = str(
            self.coordinator.get_persistent_data(KEY_ACTIVE_PROFILE, DEFAULT_SCHEDULE_PROFILE)
        )
        self.profile_expires_at = self.coordinator.get_persistent_data(
            KEY_PROFILE_EXPIRES_AT, None
        )
        self.fallback_profile = str(
            self.coordinator.get_persistent_data(KEY_FALLBACK_PROFILE, DEFAULT_SCHEDULE_PROFILE)
        )

        saved_profiles = self.coordinator.get_persistent_data(KEY_SCHEDULE_PROFILES)
        defaults = _default_profiles_dict()
        if isinstance(saved_profiles, dict):
            self.profiles = dict(saved_profiles)
        else:
            self.profiles = {}

        # Ensure standard, smart_working, holiday always exist
        for pid, pdata in defaults.items():
            if pid not in self.profiles or not isinstance(self.profiles[pid], dict):
                self.profiles[pid] = copy.deepcopy(pdata)
            else:
                prof = self.profiles[pid]
                if "name" not in prof:
                    prof["name"] = pdata["name"]
                if "baseline_preset" not in prof:
                    prof["baseline_preset"] = pdata["baseline_preset"]
                if "days" not in prof or not isinstance(prof["days"], dict):
                    prof["days"] = {day: {} for day in SCHEDULE_DAYS}
                else:
                    for day in SCHEDULE_DAYS:
                        if day not in prof["days"] or not isinstance(prof["days"][day], dict):
                            prof["days"][day] = {}

        for pid, prof in self.profiles.items():
            if not isinstance(prof, dict):
                continue
            if "name" not in prof:
                prof["name"] = pid.capitalize()
            if "baseline_preset" not in prof:
                prof["baseline_preset"] = DEFAULT_BASELINE_PRESET
            if "days" not in prof or not isinstance(prof["days"], dict):
                prof["days"] = {day: {} for day in SCHEDULE_DAYS}

        saved_overrides = self.coordinator.get_persistent_data(KEY_MANUAL_OVERRIDES, {})
        self.manual_overrides = dict(saved_overrides) if isinstance(saved_overrides, dict) else {}

        saved_sr = self.coordinator.get_persistent_data(KEY_SMART_RETURN, None)
        self.smart_return = dict(saved_sr) if isinstance(saved_sr, dict) else None

    async def async_save_to_storage(self) -> None:
        """Persist schedule state into coordinator settings store."""
        if hasattr(self.coordinator, "_settings") and isinstance(self.coordinator._settings, dict):
            self.coordinator._settings[KEY_SCHEDULER_ENABLED] = self.scheduler_enabled
            self.coordinator._settings[KEY_ACTIVE_PROFILE] = self.active_profile
            self.coordinator._settings[KEY_PROFILE_EXPIRES_AT] = self.profile_expires_at
            self.coordinator._settings[KEY_FALLBACK_PROFILE] = self.fallback_profile
            self.coordinator._settings[KEY_SCHEDULE_PROFILES] = self.profiles
            self.coordinator._settings[KEY_MANUAL_OVERRIDES] = self.manual_overrides
            self.coordinator._settings[KEY_SMART_RETURN] = self.smart_return
            if hasattr(self.coordinator, "_settings_store") and self.coordinator._settings_store:
                await self.coordinator._settings_store.async_save(self.coordinator._settings)

    async def async_set_scheduler_enabled(
        self, enabled: bool, now: datetime | None = None
    ) -> None:
        """Enable or disable the scheduler."""
        self.scheduler_enabled = bool(enabled)
        if not self.scheduler_enabled:
            self.schedule_overrides.clear()
            self.manual_overrides.clear()
            self.smart_start_info.clear()
            await self.async_save_to_storage()
            self._notify_climates()
        else:
            await self.async_save_to_storage()
            await self.async_evaluate_schedule(now)
            self._notify_climates()

    async def async_save_profile(
        self, profile_id: str, profile_data: dict[str, Any], now: datetime | None = None
    ) -> None:
        """Save or update a schedule profile."""
        name = profile_data.get("name", profile_id.capitalize())
        baseline = profile_data.get("baseline_preset", DEFAULT_BASELINE_PRESET)
        raw_days = profile_data.get("days", {})

        normalized_days: dict[str, dict[str, list[dict[str, Any]]]] = {
            day: {} for day in SCHEDULE_DAYS
        }
        if isinstance(raw_days, dict):
            for day, zones_data in raw_days.items():
                if day not in normalized_days:
                    normalized_days[day] = {}
                if isinstance(zones_data, dict):
                    for z_key, blocks in zones_data.items():
                        norm_key = (
                            z_key if z_key.startswith("climate.") else make_zone_entity_id(z_key)
                        )
                        if isinstance(blocks, list):
                            sorted_blocks = sorted(
                                [b for b in blocks if isinstance(b, dict)],
                                key=lambda b: str(b.get("start", "")),
                            )
                            normalized_days[day][norm_key] = sorted_blocks
                        else:
                            normalized_days[day][norm_key] = []

        self.profiles[profile_id] = {
            "name": name,
            "baseline_preset": baseline,
            "days": normalized_days,
        }

        await self.async_save_to_storage()

        if profile_id == self.active_profile and self.scheduler_enabled:
            await self.async_evaluate_schedule(now)
        self._notify_climates()

    async def async_duplicate_profile(
        self, source_id: str, target_id: str, target_name: str | None = None
    ) -> None:
        """Deep duplicate an existing profile into a new profile ID."""
        if source_id not in self.profiles:
            raise ValueError(f"Source profile '{source_id}' does not exist")
        new_prof = copy.deepcopy(self.profiles[source_id])
        if target_name is not None:
            new_prof["name"] = target_name
        else:
            new_prof["name"] = f"Copy of {new_prof.get('name', source_id)}"
        self.profiles[target_id] = new_prof
        await self.async_save_to_storage()
        self._notify_climates()

    async def async_activate_profile(
        self,
        profile_id: str,
        expires_at: str | datetime | None = None,
        fallback_profile: str = DEFAULT_SCHEDULE_PROFILE,
        now: datetime | None = None,
    ) -> None:
        """Activate a profile with optional expiration time."""
        if profile_id not in self.profiles:
            _LOGGER.warning("Activating unknown profile '%s', initializing default", profile_id)
            self.profiles[profile_id] = {
                "name": profile_id.capitalize(),
                "baseline_preset": DEFAULT_BASELINE_PRESET,
                "days": {day: {} for day in SCHEDULE_DAYS},
            }

        self.active_profile = profile_id
        if isinstance(expires_at, datetime):
            self.profile_expires_at = expires_at.isoformat()
        elif isinstance(expires_at, str) and expires_at.strip():
            self.profile_expires_at = expires_at.strip()
        else:
            self.profile_expires_at = None

        self.fallback_profile = fallback_profile or DEFAULT_SCHEDULE_PROFILE
        await self.async_save_to_storage()
        if self.scheduler_enabled:
            await self.async_evaluate_schedule(now)
        self._notify_climates()

    def check_profile_expiry(self, now: datetime) -> bool:
        """Check if active profile has expired and revert to fallback if so."""
        if not self.profile_expires_at:
            return False

        parsed_exp = dt_util.parse_datetime(self.profile_expires_at)
        if parsed_exp is None:
            try:
                parsed_exp = datetime.fromisoformat(self.profile_expires_at)
            except Exception:
                self.profile_expires_at = None
                return False

        check_now = now
        if parsed_exp.tzinfo is not None and check_now.tzinfo is None:
            check_now = check_now.replace(tzinfo=parsed_exp.tzinfo)
        elif parsed_exp.tzinfo is None and check_now.tzinfo is not None:
            parsed_exp = parsed_exp.replace(tzinfo=check_now.tzinfo)

        if check_now >= parsed_exp:
            old_profile = self.active_profile
            self.active_profile = self.fallback_profile or DEFAULT_SCHEDULE_PROFILE
            self.profile_expires_at = None
            if hasattr(self.coordinator, "record_diagnostic_event"):
                self.coordinator.record_diagnostic_event(
                    "SCHEDULE_PROFILE_EXPIRED",
                    {
                        "expired_profile": old_profile,
                        "fallback_profile": self.active_profile,
                        "expired_at": now.isoformat(),
                    },
                )
            return True
        return False

    def _get_zone_current_temp(self, climate_id: str) -> float | None:
        """Get current temperature for zone from climate entity or HA state."""
        entities = getattr(self.coordinator, "_climate_entities", None)
        if isinstance(entities, dict):
            climate_ent = entities.get(climate_id)
            if climate_ent is not None:
                cur = getattr(climate_ent, "current_temperature", None)
                if isinstance(cur, (int, float)):
                    return float(cur)
        if hasattr(self.hass, "states") and self.hass.states:
            st = self.hass.states.get(climate_id)
            if st and hasattr(st, "attributes") and isinstance(st.attributes, dict):
                cur = st.attributes.get("current_temperature")
                if isinstance(cur, (int, float)):
                    return float(cur)
        return None

    def _get_zone_heating_rate(self, climate_id: str) -> float:
        """Get zone heating rate from thermal model or default fallback."""
        models = getattr(self.coordinator, "_thermal_models", None)
        if isinstance(models, dict):
            model = models.get(climate_id)
            if model is not None:
                rate = getattr(model, "heating_rate", None)
                if isinstance(rate, (int, float)) and rate > 0.05:
                    return float(rate)
        return float(DEFAULT_SMART_START_HEATING_RATE)

    def _parse_arrival_time(self, arrival_time: str | datetime, now: datetime) -> datetime:
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

    def calculate_smart_return_plan(
        self,
        arrival_time: str | datetime,
        preset: str = "comfort",
        zones: list[str] | None = None,
        now: datetime | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Calculate the Thermal Radar plan with staggered preheating start times."""
        if now is None:
            now = dt_util.now()
        arrival_dt = self._parse_arrival_time(arrival_time, now)

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

            current_temp = self._get_zone_current_temp(climate_id)
            target_temp = self._resolve_preset_temp(preset, climate_id)
            heating_rate = self._get_zone_heating_rate(climate_id)

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

    async def async_set_smart_return(
        self,
        arrival_time: str | datetime,
        preset: str = "comfort",
        zones: list[str] | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Schedule Smart Return and trigger immediate plan calculation and ignition."""
        if now is None:
            now = dt_util.now()
        arrival_dt = self._parse_arrival_time(arrival_time, now)
        norm_zones = (
            [z if z.startswith("climate.") else make_zone_entity_id(z) for z in zones]
            if zones
            else None
        )

        self.smart_return = {
            "arrival_time": arrival_dt.isoformat(),
            "preset": preset,
            "zones": norm_zones,
            "created_at": now.isoformat(),
        }
        await self.async_save_to_storage()
        if hasattr(self.coordinator, "record_diagnostic_event"):
            self.coordinator.record_diagnostic_event(
                "SMART_RETURN_SCHEDULED",
                {
                    "arrival_time": arrival_dt.isoformat(),
                    "preset": preset,
                    "zones": norm_zones,
                },
            )
        await self.async_evaluate_schedule(now)
        self._notify_climates()
        return self.calculate_smart_return_plan(arrival_dt, preset, norm_zones, now)

    async def async_cancel_smart_return(self, now: datetime | None = None) -> None:
        """Cancel active Smart Return."""
        self.smart_return = None
        await self.async_save_to_storage()
        if hasattr(self.coordinator, "record_diagnostic_event"):
            self.coordinator.record_diagnostic_event("SMART_RETURN_CANCELLED")
        await self.async_evaluate_schedule(now)
        self._notify_climates()

    def _parse_block_times(
        self, block: dict[str, Any], ref_date: datetime
    ) -> tuple[datetime, datetime]:
        """Convert block start/end strings to datetime objects relative to ref_date."""
        start_str = str(block.get("start", "00:00")).strip()
        end_str = str(block.get("end", "24:00")).strip()

        sh, sm = map(int, start_str.split(":"))
        start_dt = ref_date.replace(hour=sh, minute=sm, second=0, microsecond=0)

        if end_str in ("24:00", "00:00") and start_str != "00:00":
            end_dt = (ref_date + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        elif end_str == "24:00":
            end_dt = (ref_date + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        else:
            eh, em = map(int, end_str.split(":"))
            end_dt = ref_date.replace(hour=eh, minute=em, second=0, microsecond=0)
            if end_dt <= start_dt:
                end_dt += timedelta(days=1)

        return start_dt, end_dt

    def _resolve_preset_temp(self, preset: str, climate_id: str) -> float:
        """Resolve preset temperature for a zone."""
        if hasattr(self.coordinator, "zone_manager") and hasattr(
            self.coordinator.zone_manager, "get_preset_temperature"
        ):
            t = self.coordinator.zone_manager.get_preset_temperature(preset, climate_id)
            if t is not None:
                return float(t)
        return float(DEFAULT_PRESET_TEMPS.get(preset, 20.0))

    def evaluate_zone_slot(self, climate_id: str, now: datetime) -> dict[str, Any]:
        """Evaluate active schedule profile for a specific zone at time now."""
        profile = self.profiles.get(self.active_profile, {})
        days_dict = profile.get("days", {})
        baseline_preset = profile.get("baseline_preset", DEFAULT_BASELINE_PRESET)

        day_idx = now.weekday()
        day_key = SCHEDULE_DAYS[day_idx]

        # 1. Check if yesterday had a block crossing midnight into today
        yesterday_idx = (day_idx - 1) % 7
        yesterday_key = SCHEDULE_DAYS[yesterday_idx]
        yesterday_blocks = days_dict.get(yesterday_key, {}).get(climate_id, [])
        for block in yesterday_blocks:
            b_start, b_end = self._parse_block_times(block, now - timedelta(days=1))
            if b_start <= now < b_end:
                preset = block.get("preset", "comfort")
                resolved_temp = self._resolve_preset_temp(preset, climate_id)
                start_str = block.get("start", "00:00")
                end_str = block.get("end", "24:00")
                slot_id = f"{yesterday_key}_{start_str}_{end_str}_{preset}"
                return {
                    "state_type": "block",
                    "preset": preset,
                    "target_temp": resolved_temp,
                    "slot_id": slot_id,
                    "until": b_end,
                }

        # 2. Check blocks on today
        today_blocks = days_dict.get(day_key, {}).get(climate_id, [])
        for block in today_blocks:
            b_start, b_end = self._parse_block_times(block, now)
            if b_start <= now < b_end:
                preset = block.get("preset", "comfort")
                resolved_temp = self._resolve_preset_temp(preset, climate_id)
                start_str = block.get("start", "00:00")
                end_str = block.get("end", "24:00")
                slot_id = f"{day_key}_{start_str}_{end_str}_{preset}"
                return {
                    "state_type": "block",
                    "preset": preset,
                    "target_temp": resolved_temp,
                    "slot_id": slot_id,
                    "until": b_end,
                }

        # 3. Gap: Outside defined blocks, fall back to baseline preset
        resolved_temp = self._resolve_preset_temp(baseline_preset, climate_id)

        # Find earliest upcoming block in the next 7 days
        next_block_start: datetime | None = None
        for day_offset in range(0, 8):
            target_date = now + timedelta(days=day_offset)
            d_key = SCHEDULE_DAYS[target_date.weekday()]
            blocks = days_dict.get(d_key, {}).get(climate_id, [])
            for b in blocks:
                b_start, _ = self._parse_block_times(b, target_date)
                if b_start > now:
                    if next_block_start is None or b_start < next_block_start:
                        next_block_start = b_start
            if next_block_start is not None:
                break

        if next_block_start is not None:
            until_dt = next_block_start
        else:
            until_dt = (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )

        slot_id = f"{day_key}_gap_{until_dt.isoformat()}"
        return {
            "state_type": "baseline",
            "preset": baseline_preset,
            "target_temp": resolved_temp,
            "slot_id": slot_id,
            "until": until_dt,
        }

    def get_upcoming_blocks(
        self, climate_id: str, now: datetime, horizon_hours: int = 24
    ) -> list[dict[str, Any]]:
        """Return chronological list of upcoming scheduled blocks within horizon_hours."""
        profile = self.profiles.get(self.active_profile, {})
        days_dict = profile.get("days", {})
        horizon_end = now + timedelta(hours=horizon_hours)

        upcoming: list[dict[str, Any]] = []
        max_days = int(horizon_hours // 24) + 2
        for day_offset in range(0, max_days):
            target_date = now + timedelta(days=day_offset)
            d_key = SCHEDULE_DAYS[target_date.weekday()]
            blocks = days_dict.get(d_key, {}).get(climate_id, [])
            for b in blocks:
                b_start, b_end = self._parse_block_times(b, target_date)
                if b_end > now and b_start < horizon_end:
                    preset = b.get("preset", "comfort")
                    target_temp = self._resolve_preset_temp(preset, climate_id)
                    upcoming.append({
                        "start_dt": b_start,
                        "end_dt": b_end,
                        "preset": preset,
                        "target_temp": target_temp,
                    })

        upcoming.sort(key=lambda x: x["start_dt"])
        return upcoming

    def record_manual_override(
        self, climate_id: str, target_temp: float, now: datetime | None = None
    ) -> None:
        """Record manual override for zone lasting until current slot changes/expires."""
        if now is None:
            now = dt_util.now()
        slot = self.evaluate_zone_slot(climate_id, now)
        until_dt = slot["until"]
        until_str = until_dt.isoformat() if isinstance(until_dt, datetime) else str(until_dt)
        self.manual_overrides[climate_id] = {
            "target_temp": float(target_temp),
            "slot_id": slot["slot_id"],
            "until": until_str,
            "created_at": now.isoformat(),
        }
        self.schedule_overrides[climate_id] = float(target_temp)

    def clear_manual_override(
        self, climate_id: str | None = None, now: datetime | None = None
    ):
        """Clear manual override and re-evaluate schedule immediately."""
        if climate_id is None:
            self.manual_overrides.clear()
        else:
            self.manual_overrides.pop(climate_id, None)
        coro = self.async_evaluate_schedule(now)
        if hasattr(self.hass, "async_create_task"):
            return self.hass.async_create_task(coro)
        return coro

    async def async_clear_manual_override(
        self, climate_id: str | None = None, now: datetime | None = None
    ) -> None:
        """Async version to clear manual override and re-evaluate schedule."""
        if climate_id is None:
            self.manual_overrides.clear()
        else:
            self.manual_overrides.pop(climate_id, None)
        await self.async_evaluate_schedule(now)
        self._notify_climates()

    async def _async_wake_master(self) -> None:
        """Wake up master heating switch if disabled."""
        is_master_on = True
        if hasattr(self.coordinator, "get_master_state"):
            is_master_on = bool(self.coordinator.get_master_state())
        elif hasattr(self.coordinator, "master_enabled"):
            is_master_on = bool(getattr(self.coordinator, "master_enabled", True))

        if not is_master_on:
            _LOGGER.info("Smart Return: turning ON master heating switch")
            if hasattr(self.coordinator, "master_enabled"):
                self.coordinator.master_enabled = True
            if hasattr(self.coordinator, "set_master_state"):
                self.coordinator.set_master_state(True)
            master_sw = getattr(self.coordinator, "_master_switch", None)
            if master_sw and hasattr(master_sw, "async_write_ha_state"):
                try:
                    master_sw.async_write_ha_state()
                except Exception as ex:
                    _LOGGER.debug("Could not write state for master switch: %s", ex)

    async def _async_wake_zone(self, climate_id: str, climate_ent: Any | None = None) -> None:
        """Wake up a zone to HVACMode.HEAT if currently off."""
        _LOGGER.info("Smart Return: waking up zone %s to HVACMode.HEAT", climate_id)
        if climate_ent is None:
            climate_ent = getattr(self.coordinator, "_climate_entities", {}).get(climate_id)
        if climate_ent is not None:
            if hasattr(climate_ent, "_hvac_mode"):
                climate_ent._hvac_mode = HVACMode.HEAT
            if hasattr(climate_ent, "async_set_hvac_mode"):
                try:
                    res = climate_ent.async_set_hvac_mode(HVACMode.HEAT)
                    if inspect.isawaitable(res):
                        await res
                except Exception as ex:
                    _LOGGER.debug("Error calling async_set_hvac_mode on %s: %s", climate_id, ex)
            elif hasattr(climate_ent, "async_write_ha_state"):
                try:
                    climate_ent.async_write_ha_state()
                except Exception:
                    pass
        if hasattr(self.coordinator, "_async_set_hvac_mode"):
            try:
                res = self.coordinator._async_set_hvac_mode(climate_id, HVACMode.HEAT)
                if inspect.isawaitable(res):
                    await res
            except Exception as ex:
                _LOGGER.debug("Error calling coordinator._async_set_hvac_mode for %s: %s", climate_id, ex)

    async def async_evaluate_schedule(self, now: datetime | None = None) -> None:
        """Evaluate active schedule profile, smart start, and smart return across all zones."""
        if now is None:
            now = dt_util.now()

        profile_expired = self.check_profile_expiry(now)
        if profile_expired:
            await self.async_save_to_storage()

        # Check Smart Return completion
        smart_return_completed = False
        if self.smart_return is not None:
            arrival_raw = self.smart_return.get("arrival_time")
            arrival_dt = dt_util.parse_datetime(arrival_raw) if arrival_raw else None
            if arrival_dt is None and arrival_raw:
                try:
                    arrival_dt = datetime.fromisoformat(arrival_raw)
                except Exception:
                    pass
            if arrival_dt is not None:
                check_now = now
                if arrival_dt.tzinfo is not None and check_now.tzinfo is None:
                    check_now = check_now.replace(tzinfo=arrival_dt.tzinfo)
                elif arrival_dt.tzinfo is None and check_now.tzinfo is not None:
                    arrival_dt = arrival_dt.replace(tzinfo=check_now.tzinfo)

                if check_now >= arrival_dt:
                    smart_return_completed = True
                    sr_preset = self.smart_return.get("preset", "comfort")
                    sr_zones = self.smart_return.get("zones")

                    # Wake up master if disabled
                    await self._async_wake_master()

                    # Ensure plan zones are in HVACMode.HEAT
                    all_zones_list = getattr(self.coordinator, "zones", [])
                    for z in all_zones_list:
                        cid = z.get("climate_id") or make_zone_entity_id(z.get(CONF_ZONE_NAME, ""))
                        if sr_zones is None or cid in sr_zones:
                            z_mode = None
                            if hasattr(self.coordinator, "get_zone_mode"):
                                z_mode = self.coordinator.get_zone_mode(cid)
                            elif hasattr(self.coordinator, "zone_manager") and hasattr(self.coordinator.zone_manager, "get_zone_mode"):
                                z_mode = self.coordinator.zone_manager.get_zone_mode(cid)
                            if z_mode != ZONE_MODE_BYPASS:
                                await self._async_wake_zone(cid)

                    if not self.scheduler_enabled and hasattr(self.coordinator, "zone_manager"):
                        await self.coordinator.zone_manager.async_set_global_preset(sr_preset)
                    self.smart_return = None
                    await self.async_save_to_storage()
                    if hasattr(self.coordinator, "record_diagnostic_event"):
                        self.coordinator.record_diagnostic_event(
                            "SMART_RETURN_COMPLETED",
                            {"preset": sr_preset, "completed_at": now.isoformat()},
                        )

        if not self.scheduler_enabled and self.smart_return is None:
            if self.schedule_overrides or self.smart_start_info:
                self.schedule_overrides.clear()
                self.smart_start_info.clear()
                self._notify_climates()
            return

        old_overrides = dict(self.schedule_overrides)
        old_smart_start = dict(self.smart_start_info)
        self.smart_start_info.clear()

        # Calculate Smart Return plan if active
        sr_plan = {}
        if self.smart_return is not None:
            sr_arrival = self.smart_return["arrival_time"]
            sr_preset = self.smart_return.get("preset", "comfort")
            sr_zones = self.smart_return.get("zones")
            sr_plan = self.calculate_smart_return_plan(sr_arrival, sr_preset, sr_zones, now)

        zones = getattr(self.coordinator, "zones", [])

        for zone in zones:
            climate_id = zone.get("climate_id") or make_zone_entity_id(
                zone.get(CONF_ZONE_NAME, "")
            )

            # Check if climate entity is in HVACMode.OFF
            is_off = False
            climate_ent = getattr(self.coordinator, "_climate_entities", {}).get(climate_id)
            if climate_ent is not None:
                if (
                    getattr(climate_ent, "hvac_mode", None) == HVACMode.OFF
                    or getattr(climate_ent, "_hvac_mode", None) == HVACMode.OFF
                ):
                    is_off = True
            if not is_off and hasattr(self.hass, "states") and self.hass.states:
                st = self.hass.states.get(climate_id)
                if st is not None and st.state in (HVACMode.OFF, "off"):
                    is_off = True

            # 1. Smart Return check for zone:
            # If Smart Return ignition time has arrived, Smart Return wakes up Master and turns the zone to HEAT
            if climate_id in sr_plan:
                item = sr_plan[climate_id]
                ign_raw = item.get("ignition_time")
                ign_dt = dt_util.parse_datetime(ign_raw) if ign_raw else None
                if ign_dt is None and ign_raw:
                    try:
                        ign_dt = datetime.fromisoformat(ign_raw)
                    except Exception:
                        pass
                if ign_dt is not None:
                    check_now = now
                    if ign_dt.tzinfo is not None and check_now.tzinfo is None:
                        check_now = check_now.replace(tzinfo=ign_dt.tzinfo)
                    elif ign_dt.tzinfo is None and check_now.tzinfo is not None:
                        ign_dt = ign_dt.replace(tzinfo=check_now.tzinfo)

                    if check_now >= ign_dt:
                        z_mode = None
                        if hasattr(self.coordinator, "get_zone_mode"):
                            z_mode = self.coordinator.get_zone_mode(climate_id)
                        elif hasattr(self.coordinator, "zone_manager") and hasattr(self.coordinator.zone_manager, "get_zone_mode"):
                            z_mode = self.coordinator.zone_manager.get_zone_mode(climate_id)

                        if z_mode != ZONE_MODE_BYPASS:
                            # Wake up master and zone if off
                            await self._async_wake_master()
                            if is_off:
                                await self._async_wake_zone(climate_id, climate_ent)
                                is_off = False

                            sr_target = float(item["target_temp"])
                            self.schedule_overrides[climate_id] = sr_target
                            self.smart_start_info[climate_id] = {
                                "target_temp": sr_target,
                                "preset": self.smart_return.get("preset", "comfort"),
                                "block_start": item["arrival_time"],
                                "preheat_start": item["ignition_time"],
                                "heating_rate": item["heating_rate"],
                                "source": "smart_return",
                            }
                            continue

            # 2. Explicit OFF check:
            # If zone is in HVACMode.OFF (and not currently firing a Smart Return ignition),
            # strictly preserve Explicit OFF - do not force turning on and drop overrides.
            if is_off:
                self.manual_overrides.pop(climate_id, None)
                self.schedule_overrides.pop(climate_id, None)
                continue

            # 3. Manual override check (only when scheduler is enabled)
            slot = self.evaluate_zone_slot(climate_id, now)
            has_valid_manual_override = False
            if self.scheduler_enabled and climate_id in self.manual_overrides:
                ov = self.manual_overrides[climate_id]
                ov_until_str = ov.get("until")
                ov_slot_id = ov.get("slot_id")

                is_expired = False
                if ov_until_str:
                    until_dt = dt_util.parse_datetime(ov_until_str)
                    if until_dt is None:
                        try:
                            until_dt = datetime.fromisoformat(ov_until_str)
                        except Exception:
                            is_expired = True
                    if until_dt is not None:
                        check_now = now
                        if until_dt.tzinfo is not None and check_now.tzinfo is None:
                            check_now = check_now.replace(tzinfo=until_dt.tzinfo)
                        elif until_dt.tzinfo is None and check_now.tzinfo is not None:
                            until_dt = until_dt.replace(tzinfo=check_now.tzinfo)
                        if check_now >= until_dt:
                            is_expired = True

                if is_expired or (ov_slot_id and ov_slot_id != slot["slot_id"]):
                    self.manual_overrides.pop(climate_id, None)
                else:
                    self.schedule_overrides[climate_id] = float(ov["target_temp"])
                    has_valid_manual_override = True

            if has_valid_manual_override:
                continue

            # 4. Smart Return waiting check:
            # If zone is in sr_plan but ignition time has not arrived yet, and scheduler is disabled, do not apply overrides
            if climate_id in sr_plan:
                if not self.scheduler_enabled:
                    self.schedule_overrides.pop(climate_id, None)
                    continue

            # 5. Weekly scheduler baseline & Predictive Smart Start
            if self.scheduler_enabled:
                self.schedule_overrides[climate_id] = float(slot["target_temp"])

                # Check predictive smart start for upcoming block
                upcoming = self.get_upcoming_blocks(climate_id, now, horizon_hours=12)
                future_blocks = [b for b in upcoming if b["start_dt"] > now]
                if future_blocks:
                    next_b = future_blocks[0]
                    if next_b["target_temp"] > slot["target_temp"]:
                        curr_temp = self._get_zone_current_temp(climate_id)
                        if curr_temp is not None and curr_temp < next_b["target_temp"]:
                            heating_rate = self._get_zone_heating_rate(climate_id)
                            hours_needed = min(
                                MAX_SMART_START_HOURS,
                                (next_b["target_temp"] - curr_temp) / heating_rate,
                            )
                            preheat_dt = next_b["start_dt"] - timedelta(hours=hours_needed)
                            check_now = now
                            if preheat_dt.tzinfo is not None and check_now.tzinfo is None:
                                check_now = check_now.replace(tzinfo=preheat_dt.tzinfo)
                            elif preheat_dt.tzinfo is None and check_now.tzinfo is not None:
                                preheat_dt = preheat_dt.replace(tzinfo=check_now.tzinfo)

                            if check_now >= preheat_dt:
                                self.schedule_overrides[climate_id] = float(next_b["target_temp"])
                                self.smart_start_info[climate_id] = {
                                    "target_temp": float(next_b["target_temp"]),
                                    "preset": next_b["preset"],
                                    "block_start": next_b["start_dt"].isoformat(),
                                    "preheat_start": preheat_dt.isoformat(),
                                    "heating_rate": round(heating_rate, 2),
                                    "source": "schedule",
                                }

        target_changed = old_overrides != self.schedule_overrides
        smart_start_changed = old_smart_start != self.smart_start_info
        if target_changed or smart_start_changed or profile_expired or smart_return_completed:
            self._notify_climates()

    def get_effective_target(self, climate_id: str) -> float | None:
        """Return currently scheduled effective target temperature for zone, or None."""
        if not self.scheduler_enabled and self.smart_return is None:
            return None
        return self.schedule_overrides.get(climate_id)

    def get_state_summary(self, now: datetime | None = None) -> dict[str, Any]:
        """Return complete summary for Lovelace UI."""
        if now is None:
            now = dt_util.now()
        sr_plan = {}
        if self.smart_return:
            sr_plan = self.calculate_smart_return_plan(
                self.smart_return["arrival_time"],
                self.smart_return.get("preset", "comfort"),
                self.smart_return.get("zones"),
                now,
            )

        preset_matrix = {}
        all_zones = getattr(self.coordinator, "zones", [])
        for p in ("comfort", "eco", "sleep", "away"):
            preset_matrix[p] = {}
            for z in all_zones:
                if z.get(CONF_ZONE_NAME):
                    cid = z.get("climate_id") or make_zone_entity_id(z.get(CONF_ZONE_NAME, ""))
                    preset_matrix[p][cid] = self._resolve_preset_temp(p, cid)

        return {
            "scheduler_enabled": self.scheduler_enabled,
            "active_profile": self.active_profile,
            "profile_expires_at": self.profile_expires_at,
            "fallback_profile": self.fallback_profile,
            "profiles": self.profiles,
            "manual_overrides": self.manual_overrides,
            "smart_start_info": self.smart_start_info,
            "smart_return": self.smart_return,
            "smart_return_plan": sr_plan,
            "preset_matrix": preset_matrix,
        }

    def _notify_climates(self, climate_ids: set[str] | list[str] | None = None) -> None:
        """Notify climate entities, switches and selects."""
        if hasattr(self.coordinator, "calendar_manager") and hasattr(
            self.coordinator.calendar_manager, "_notify_climates_and_sync_trvs"
        ):
            self.coordinator.calendar_manager._notify_climates_and_sync_trvs(climate_ids)
        else:
            target_ids = (
                climate_ids
                if climate_ids is not None
                else list(getattr(self.coordinator, "_climate_callbacks", {}).keys())
            )
            for cid in target_ids:
                cb = getattr(self.coordinator, "_climate_callbacks", {}).get(cid)
                if cb:
                    cb()

        for attr in ("_master_switch", "_scheduler_switch"):
            sw = getattr(self.coordinator, attr, None)
            if sw and hasattr(sw, "async_write_ha_state"):
                sw.async_write_ha_state()

        for attr in ("_profile_select", "_schedule_select"):
            sel = getattr(self.coordinator, attr, None)
            if sel and hasattr(sel, "async_write_ha_state"):
                sel.async_write_ha_state()

        selects = getattr(self.coordinator, "_select_entities", {})
        if isinstance(selects, dict):
            prof_select = selects.get("schedule_profile")
            if prof_select and hasattr(prof_select, "async_write_ha_state"):
                prof_select.async_write_ha_state()
