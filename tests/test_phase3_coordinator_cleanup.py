"""Dedicated unit tests for Phase 3: Coordinator cleanup and delegation."""
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.multizone_thermostat.const import (
    CONF_BOILER_MODE,
    CONF_BOILER_SWITCH,
    CONF_MIN_CYCLE_OFF,
    CONF_MIN_CYCLE_ON,
    CONF_VALVE_DELAY,
    CONF_ZONE_NAME,
    CONF_ZONE_WINDOW_SENSOR,
    CONF_ZONES,
    DOMAIN,
    MODE_RELAY,
    ZONE_MODE_BYPASS,
    ZONE_MODE_PRIMARY,
    make_zone_entity_id,
)
from custom_components.multizone_thermostat.coordinator import MultizoneCoordinator
from custom_components.multizone_thermostat.zone_manager import ZoneManager


def _create_mock_entry(entry_id="test_cleanup_entry"):
    entry = MagicMock()
    entry.entry_id = entry_id
    entry.data = {
        CONF_BOILER_MODE: MODE_RELAY,
        CONF_BOILER_SWITCH: "switch.boiler",
        CONF_MIN_CYCLE_ON: 5.0,
        CONF_MIN_CYCLE_OFF: 3.0,
        CONF_VALVE_DELAY: 30.0,
        CONF_ZONES: [
            {
                CONF_ZONE_NAME: "Living Room",
                CONF_ZONE_WINDOW_SENSOR: "binary_sensor.living_room_window",
                "zone_climates": ["climate.living_room_trv"],
            },
            {
                CONF_ZONE_NAME: "Bedroom",
                CONF_ZONE_WINDOW_SENSOR: None,
                "zone_climates": ["climate.bedroom_trv"],
            },
        ],
    }
    return entry


def _create_test_coordinator():
    hass = MagicMock()
    hass.states.get.return_value = None
    hass.services.async_call = AsyncMock()
    coros = []
    def create_task(coro):
        coros.append(coro)
        return MagicMock()
    hass.async_create_task = MagicMock(side_effect=create_task)
    entry = _create_mock_entry()
    coord = MultizoneCoordinator(hass, entry)
    return coord, hass, entry, coros


def test_coordinator_removed_dead_attributes():
    """Verify that unused dead attributes were removed from coordinator."""
    coord, _, _, coros = _create_test_coordinator()

    # _last_boiler_change should no longer exist on coordinator (owned by boiler backend)
    assert not hasattr(coord, "_last_boiler_change")

    # These were previously duplicated dead attributes now owned by subsystems
    assert not hasattr(coord, "_anti_seize_running")
    assert not hasattr(coord, "_pre_anti_seize_state")
    assert not hasattr(coord, "_storage_save_pending")
    assert not hasattr(coord, "_calendar_active_event_id")
    assert not hasattr(coord, "_calendar_temp_overrides")
    assert not hasattr(coord, "_calendar_mode_overrides")
    assert not hasattr(coord, "_pre_calendar_preset")
    for c in coros:
        c.close()


def test_coordinator_aliases_to_subsystems():
    """Verify coordinator aliases correctly point to live subsystem dictionaries."""
    coord, _, _, coros = _create_test_coordinator()

    z_living = make_zone_entity_id("Living Room")

    # _zone_modes alias points to zone_manager._zone_modes
    assert coord._zone_modes is coord.zone_manager._zone_modes
    coord.zone_manager.set_zone_mode(z_living, "secondary")
    assert coord._zone_modes[z_living] == "secondary"

    # _zone_demands alias points to demand_aggregator._zone_demands
    assert coord._zone_demands is coord.demand_aggregator._zone_demands
    coord.demand_aggregator.set_zone_demand(z_living, 42.0)
    assert coord._zone_demands[z_living] == 42.0

    # _pre_window_state alias points to zone_manager._pre_window_state
    assert coord._pre_window_state is coord.zone_manager._pre_window_state
    coord.zone_manager._pre_window_state[z_living] = "heat"
    assert coord._pre_window_state[z_living] == "heat"
    for c in coros:
        c.close()


def test_coordinator_last_active_time():
    """Verify last_active_time property and reset_last_active_time method."""
    coord, _, _, coros = _create_test_coordinator()

    t0 = 1000.0
    with patch("time.monotonic", return_value=t0):
        coord.reset_last_active_time()
        assert coord.last_active_time == t0

    t1 = 1500.0
    with patch("time.monotonic", return_value=t1):
        coord.reset_last_active_time()
        assert coord.last_active_time == t1
    for c in coros:
        c.close()


def test_coordinator_setters_delegate_to_backend():
    """Verify set_min_cycle_on, set_min_cycle_off, set_valve_delay delegate cleanly."""
    coord, _, _, coros = _create_test_coordinator()

    assert coord._min_cycle_on == 5.0
    assert coord._min_cycle_off == 3.0
    assert coord._valve_delay == 30.0

    coord.set_min_cycle_on(10.0)
    assert coord._min_cycle_on == 10.0
    assert coord.boiler_backend._min_cycle_on == 10
    assert coord.boiler_backend._boiler_pwm.min_on == 600.0

    coord.set_min_cycle_off(8.0)
    assert coord._min_cycle_off == 8.0
    assert coord.boiler_backend._min_cycle_off == 8
    assert coord.boiler_backend._boiler_pwm.min_off == 480.0

    coord.set_valve_delay(45.0)
    assert coord._valve_delay == 45.0
    assert coord.boiler_backend._valve_delay == 45
    for c in coros:
        c.close()


