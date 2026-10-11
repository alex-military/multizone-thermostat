"""Tests for RoutineManager."""
import asyncio
import datetime
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

from custom_components.multizone_thermostat.routine_manager import RoutineManager
from custom_components.multizone_thermostat.const import (
    KEY_NIGHT_TIME,
    KEY_AUTO_NIGHT_MODE,
    GLOBAL_PRESET_COMFORT,
)


@pytest.mark.asyncio
async def test_geofencing_everyone_left():
    hass = MagicMock()
    coros = []
    def create_task(coro):
        coros.append(coro)
        return MagicMock()
    hass.async_create_task = MagicMock(side_effect=create_task)
    
    get_persistent_data = MagicMock(return_value=True)
    async_set_persistent_data = AsyncMock()
    get_current_global_preset = MagicMock(return_value=GLOBAL_PRESET_COMFORT)
    async_set_global_preset = AsyncMock()
    
    manager = RoutineManager(
        hass, "sensor", get_persistent_data, async_set_persistent_data,
        get_current_global_preset, async_set_global_preset
    )
    
    event = MagicMock()
    event.data = {"old_state": MagicMock(state="home"), "new_state": MagicMock(state="not_home")}
    manager._async_on_presence_changed(event)
    
    assert hass.async_create_task.call_count == 2
    for c in coros:
        await c


@pytest.mark.asyncio
async def test_auto_night():
    hass = MagicMock()
    coros = []
    def create_task(coro):
        coros.append(coro)
        return MagicMock()
    hass.async_create_task = MagicMock(side_effect=create_task)
    
    def get_data(key, default=None):
        if key == KEY_AUTO_NIGHT_MODE:
            return True
        if key == KEY_NIGHT_TIME:
            return "22:30"
        return default
        
    get_persistent_data = MagicMock(side_effect=get_data)
    async_set_persistent_data = AsyncMock()
    get_current_global_preset = MagicMock(return_value=GLOBAL_PRESET_COMFORT)
    async_set_global_preset = AsyncMock()
    
    manager = RoutineManager(
        hass, "sensor", get_persistent_data, async_set_persistent_data,
        get_current_global_preset, async_set_global_preset
    )
    
    now = datetime.datetime(2023, 1, 1, 22, 30)
    with patch("custom_components.multizone_thermostat.routine_manager.dt_util.now", return_value=now):
        manager._async_check_schedule(now)
        assert hass.async_create_task.call_count == 2
        for c in coros:
            await c
