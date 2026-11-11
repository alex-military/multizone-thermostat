"""Storage and profile persistence engine for Multizone Thermostat Schedule."""
from __future__ import annotations

import copy
from datetime import datetime, timedelta, time
import logging
from typing import Any

import homeassistant.util.dt as dt_util

from ..const import (
    DEFAULT_BASELINE_PRESET,
    DEFAULT_SCHEDULE_PROFILE,
    KEY_ACTIVE_PROFILE,
    KEY_FALLBACK_PROFILE,
    KEY_MANUAL_OVERRIDES,
    KEY_PROFILE_EXPIRES_AT,
    KEY_SCHEDULE_PROFILES,
    KEY_SCHEDULER_ENABLED,
    KEY_SMART_RETURN,
    SCHEDULE_DAYS,
    make_zone_entity_id,
)

_LOGGER = logging.getLogger(__name__)


def _parse_time_str(val: str):
    """Parse HH:MM or HH:MM:SS string to datetime.time."""
    if not isinstance(val, str):
        return None
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(val.strip(), fmt).time()
        except ValueError:
            pass
    return None


def default_profiles_dict() -> dict[str, dict[str, Any]]:
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


class ScheduleProfileStorage:
    """Encapsulates persistent state and CRUD operations for schedule profiles."""

    def __init__(self, coordinator: Any) -> None:
        """Initialize schedule profile storage."""
        self.coordinator = coordinator
        self.scheduler_enabled: bool = False
        self.active_profile: str = DEFAULT_SCHEDULE_PROFILE
        self.profile_expires_at: str | None = None
        self.fallback_profile: str = DEFAULT_SCHEDULE_PROFILE
        self.profiles: dict[str, dict[str, Any]] = default_profiles_dict()
        self.manual_overrides: dict[str, dict[str, Any]] = {}
        self.smart_return: dict[str, Any] | None = None

    def load_from_storage(self) -> None:
        """Load schedule state from coordinator persistent settings."""
        self.scheduler_enabled = bool(
            self.coordinator.get_persistent_data(KEY_SCHEDULER_ENABLED, False)
        )
        saved_profile = self.coordinator.get_persistent_data(KEY_ACTIVE_PROFILE, DEFAULT_SCHEDULE_PROFILE)
        self.active_profile = str(saved_profile) if saved_profile is not None else DEFAULT_SCHEDULE_PROFILE
        self.profile_expires_at = self.coordinator.get_persistent_data(
            KEY_PROFILE_EXPIRES_AT, None
        )
        saved_fallback = self.coordinator.get_persistent_data(KEY_FALLBACK_PROFILE, DEFAULT_SCHEDULE_PROFILE)
        self.fallback_profile = str(saved_fallback) if saved_fallback is not None else DEFAULT_SCHEDULE_PROFILE

        saved_profiles = self.coordinator.get_persistent_data(KEY_SCHEDULE_PROFILES)
        defaults = default_profiles_dict()
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

    def save_profile(self, profile_id: str, profile_data: dict[str, Any]) -> None:
        """Normalize and store profile data in memory."""
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

    def duplicate_profile(self, source_id: str, target_id: str, target_name: str | None = None) -> None:
        """Deep duplicate an existing profile into target_id."""
        if source_id not in self.profiles:
            raise ValueError(f"Source profile '{source_id}' does not exist")
        new_prof = copy.deepcopy(self.profiles[source_id])
        if target_name is not None:
            new_prof["name"] = target_name
        else:
            new_prof["name"] = f"Copy of {new_prof.get('name', source_id)}"
        self.profiles[target_id] = new_prof

    def activate_profile(
        self,
        profile_id: str,
        expires_at: str | datetime | None = None,
        fallback_profile: str = DEFAULT_SCHEDULE_PROFILE,
    ) -> None:
        """Activate profile and set optional expiration."""
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
            exp_str = expires_at.strip()
            # If HH:MM or HH:MM:SS format, resolve against current date
            t_obj = _parse_time_str(exp_str)
            if t_obj is not None:
                now_local = dt_util.now()
                target_dt = now_local.replace(
                    hour=t_obj.hour, minute=t_obj.minute, second=t_obj.second, microsecond=0
                )
                if target_dt <= now_local:
                    target_dt += timedelta(days=1)
                self.profile_expires_at = target_dt.isoformat()
            else:
                self.profile_expires_at = exp_str
        else:
            self.profile_expires_at = None

        self.fallback_profile = fallback_profile or DEFAULT_SCHEDULE_PROFILE

    def check_profile_expiry(self, now: datetime) -> tuple[bool, str | None, str | None]:
        """Check if profile expired. Returns (expired, old_profile, new_profile)."""
        if not self.profile_expires_at:
            return False, None, None

        parsed_exp = dt_util.parse_datetime(self.profile_expires_at)
        if parsed_exp is None:
            try:
                parsed_exp = datetime.fromisoformat(self.profile_expires_at)
            except Exception:
                # Fallback: check if time-only string
                t_obj = _parse_time_str(self.profile_expires_at)
                if t_obj is not None:
                    check_now = now
                    parsed_exp = check_now.replace(
                        hour=t_obj.hour, minute=t_obj.minute, second=t_obj.second, microsecond=0
                    )
                else:
                    self.profile_expires_at = None
                    return False, None, None

        check_now = now
        if parsed_exp.tzinfo is not None and check_now.tzinfo is None:
            check_now = check_now.replace(tzinfo=parsed_exp.tzinfo)
        elif parsed_exp.tzinfo is None and check_now.tzinfo is not None:
            parsed_exp = parsed_exp.replace(tzinfo=check_now.tzinfo)

        if check_now >= parsed_exp:
            old_profile = self.active_profile
            self.active_profile = self.fallback_profile or DEFAULT_SCHEDULE_PROFILE
            self.profile_expires_at = None
            return True, old_profile, self.active_profile
        return False, None, None

    def get_valid_manual_override(
        self, climate_id: str, current_slot_id: str, now: datetime
    ) -> float | None:
        """Validate and return manual override target temperature, or None if expired/slot changed."""
        if climate_id not in self.manual_overrides:
            return None

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

        if is_expired or (ov_slot_id and ov_slot_id != current_slot_id):
            self.manual_overrides.pop(climate_id, None)
            return None

        return float(ov["target_temp"])