def test_coordinator_unregister_climate_cleans_aggregator():
    """Verify unregister_climate cleans up callbacks in both coordinator and demand_aggregator."""
    coord, _, _, coros = _create_test_coordinator()

    cb = MagicMock()
    entity_id = "climate.living_room"
    coord.register_climate(entity_id, cb)

    assert entity_id in coord._climate_callbacks
    assert cb in coord.demand_aggregator._climate_callbacks[entity_id]

    coord.unregister_climate(entity_id)

    assert entity_id not in coord._climate_callbacks
    assert entity_id not in coord._climate_entities
    assert entity_id not in coord.demand_aggregator._climate_callbacks
    for c in coros:
        c.close()


@pytest.mark.asyncio
async def test_window_storage_isolation_and_migration():
    """Verify window storage isolates per entry and migrates legacy store."""
    coord, _, entry, coros = _create_test_coordinator()

    # Setup mocks for stores
    coord._store.async_load = AsyncMock(return_value=None)
    coord._store.async_save = AsyncMock()
    coord._legacy_window_store.async_load = AsyncMock(return_value={"climate.living_room": "heat"})
    coord._preset_store.async_load = AsyncMock(return_value={})
    coord._settings_store.async_load = AsyncMock(return_value={})

    await coord.async_load_storage()

    # Legacy store was migrated to entry-specific store
    coord._store.async_save.assert_called_with({"climate.living_room": "heat"})
    assert coord.zone_manager._pre_window_state == {"climate.living_room": "heat"}
    assert coord._pre_window_state == {"climate.living_room": "heat"}

    # Now modify pre_window_state and save
    coord.zone_manager._pre_window_state["climate.living_room"] = "eco"
    await coord.async_save_storage()
    coord._store.async_save.assert_called_with({"climate.living_room": "eco"})
    for c in coros:
        c.close()


@pytest.mark.asyncio
async def test_zone_manager_window_event_triggers_window_storage_save():
    """Verify that opening/closing window triggers async_save_storage instead of presets save."""
    coord, hass, _, coros = _create_test_coordinator()
    zm = coord.zone_manager

    zone_id = make_zone_entity_id("Living Room")
    coord.async_save_storage = AsyncMock()
    coord._async_save_presets_storage = AsyncMock()

    created_tasks = []
    def mock_create_task(coro):
        created_tasks.append(coro)
        return MagicMock()
    hass.async_create_task = mock_create_task

    # 1. Window OPEN
    ev_open = MagicMock()
    ev_open.data = {
        "entity_id": "binary_sensor.living_room_window",
        "new_state": MagicMock(state="on"),
    }
    zm.async_on_window_state_changed(ev_open)

    for t in created_tasks:
        await t
    created_tasks.clear()

    coord.async_save_storage.assert_called_once()
    coord._async_save_presets_storage.assert_not_called()
    assert zm._pre_window_state[zone_id] == ZONE_MODE_PRIMARY

    # 2. Window CLOSE
    coord.async_save_storage.reset_mock()
    coord._async_save_presets_storage.reset_mock()

    ev_close = MagicMock()
    ev_close.data = {
        "entity_id": "binary_sensor.living_room_window",
        "new_state": MagicMock(state="off"),
    }
    zm.async_on_window_state_changed(ev_close)

    for t in created_tasks:
        await t
    created_tasks.clear()

    coord.async_save_storage.assert_called_once()
    coord._async_save_presets_storage.assert_not_called()
    assert zone_id not in zm._pre_window_state


@pytest.mark.asyncio
async def test_shared_storage_no_split_brain_and_teardown_cleans_routine():
    """Verify coordinator and StorageManager share backing dicts/stores and teardown calls routine_manager.cleanup()."""
    coord, _, _, coros = _create_test_coordinator()

    assert coord._settings is coord.storage._settings
    assert coord._presets is coord.storage._presets
    assert coord._settings_store is coord.storage._settings_store

    coord._store.async_load = AsyncMock(return_value={})
    coord._preset_store.async_load = AsyncMock(return_value={"eco": {"climate.living_room": {"target_temp": 18.0}}})
    coord._settings_store.async_load = AsyncMock(return_value={})
    coord._settings_store.async_save = AsyncMock()

    # Load storage when settings_stored is empty -> presets must still be loaded into zone_manager
    await coord.async_load_storage()
    assert coord.zone_manager._presets == {"eco": {"climate.living_room": {"target_temp": 18.0}}}

    # Saving persistent data via coordinator must be visible in coord.storage.settings
    await coord.async_set_persistent_data("passive_heat_living_room", True)
    assert coord.storage.get_data("passive_heat_living_room") is True

    # Passive heat key lookup must match "passive_heat_living_room"
    z_living = make_zone_entity_id("Living Room")
    assert coord.zone_manager.is_passive_heat_allowed(z_living) is True

    # Teardown must invoke routine_manager.cleanup()
    coord.routine_manager.cleanup = MagicMock()
    coord.async_teardown_listeners()
    coord.routine_manager.cleanup.assert_called_once()
    for c in coros:
        c.close()
