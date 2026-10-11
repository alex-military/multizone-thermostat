"""Tests for Calendar Manager."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone

import homeassistant.util.dt as dt_util
import pytest

from custom_components.multizone_thermostat.calendar_manager import CalendarManager
from custom_components.multizone_thermostat.const import CONF_ZONE_NAME

@pytest.fixture
def mock_coordinator():
    coord = MagicMock()
    coord.hass = MagicMock()
    coord.hass.services = AsyncMock()
    coord.hass.services.async_call = AsyncMock()
    coord.global_calendar_id = "calendar.test"
    coord.zones = [{CONF_ZONE_NAME: "Living Room"}, {CONF_ZONE_NAME: "Bedroom"}]
    
    # Mocks for Zone Manager
    coord.zone_manager = MagicMock()
    coord.zone_manager.current_global_preset = "eco"
    coord.zone_manager._presets = {
        "comfort": {"climate.multizone_thermostat_living_room": {"target_temp": 22.0}}
    }
    coord.zone_manager.async_set_global_preset = AsyncMock()
    coord.async_set_global_preset = coord.zone_manager.async_set_global_preset
    coord._async_save_presets_storage = AsyncMock()
    
    coord._select_entities = {}
    
    # Climate callbacks
    cb1 = MagicMock()
    cb2 = MagicMock()
    coord._climate_callbacks = {
        "climate.multizone_thermostat_living_room": cb1,
        "climate.multizone_thermostat_bedroom": cb2
    }
    
    # Thermal models
    tm = MagicMock()
    tm.heating_rate = 1.0 # 1 deg per hour
    coord._thermal_models = {
        "climate.multizone_thermostat_living_room": tm
    }
    
    return coord


@pytest.mark.asyncio
@patch('custom_components.multizone_thermostat.calendar_manager.dt_util')
async def test_calendar_no_events(mock_dt_util, mock_coordinator):
    """Test calendar parsing when no events are returned."""
    manager = CalendarManager(mock_coordinator)
    now = datetime.now(timezone.utc)
    mock_dt_util.utcnow.return_value = now
    
    # Mock empty response
    mock_coordinator.hass.services.async_call.return_value = {"calendar.test": {"events": []}}
    
    await manager.async_check_global_calendar(now)
    
    assert manager.active_event_id is None
    assert len(manager.temp_overrides) == 0


@pytest.mark.asyncio
@patch('custom_components.multizone_thermostat.calendar_manager.dt_util')
async def test_calendar_current_event(mock_dt_util, mock_coordinator):
    """Test calendar applying a current event."""
    manager = CalendarManager(mock_coordinator)
    now = datetime.now(timezone.utc)
    mock_dt_util.utcnow.return_value = now
    mock_dt_util.DEFAULT_TIME_ZONE = timezone.utc
    mock_dt_util.as_local.side_effect = lambda x: x
    mock_dt_util.parse_datetime.side_effect = lambda x: datetime.fromisoformat(x.replace('Z', '+00:00')) if x else None
    
    # Event that started 1 hour ago and ends in 1 hour
    start = (now - timedelta(hours=1)).isoformat()
    end = (now + timedelta(hours=1)).isoformat()
    
    # Summary with a global preset override
    mock_coordinator.hass.services.async_call.return_value = {
        "calendar.test": {
            "events": [
                {
                    "start": start,
                    "end": end,
                    "summary": "comfort"
                }
            ]
        }
    }
    
    await manager.async_check_global_calendar(now)
    
    assert manager.active_event_id == f"{start}_comfort"
    assert manager.pre_calendar_preset == "eco"
    mock_coordinator.async_set_global_preset.assert_called_once_with("comfort")
    
    # Verify callbacks were called to refresh climates
    mock_coordinator._climate_callbacks["climate.multizone_thermostat_living_room"].assert_called()


@pytest.mark.asyncio
@patch('custom_components.multizone_thermostat.calendar_manager.dt_util')
async def test_calendar_smart_start(mock_dt_util, mock_coordinator):
    """Test Smart Start triggering for an upcoming event."""
    manager = CalendarManager(mock_coordinator)
    now = datetime.now(timezone.utc)
    mock_dt_util.utcnow.return_value = now
    mock_dt_util.DEFAULT_TIME_ZONE = timezone.utc
    mock_dt_util.as_local.side_effect = lambda x: x
    mock_dt_util.parse_datetime.side_effect = lambda x: datetime.fromisoformat(x.replace('Z', '+00:00')) if x else None
    
    # Event starting in 30 minutes, requires heating
    start = (now + timedelta(minutes=30)).isoformat()
    end = (now + timedelta(hours=2)).isoformat()
    
    # Mock current temperature in HA to be 20.0
    state_mock = MagicMock()
    state_mock.attributes = {"current_temperature": 20.0}
    mock_coordinator.hass.states.get.return_value = state_mock
    
    # Summary specifies global temp 22.0
    mock_coordinator.hass.services.async_call.return_value = {
        "calendar.test": {
            "events": [
                {
                    "start": start,
                    "end": end,
                    "summary": "22.0"
                }
            ]
        }
    }
    
    await manager.async_check_global_calendar(now)
    
    # Delta T is 2.0. Heating rate is 1.0 deg/h. Needs 2 hours.
    # Start is in 30 mins (0.5 h). We have less time than needed (0.5 < 2.0).
    # So we should start heating NOW (Smart Start Triggered)
    
    assert "climate.multizone_thermostat_living_room" in manager.temp_overrides
    assert manager.temp_overrides["climate.multizone_thermostat_living_room"] == 22.0
    
    # Verify callback triggered to wake up zone
    mock_coordinator._climate_callbacks["climate.multizone_thermostat_living_room"].assert_called()
