"""Tests for proportional and 0-10V valve control."""
from unittest.mock import AsyncMock, MagicMock
import pytest

from homeassistant.components.climate import HVACMode
from custom_components.multizone_thermostat.const import (
    VALVE_SCALE_PERCENT,
    VALVE_SCALE_VOLT,
)
from custom_components.multizone_thermostat.sync_manager import ZoneSyncManager


@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    return hass


@pytest.fixture
def mock_coordinator():
    coordinator = MagicMock()
    coordinator.get_zone_demand.return_value = 65.0
    coordinator.get_zone_mode.return_value = "primary"
    return coordinator


@pytest.mark.asyncio
async def test_proportional_valve_percent_scale(mock_hass, mock_coordinator):
    """Test proportional valve with 0-100% scale."""
    sm = ZoneSyncManager(
        hass=mock_hass,
        coordinator=mock_coordinator,
        zone_name="Living Room",
        entity_id="climate.living_room",
        climates=[],
        switches=[],
        calibrations={},
        valves=["number.underfloor_valve_1", "valve.smart_valve_1"],
        valve_scale=VALVE_SCALE_PERCENT,
    )

    await sm.async_sync_proportional_valves(HVACMode.HEAT)

    # number.set_value called with 65.0
    mock_hass.services.async_call.assert_any_call(
        "number",
        "set_value",
        {"entity_id": "number.underfloor_valve_1", "value": 65.0},
        context=sm.internal_context,
    )

    # valve.set_valve_position called with position 65
    mock_hass.services.async_call.assert_any_call(
        "valve",
        "set_valve_position",
        {"entity_id": "valve.smart_valve_1", "position": 65},
        context=sm.internal_context,
    )


@pytest.mark.asyncio
async def test_proportional_valve_volt_scale(mock_hass, mock_coordinator):
    """Test proportional valve with 0-10V scale (65% -> 6.5V)."""
    sm = ZoneSyncManager(
        hass=mock_hass,
        coordinator=mock_coordinator,
        zone_name="Living Room",
        entity_id="climate.living_room",
        climates=[],
        switches=[],
        calibrations={},
        valves=["number.dac_output_0_10v"],
        valve_scale=VALVE_SCALE_VOLT,
    )

    await sm.async_sync_proportional_valves(HVACMode.HEAT)

    mock_hass.services.async_call.assert_called_with(
        "number",
        "set_value",
        {"entity_id": "number.dac_output_0_10v", "value": 6.5},
        context=sm.internal_context,
    )


@pytest.mark.asyncio
async def test_proportional_valve_off_and_bypass(mock_hass, mock_coordinator):
    """Test proportional valve forced to 0% / 0V when OFF or in bypass mode."""
    sm = ZoneSyncManager(
        hass=mock_hass,
        coordinator=mock_coordinator,
        zone_name="Living Room",
        entity_id="climate.living_room",
        climates=[],
        switches=[],
        calibrations={},
        valves=["number.dac_output_0_10v"],
        valve_scale=VALVE_SCALE_VOLT,
    )

    # When HVACMode is OFF
    await sm.async_sync_proportional_valves(HVACMode.OFF)
    mock_hass.services.async_call.assert_called_with(
        "number",
        "set_value",
        {"entity_id": "number.dac_output_0_10v", "value": 0.0},
        context=sm.internal_context,
    )

    mock_hass.services.async_call.reset_mock()

    # When zone is bypassed
    mock_coordinator.get_zone_mode.return_value = "bypass"
    await sm.async_sync_proportional_valves(HVACMode.HEAT)
    mock_hass.services.async_call.assert_called_with(
        "number",
        "set_value",
        {"entity_id": "number.dac_output_0_10v", "value": 0.0},
        context=sm.internal_context,
    )


@pytest.mark.asyncio
async def test_proportional_valve_deadband(mock_hass, mock_coordinator):
    """Test deadband skips minor jitters."""
    sm = ZoneSyncManager(
        hass=mock_hass,
        coordinator=mock_coordinator,
        zone_name="Living Room",
        entity_id="climate.living_room",
        climates=[],
        switches=[],
        calibrations={},
        valves=["number.dac_output_0_10v"],
        valve_scale=VALVE_SCALE_VOLT,
    )

    # First call sets to 6.5V
    await sm.async_sync_proportional_valves(HVACMode.HEAT)
    assert mock_hass.services.async_call.call_count == 1

    # Second call with tiny change (65.2% -> 6.5V) should not trigger call
    mock_coordinator.get_zone_demand.return_value = 65.2
    await sm.async_sync_proportional_valves(HVACMode.HEAT)
    assert mock_hass.services.async_call.call_count == 1
