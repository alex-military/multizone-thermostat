"""Regression tests for Block 2 (Issue #12): Scheduler timeline & Global Preset sync."""
from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.meta_path[:] = [
    f for f in sys.meta_path if f.__class__.__name__ != "HomeAssistantMockFinder"
]
for _mod_name in (
    "homeassistant.components.select",
    "homeassistant.components.number",
    "homeassistant.components.switch",
    "homeassistant.components.button",
    "homeassistant.components.sensor",
    "homeassistant.helpers.restore_state",
    "homeassistant.helpers.entity",
):
    if _mod_name in sys.modules and isinstance(sys.modules[_mod_name], MagicMock):
        del sys.modules[_mod_name]

from custom_components.multizone_thermostat.const import (
    CONF_BOILER_MODE,
    CONF_PRESENCE_SENSOR,
    CONF_ZONE_NAME,
    CONF_ZONE_TEMP_SENSOR,
    CONF_ZONES,
    MODE_CENTRAL,
    make_zone_entity_id,
)
from custom_components.multizone_thermostat.coordinator import MultizoneCoordinator


def _make_coord(with_presence: bool = False):
    hass = MagicMock()
    hass.states = MagicMock()
    hass.states.get = MagicMock(return_value=None)
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.async_create_task = MagicMock()

    entry = SimpleNamespace(
        entry_id="issue12_entry",
        data={
            CONF_BOILER_MODE: MODE_CENTRAL,
            CONF_PRESENCE_SENSOR: "person.alex" if with_presence else None,
            CONF_ZONES: [
                {CONF_ZONE_NAME: "Giorno", CONF_ZONE_TEMP_SENSOR: "sensor.t1"},
                {CONF_ZONE_NAME: "Notte", CONF_ZONE_TEMP_SENSOR: "sensor.t2"},
            ],
        },
        options={},
    )
    coord = MultizoneCoordinator(hass, entry)
    coord.async_set_persistent_data = AsyncMock(
        side_effect=lambda k, v: coord._settings.__setitem__(k, v)
    )
    coord.schedule_manager.async_save_to_storage = AsyncMock()
    return coord


async def test_global_preset_syncs_with_active_weekly_schedule():
    coord = _make_coord()
    sched = coord.schedule_manager
    z1 = make_zone_entity_id("Giorno")
    z2 = make_zone_entity_id("Notte")

    global_sel_mock = MagicMock()
    global_sel_mock.async_write_ha_state = MagicMock()
    coord._select_entities["global_preset"] = global_sel_mock
    coord.zone_manager.set_global_preset("manual")

    sched.scheduler_enabled = True
    sched.profiles["standard"] = {
        "name": "Standard",
        "baseline_preset": "eco",
        "days": {
            "mon": {
                z1: [{"start": "06:00", "end": "09:00", "preset": "comfort"}],
                z2: [{"start": "06:00", "end": "09:00", "preset": "comfort"}],
            }
        },
    }
    sched.active_profile = "standard"

    # Monday 07:30 -> both zones in "comfort" -> Global Preset syncs to "comfort" without manual_overrides
    now_comfort = datetime(2026, 11, 9, 7, 30, tzinfo=timezone.utc)
    await sched.async_evaluate_schedule(now_comfort)
    assert coord.zone_manager.current_global_preset == "comfort"
    assert sched.manual_overrides == {}
    assert global_sel_mock.async_write_ha_state.called

    # Monday 11:00 -> outside blocks -> baseline "eco" -> Global Preset syncs to "eco"
    global_sel_mock.async_write_ha_state.reset_mock()
    now_eco = datetime(2026, 11, 9, 11, 0, tzinfo=timezone.utc)
    await sched.async_evaluate_schedule(now_eco)
    assert coord.zone_manager.current_global_preset == "eco"
    assert global_sel_mock.async_write_ha_state.called


async def test_global_preset_sync_respects_geofencing_away():
    coord = _make_coord(with_presence=True)
    sched = coord.schedule_manager
    z1 = make_zone_entity_id("Giorno")

    coord.zone_manager.set_global_preset("away")
    coord.routine_manager._last_known_presence = "not_home"
    sched.scheduler_enabled = True
    sched.profiles["standard"] = {
        "name": "Standard",
        "baseline_preset": "eco",
        "days": {"mon": {z1: [{"start": "06:00", "end": "09:00", "preset": "comfort"}]}},
    }
    sched.active_profile = "standard"

    await sched.async_evaluate_schedule(datetime(2026, 11, 9, 7, 30, tzinfo=timezone.utc))
    assert coord.zone_manager.current_global_preset == "away"


async def test_global_preset_preserves_state_when_all_zones_have_manual_overrides():
    coord = _make_coord()
    sched = coord.schedule_manager
    z1 = make_zone_entity_id("Giorno")
    z2 = make_zone_entity_id("Notte")

    coord.zone_manager.set_global_preset("sleep")
    sched.scheduler_enabled = True
    sched.profiles["standard"] = {
        "name": "Standard",
        "baseline_preset": "eco",
        "days": {
            "mon": {
                z1: [{"start": "06:00", "end": "09:00", "preset": "comfort"}],
                z2: [{"start": "06:00", "end": "09:00", "preset": "comfort"}],
            }
        },
    }
    sched.active_profile = "standard"

    now_slot = datetime(2026, 11, 9, 7, 30, tzinfo=timezone.utc)
    slot_id_1 = sched.evaluate_zone_slot(z1, now_slot)["slot_id"]
    slot_id_2 = sched.evaluate_zone_slot(z2, now_slot)["slot_id"]
    sched.manual_overrides[z1] = {
        "target_temp": 18.0,
        "until": datetime(2026, 11, 9, 9, 0, tzinfo=timezone.utc).isoformat(),
        "slot_id": slot_id_1,
    }
    sched.manual_overrides[z2] = {
        "target_temp": 18.0,
        "until": datetime(2026, 11, 9, 9, 0, tzinfo=timezone.utc).isoformat(),
        "slot_id": slot_id_2,
    }

    await sched.async_evaluate_schedule(now_slot)
    assert coord.zone_manager.current_global_preset == "sleep"


def test_scheduler_card_ruler_alignment_and_general_timeline_bundle():
    build_path = Path(__file__).resolve().parents[1] / "frontend" / "build.py"
    spec = importlib.util.spec_from_file_location("build", build_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.build(check_only=True) is True

    bundle_path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "multizone_thermostat"
        / "www"
        / "multizone-thermostat-card.js"
    )
    content = bundle_path.read_text(encoding="utf-8")
    for marker in (
        "ruler-spacer",
        "ruler-track",
        "leftPct = (i * 100) / 12",
        "baseline-block",
        "general-master-row",
        "manual-override-block",
        "_computeBaselineGaps",
        "_computeGeneralDayBlocks",
    ):
        assert marker in content
