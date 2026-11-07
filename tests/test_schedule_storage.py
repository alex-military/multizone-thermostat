"""Unit tests for ScheduleProfileStorage."""
from unittest.mock import MagicMock
import pytest

from custom_components.multizone_thermostat.const import (
    DEFAULT_BASELINE_PRESET,
    DEFAULT_SCHEDULE_PROFILE,
    KEY_ACTIVE_PROFILE,
    KEY_SCHEDULE_PROFILES,
    KEY_SCHEDULER_ENABLED,
)
from custom_components.multizone_thermostat.schedule.storage import (
    ScheduleProfileStorage,
    default_profiles_dict,
)


def test_default_profiles():
    """Verify base profiles dictionary keys."""
    profiles = default_profiles_dict()
    assert "standard" in profiles
    assert "smart_working" in profiles
    assert "holiday" in profiles
    assert profiles["standard"]["baseline_preset"] == DEFAULT_BASELINE_PRESET


def test_load_from_storage_defaults():
    """Verify loading from coordinator with empty data populates standard defaults."""
    coord = MagicMock()
    coord.get_persistent_data = MagicMock(return_value=None)

    store = ScheduleProfileStorage(coord)
    store.load_from_storage()

    assert store.scheduler_enabled is False
    assert store.active_profile == DEFAULT_SCHEDULE_PROFILE
    assert "standard" in store.profiles
    assert "smart_working" in store.profiles
    assert "holiday" in store.profiles


def test_duplicate_profile():
    """Verify duplicating an existing profile."""
    coord = MagicMock()
    coord.get_persistent_data = MagicMock(return_value=None)

    store = ScheduleProfileStorage(coord)
    store.load_from_storage()

    store.duplicate_profile("standard", "custom_work", target_name="Lavoro Flessibile")
    assert "custom_work" in store.profiles
    assert store.profiles["custom_work"]["name"] == "Lavoro Flessibile"


def test_save_profile_normalization():
    """Verify block normalization and sorting by start time."""
    coord = MagicMock()
    coord.get_persistent_data = MagicMock(return_value=None)

    store = ScheduleProfileStorage(coord)
    store.load_from_storage()

    p_data = {
        "name": "Test Profile",
        "baseline_preset": "eco",
        "days": {
            "mon": {
                "climate.living": [
                    {"start": "18:00", "end": "22:00", "preset": "comfort"},
                    {"start": "06:00", "end": "08:00", "preset": "comfort"},
                ]
            }
        },
    }
    store.save_profile("test_p", p_data)

    mon_blocks = store.profiles["test_p"]["days"]["mon"]["climate.living"]
    assert len(mon_blocks) == 2
    # Verify sorted by start time
    assert mon_blocks[0]["start"] == "06:00"
    assert mon_blocks[1]["start"] == "18:00"
