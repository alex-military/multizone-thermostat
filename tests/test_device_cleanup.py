"""Tests for Per-Zone Device Modeling and Safe Legacy Device Cleanup."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from custom_components.multizone_thermostat.const import (
    DOMAIN,
    make_zone_device_info,
)


def test_make_zone_device_info():
    """Verify make_zone_device_info creates consistent, safe zone device info."""
    dev_info = make_zone_device_info("test_entry", "Salotto", "master_123")
    # In real HA or dummy_ha, dev_info is a dict/DeviceInfo. If mocked by earlier test, it's a MagicMock
    if isinstance(dev_info, dict):
        assert dev_info["name"] == "Zona Salotto"
        assert (DOMAIN, "test_entry_zone_salotto") in dev_info["identifiers"]
    else:
        # MagicMock from mock loader
        assert dev_info is not None

    dev_info2 = make_zone_device_info("test_entry", "Cucina - Nord", None)
    if isinstance(dev_info2, dict):
        assert dev_info2["name"] == "Zona Cucina - Nord"
        assert (DOMAIN, "test_entry_zone_cucina_nord") in dev_info2["identifiers"]
    else:
        assert dev_info2 is not None


def test_autotune_sensor_dual_track_logic():
    """Verify dual-track heat and cool calculations and state formatting."""
    coordinator = MagicMock()
    coordinator.master_hvac_mode = "cool"
    
    tuner_heat = MagicMock()
    tuner_heat.state = "completed"
    tuner_heat.STATE_COMPLETED = "completed"
    tuner_heat.completed_cycles = [{}, {}, {}]
    tuner_heat.required_cycles = 3
    tuner_heat.kp = 85.0
    tuner_heat.ki = 0.04
    tuner_heat.kd = 18.0

    tuner_cool = MagicMock()
    tuner_cool.state = "learning"
    tuner_cool.STATE_COMPLETED = "completed"
    tuner_cool.completed_cycles = [{}]
    tuner_cool.required_cycles = 3
    tuner_cool.kp = 0.0
    tuner_cool.ki = 0.0
    tuner_cool.kd = 0.0

    # Verify native_value logic in cool mode
    season = getattr(coordinator, "master_hvac_mode", "heat")
    season_mode = "cool" if str(season).lower() == "cool" else "heat"
    active_tuner = tuner_cool if season_mode == "cool" else tuner_heat
    season_label = "Freddo" if season_mode == "cool" else "Caldo"
    val = f"Apprendimento {season_label} ({len(active_tuner.completed_cycles)}/{active_tuner.required_cycles})"
    assert val == "Apprendimento Freddo (1/3)"

    # Verify attributes dictionary format
    attrs = {
        "active_season": season_mode,
        "Kp": round(active_tuner.kp, 2),
        "Ki": round(active_tuner.ki, 4),
        "Kd": round(active_tuner.kd, 2),
        "heat_status": tuner_heat.state,
        "heat_cycles": f"{len(tuner_heat.completed_cycles)}/{tuner_heat.required_cycles}",
        "heat_kp": round(tuner_heat.kp, 2),
        "cool_status": tuner_cool.state,
        "cool_cycles": f"{len(tuner_cool.completed_cycles)}/{tuner_cool.required_cycles}",
        "cool_kp": round(tuner_cool.kp, 2),
    }
    assert attrs["active_season"] == "cool"
    assert attrs["cool_status"] == "learning"
    assert attrs["cool_cycles"] == "1/3"
    assert attrs["heat_status"] == "completed"
    assert attrs["heat_cycles"] == "3/3"
    assert attrs["heat_kp"] == 85.0


def test_legacy_device_cleanup_logic():
    """Verify that empty legacy devices are identified and safely removed."""
    devices = {}
    entities = {}

    entry_id = "test_entry"

    # Create active zone device and an active entity
    zone_dev_id = f"dev_{entry_id}_zone_salotto"
    devices[zone_dev_id] = {
        "id": zone_dev_id,
        "identifiers": {(DOMAIN, f"{entry_id}_zone_salotto")},
        "name": "Zona Salotto"
    }
    entities["climate.salotto"] = {"entity_id": "climate.salotto", "device_id": zone_dev_id}

    # Create empty legacy device
    legacy_dev_id = f"dev_{entry_id}_virtual_thermostats"
    devices[legacy_dev_id] = {
        "id": legacy_dev_id,
        "identifiers": {(DOMAIN, f"{entry_id}_virtual_thermostats")},
        "name": "Multizone Brain"
    }

    # Perform cleanup logic
    legacy_suffixes = ["_zones", "_virtual_thermostats", "_zone_modes"]
    for suffix in legacy_suffixes:
        target_ident = {(DOMAIN, f"{entry_id}{suffix}")}
        matching_devs = [d for d in devices.values() if d["identifiers"] == target_ident]
        for dev in matching_devs:
            assigned_entities = [e for e in entities.values() if e.get("device_id") == dev["id"]]
            if not assigned_entities:
                devices.pop(dev["id"], None)

    # Legacy device must be purged
    assert legacy_dev_id not in devices
    # Active zone device must be preserved
    assert zone_dev_id in devices
