"""Unit tests validating fixes for BUG-06 through BUG-11 (Audit Medium Severity)."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

from custom_components.multizone_thermostat.schedule.storage import ScheduleProfileStorage
from custom_components.multizone_thermostat.schedule.slot_engine import ScheduleSlotEngine
from custom_components.multizone_thermostat.schedule.manager import ScheduleProfileManager
from custom_components.multizone_thermostat.select import (
    MultizoneGlobalPresetSelect,
    MultizoneZoneSelect,
    MultizoneDemandStrategySelect,
    MultizoneScheduleProfileSelect,
)
from custom_components.multizone_thermostat.coordinator import MultizoneCoordinator
from custom_components.multizone_thermostat.storage.storage_manager import StorageManager
from custom_components.multizone_thermostat.const import make_zone_entity_id


def test_bug06_profile_expiration_supports_time_string():
    """BUG-06: Profile expiration supports 'HH:MM' time string with automatic next-occurrence resolution."""
    storage = ScheduleProfileStorage(coordinator=MagicMock())
    storage.profiles = {"default": {}, "party": {}}

    mock_now = datetime(2026, 11, 7, 10, 0, 0)
    with patch("homeassistant.util.dt.now", return_value=mock_now):
        # Set expiration at 11:30 (today relative to mock_now)
        storage.activate_profile("party", expires_at="11:30", fallback_profile="default")
        assert storage.profile_expires_at is not None

        # At 10:15 -> not expired
        t_1015 = datetime(2026, 11, 7, 10, 15, 0)
        expired, _, _ = storage.check_profile_expiry(t_1015)
        assert expired is False

        # At 11:35 -> expired, reverts to default
        t_1135 = datetime(2026, 11, 7, 11, 35, 0)
        expired, old_p, new_p = storage.check_profile_expiry(t_1135)
        assert expired is True
        assert old_p == "party"
        assert new_p == "default"


def test_bug08_upcoming_blocks_includes_overnight_blocks_from_yesterday():
    """BUG-08: Upcoming blocks scan day_offset = -1 so overnight blocks started yesterday are detected."""
    engine = ScheduleSlotEngine(resolve_preset_temp_fn=lambda p, c: 21.0)
    profile = {
        "days": {
            "mon": {"climate.living": [{"start": "22:00", "end": "06:00", "preset": "comfort"}]},
            "tue": {"climate.living": [{"start": "12:00", "end": "14:00", "preset": "comfort"}]},
        }
    }

    # Tuesday Nov 10, 2026 at 02:00 AM: Monday 22:00 - Tuesday 06:00 block is currently active!
    t_tue_0200 = datetime(2026, 11, 10, 2, 0, 0)
    blocks = engine.get_upcoming_blocks(profile, "climate.living", t_tue_0200, horizon_hours=6)

    # Must contain the ongoing overnight block ending at 06:00 on Nov 10!
    assert len(blocks) >= 1
    found = any(
        b["start_dt"].day == 9 and b["start_dt"].hour == 22 and
        b["end_dt"].day == 10 and b["end_dt"].hour == 6
        for b in blocks
    )
    assert found


@pytest.mark.asyncio
async def test_bug09_predictive_smart_start_scans_all_future_blocks():
    """BUG-09: Predictive smart start evaluates all future blocks in horizon, not just future_blocks[0]."""
    coordinator = MagicMock()
    cid = "climate.living"
    coordinator.zones = [{"climate_id": cid}]
    coordinator._climate_entities = {}

    mgr = ScheduleProfileManager(coordinator=coordinator)
    mgr._notify_climates = MagicMock()
    mgr.scheduler_enabled = True

    now = datetime(2026, 11, 9, 6, 0, 0, tzinfo=timezone.utc)

    # 2 upcoming blocks:
    # 1. 06:15 - 06:30 (Eco, 18°C) -> target not higher than current baseline
    # 2. 07:00 - 12:00 (Comfort, 22°C) -> preheating needed!
    upcoming_blocks = [
        {
            "start_dt": datetime(2026, 11, 9, 6, 15, 0, tzinfo=timezone.utc),
            "end_dt": datetime(2026, 11, 9, 6, 30, 0, tzinfo=timezone.utc),
            "preset": "eco",
            "target_temp": 18.0,
        },
        {
            "start_dt": datetime(2026, 11, 9, 7, 0, 0, tzinfo=timezone.utc),
            "end_dt": datetime(2026, 11, 9, 12, 0, 0, tzinfo=timezone.utc),
            "preset": "comfort",
            "target_temp": 22.0,
        },
    ]

    mgr.get_upcoming_blocks = MagicMock(return_value=upcoming_blocks)
    mgr._get_zone_current_temp = MagicMock(return_value=19.0)
    mgr._get_zone_heating_rate = MagicMock(return_value=2.0)  # 2°C/h -> needs 1.5h preheat (start at 05:30)
    mgr.evaluate_zone_slot = MagicMock(return_value={"target_temp": 18.0, "preset": "eco", "slot_id": "slot1"})

    await mgr.async_evaluate_schedule(now=now)

    # Smart start must have activated for the 22.0°C comfort block!
    assert cid in mgr.smart_start_info
    assert mgr.smart_start_info[cid]["target_temp"] == 22.0
    assert mgr.schedule_overrides[cid] == 22.0


@pytest.mark.asyncio
async def test_bug10_select_removal_cleans_select_entities():
    """BUG-10: Select entity removal cleans up _select_entities dictionary."""
    coordinator = MagicMock()
    cid = make_zone_entity_id("Living")
    coordinator._select_entities = {
        "global_preset": MagicMock(),
        f"zone_mode_{cid}": MagicMock(),
        "demand_strategy": MagicMock(),
        "schedule_profile": MagicMock(),
    }

    p_sel = MultizoneGlobalPresetSelect(coordinator, "test")
    await p_sel.async_will_remove_from_hass()
    assert "global_preset" not in coordinator._select_entities

    z_sel = MultizoneZoneSelect(coordinator, "test", "Living")
    await z_sel.async_will_remove_from_hass()
    assert f"zone_mode_{cid}" not in coordinator._select_entities

    d_sel = MultizoneDemandStrategySelect(coordinator, "test")
    await d_sel.async_will_remove_from_hass()
    assert "demand_strategy" not in coordinator._select_entities

    s_sel = MultizoneScheduleProfileSelect(coordinator, "test")
    await s_sel.async_will_remove_from_hass()
    assert "schedule_profile" not in coordinator._select_entities


def test_bug11_reset_last_active_time_triggers_debounced_save():
    """BUG-11: reset_last_active_time triggers storage.debounced_save_settings to persist uptime across reboots."""
    coordinator = MagicMock()
    coordinator._last_active_time = 0.0
    coordinator._settings = {}
    coordinator.storage = MagicMock()

    # Call reset_last_active_time from coordinator implementation
    MultizoneCoordinator.reset_last_active_time(coordinator)

    assert coordinator._settings.get("last_active_wall_time") is not None
    assert coordinator.storage.debounced_save_settings.called
