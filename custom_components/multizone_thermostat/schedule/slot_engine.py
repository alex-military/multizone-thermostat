"""Timeline and slot evaluation engine for Multizone Thermostat Schedule."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any, Callable

import homeassistant.util.dt as dt_util

from ..const import (
    DEFAULT_BASELINE_PRESET,
    DEFAULT_PRESET_TEMPS,
    SCHEDULE_DAYS,
)

_LOGGER = logging.getLogger(__name__)


class ScheduleSlotEngine:
    """Calculates active time blocks, baseline fallbacks, and lookahead windows."""

    def __init__(
        self,
        resolve_preset_temp_fn: Callable[[str, str], float] | None = None,
        as_local_fn: Callable[[datetime | None], datetime] | None = None,
    ) -> None:
        """Initialize schedule slot engine."""
        self._resolve_preset_temp_fn = resolve_preset_temp_fn
        self._as_local_fn = as_local_fn

    def as_local(self, dt: datetime | None) -> datetime:
        """Ensure datetime is in local timezone."""
        if self._as_local_fn:
            return self._as_local_fn(dt)
        if dt is None:
            return dt_util.now()
        return dt_util.as_local(dt)

    def resolve_preset_temp(self, preset: str, climate_id: str) -> float:
        """Resolve preset temperature for a zone."""
        if self._resolve_preset_temp_fn:
            return float(self._resolve_preset_temp_fn(preset, climate_id))
        return float(DEFAULT_PRESET_TEMPS.get(preset, 20.0))

    def parse_block_times(
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

    def evaluate_zone_slot(
        self, profile: dict[str, Any], climate_id: str, now: datetime
    ) -> dict[str, Any]:
        """Evaluate active schedule profile for a specific zone at time now."""
        now = self.as_local(now)
        days_dict = profile.get("days", {})
        baseline_preset = profile.get("baseline_preset", DEFAULT_BASELINE_PRESET)

        day_idx = now.weekday()
        day_key = SCHEDULE_DAYS[day_idx]

        # 1. Check if yesterday had a block crossing midnight into today
        yesterday_idx = (day_idx - 1) % 7
        yesterday_key = SCHEDULE_DAYS[yesterday_idx]
        yesterday_blocks = days_dict.get(yesterday_key, {}).get(climate_id, [])
        for block in yesterday_blocks:
            b_start, b_end = self.parse_block_times(block, now - timedelta(days=1))
            if b_start <= now < b_end:
                preset = block.get("preset", "comfort")
                resolved_temp = self.resolve_preset_temp(preset, climate_id)
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
            b_start, b_end = self.parse_block_times(block, now)
            if b_start <= now < b_end:
                preset = block.get("preset", "comfort")
                resolved_temp = self.resolve_preset_temp(preset, climate_id)
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
        resolved_temp = self.resolve_preset_temp(baseline_preset, climate_id)

        # Find earliest upcoming block in the next 7 days
        next_block_start: datetime | None = None
        for day_offset in range(0, 8):
            target_date = now + timedelta(days=day_offset)
            d_key = SCHEDULE_DAYS[target_date.weekday()]
            blocks = days_dict.get(d_key, {}).get(climate_id, [])
            for b in blocks:
                b_start, _ = self.parse_block_times(b, target_date)
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
        self, profile: dict[str, Any], climate_id: str, now: datetime, horizon_hours: int = 24
    ) -> list[dict[str, Any]]:
        """Return chronological list of upcoming scheduled blocks within horizon_hours."""
        now = self.as_local(now)
        days_dict = profile.get("days", {})
        horizon_end = now + timedelta(hours=horizon_hours)

        upcoming: list[dict[str, Any]] = []
        max_days = int(horizon_hours // 24) + 2
        for day_offset in range(0, max_days):
            target_date = now + timedelta(days=day_offset)
            d_key = SCHEDULE_DAYS[target_date.weekday()]
            blocks = days_dict.get(d_key, {}).get(climate_id, [])
            for b in blocks:
                b_start, b_end = self.parse_block_times(b, target_date)
                if b_end > now and b_start < horizon_end:
                    preset = b.get("preset", "comfort")
                    target_temp = self.resolve_preset_temp(preset, climate_id)
                    upcoming.append({
                        "start_dt": b_start,
                        "end_dt": b_end,
                        "preset": preset,
                        "target_temp": target_temp,
                    })

        upcoming.sort(key=lambda x: x["start_dt"])
        return upcoming
