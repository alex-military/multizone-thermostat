"""Unit tests for ScheduleSlotEngine."""
from datetime import datetime, timedelta
import pytest

from custom_components.multizone_thermostat.schedule.slot_engine import ScheduleSlotEngine


def test_parse_block_times_standard():
    """Verify standard start and end times."""
    engine = ScheduleSlotEngine()
    ref = datetime(2026, 11, 9, 0, 0, 0)  # Monday
    s, e = engine.parse_block_times({"start": "08:30", "end": "17:45"}, ref)
    assert s == datetime(2026, 11, 9, 8, 30, 0)
    assert e == datetime(2026, 11, 9, 17, 45, 0)


def test_parse_block_times_end_at_24_00():
    """Verify 24:00 ends at midnight next day."""
    engine = ScheduleSlotEngine()
    ref = datetime(2026, 11, 9, 0, 0, 0)
    s, e = engine.parse_block_times({"start": "18:00", "end": "24:00"}, ref)
    assert s == datetime(2026, 11, 9, 18, 0, 0)
    assert e == datetime(2026, 11, 10, 0, 0, 0)


def test_evaluate_zone_slot_active_block():
    """Verify active block match."""
    engine = ScheduleSlotEngine(resolve_preset_temp_fn=lambda p, c: 21.0 if p == "comfort" else 18.0)
    profile = {
        "baseline_preset": "eco",
        "days": {
            "mon": {
                "climate.living": [
                    {"start": "08:00", "end": "12:00", "preset": "comfort"}
                ]
            }
        },
    }
    # 2026-11-09 is a Monday
    now = datetime(2026, 11, 9, 10, 0, 0)
    res = engine.evaluate_zone_slot(profile, "climate.living", now)
    assert res["state_type"] == "block"
    assert res["preset"] == "comfort"
    assert res["target_temp"] == 21.0
    assert res["until"].hour == 12
    assert res["until"].minute == 0


def test_evaluate_zone_slot_gap_fallback():
    """Verify gap between blocks falls back to baseline preset."""
    engine = ScheduleSlotEngine(resolve_preset_temp_fn=lambda p, c: 21.0 if p == "comfort" else 18.0)
    profile = {
        "baseline_preset": "eco",
        "days": {
            "mon": {
                "climate.living": [
                    {"start": "18:00", "end": "22:00", "preset": "comfort"}
                ]
            }
        },
    }
    # 14:00 is outside defined block -> baseline eco
    now = datetime(2026, 11, 9, 14, 0, 0)
    res = engine.evaluate_zone_slot(profile, "climate.living", now)
    assert res["state_type"] == "baseline"
    assert res["preset"] == "eco"
    assert res["target_temp"] == 18.0
    assert res["until"].hour == 18
    assert res["until"].minute == 0
