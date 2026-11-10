"""Tests for ListenerManager and StorageManager coordinator storage loading."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from custom_components.multizone_thermostat.listener_manager import ListenerManager
from custom_components.multizone_thermostat.const import CONF_ZONE_NAME, CONF_ZONE_WINDOW_SENSOR, HVAC_MODE_COOL


@pytest.mark.asyncio
async def test_listener_manager_setup_and_teardown():
    coord = MagicMock()
    coord.hass = MagicMock()
    coord._unsub_listeners = []
    coord.zones = [
        {CONF_ZONE_NAME: "Living", CONF_ZONE_WINDOW_SENSOR: "binary_sensor.window_living"},
        {CONF_ZONE_NAME: "Bed", CONF_ZONE_WINDOW_SENSOR: "none"},
    ]
    coord.global_calendar_id = "calendar.heating"
    coord.energy_manager = MagicMock()
    coord.energy_manager.async_start = AsyncMock()
    coord.schedule_manager = MagicMock()
    coord.routine_manager = MagicMock()
    coord.anti_seize_manager = MagicMock()
    coord.plant_orchestrator = MagicMock()
    coord.boiler_backend = MagicMock()

    lm = ListenerManager(coord)
    
    with patch("custom_components.multizone_thermostat.listener_manager.async_track_state_change_event", return_value=lambda: None) as mock_state_track, \
         patch("custom_components.multizone_thermostat.listener_manager.async_track_time_interval", return_value=lambda: None) as mock_time_track:
        
        lm.async_setup_listeners()
        assert mock_state_track.call_count >= 2  # climate entities + window sensors
        assert mock_time_track.call_count >= 3   # pwm tick, anti-seize, calendar, schedule
        assert len(coord._unsub_listeners) > 0

    # Teardown
    unsub_mock = MagicMock()
    coord._unsub_listeners.append(unsub_mock)
    lm.async_teardown_listeners()
    assert unsub_mock.called
    assert len(coord._unsub_listeners) == 0


@pytest.mark.asyncio
async def test_listener_manager_climate_state_changed():
    coord = MagicMock()
    coord.zone_controller.async_update_zone = AsyncMock(return_value=75.0)
    coord.demand_aggregator.set_zone_demand = MagicMock()
    coord.plant_orchestrator._async_update_boiler = AsyncMock()

    lm = ListenerManager(coord)
    event = MagicMock()
    event.data = {"entity_id": "climate.living", "new_state": MagicMock()}

    await lm.async_on_climate_state_changed(event)

    coord.zone_controller.async_update_zone.assert_awaited_once_with("climate.living", event.data["new_state"])
    coord.demand_aggregator.set_zone_demand.assert_called_once_with("climate.living", 75.0)
    coord.plant_orchestrator._async_update_boiler.assert_awaited_once()


@pytest.mark.asyncio
async def test_storage_manager_load_coordinator_storage():
    from custom_components.multizone_thermostat.storage.storage_manager import StorageManager

    hass = MagicMock()
    storage = StorageManager(hass, "test_entry")

    storage._window_store.async_load = AsyncMock(return_value={"climate.living": "heat"})
    storage._settings_store.async_load = AsyncMock(return_value={"master_hvac_mode": HVAC_MODE_COOL, "zone_modes": {"climate.living": "primary"}})
    storage._preset_store.async_load = AsyncMock(return_value={"presets_heat": {"comfort": {"target_temp": 21.0}}, "presets_cool": {}})

    coord = MagicMock()
    coord._store = storage._window_store
    coord._settings_store = storage._settings_store
    coord._preset_store = storage._preset_store
    coord._legacy_window_store = storage._legacy_window_store
    coord._climate_callbacks = {"climate.living": MagicMock()}
    coord.zone_manager._pre_window_state = {}
    coord.demand_aggregator = MagicMock()
    coord._settings = storage._settings
    del coord.schedule_manager

    await storage.async_load_coordinator_storage(coord)

    assert coord.master_hvac_mode == HVAC_MODE_COOL
    assert coord.zone_manager._pre_window_state["climate.living"] == "heat"
    coord._climate_callbacks["climate.living"].assert_called_once()
