"""Tests for Normally Open / Normally Closed (NO/NC) actuator output inversion.

Validates GitHub Issue #17:
- Relays / Thermal Heads: invert_switch=True turns switch OFF on demand and ON when idle.
- Proportional Valves: invert_valve=True maps demand 0-100% to position 100-0%.
"""
from unittest.mock import AsyncMock, MagicMock
import pytest

from homeassistant.components.climate import HVACMode
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
)
from custom_components.multizone_thermostat.const import (
    CONF_ZONE_INVERT_SWITCH,
    CONF_ZONE_INVERT_VALVE,
    CONF_ZONE_NAME,
    CONF_ZONE_SWITCHES,
    CONF_ZONE_VALVES,
    VALVE_SCALE_PERCENT,
    VALVE_SCALE_VOLT,
)
from custom_components.multizone_thermostat.sync_manager import ZoneSyncManager


@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    # Mock states dict
    states_dict = {}
    hass.states.get = lambda eid: states_dict.get(eid)
    hass.states._states = states_dict
    return hass


@pytest.fixture
def mock_coordinator():
    coordinator = MagicMock()
    coordinator.get_zone_demand.return_value = 40.0
    coordinator.get_zone_mode.return_value = "primary"
    coordinator.get_master_state.return_value = True
    return coordinator


@pytest.mark.asyncio
async def test_relay_switch_normally_closed_default(mock_hass, mock_coordinator):
    """Standard NC actuator: ON during demand, OFF when idle."""
    sw_entity = "switch.zone_nc_valve"
    st = MagicMock()
    st.state = "off"
    mock_hass.states._states[sw_entity] = st

    sm = ZoneSyncManager(
        hass=mock_hass,
        coordinator=mock_coordinator,
        zone_name="Living Room",
        entity_id="climate.living_room",
        climates=[],
        switches=[sw_entity],
        calibrations={},
        invert_switch=False,
    )

    # 1. PWM turns active (demand ON)
    sm._local_pwm_state = True
    await sm.async_sync_switches()

    mock_hass.services.async_call.assert_called_with(
        "switch",
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: sw_entity},
        context=sm._internal_context,
    )

    # 2. PWM turns idle (demand OFF)
    st.state = STATE_ON
    mock_hass.services.async_call.reset_mock()
    sm._local_pwm_state = False
    await sm.async_sync_switches()

    mock_hass.services.async_call.assert_called_with(
        "switch",
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: sw_entity},
        context=sm._internal_context,
    )


@pytest.mark.asyncio
async def test_relay_switch_normally_open_inverted(mock_hass, mock_coordinator):
    """Normally Open (NO) actuator: OFF during demand, ON when idle."""
    sw_entity = "switch.zone_no_valve"
    st = MagicMock()
    st.state = STATE_ON
    mock_hass.states._states[sw_entity] = st

    sm = ZoneSyncManager(
        hass=mock_hass,
        coordinator=mock_coordinator,
        zone_name="Bedroom",
        entity_id="climate.bedroom",
        climates=[],
        switches=[sw_entity],
        calibrations={},
        invert_switch=True,
    )

    # 1. PWM turns active (demand ON) -> must turn OFF switch to open NO valve
    sm._local_pwm_state = True
    await sm.async_sync_switches()

    mock_hass.services.async_call.assert_called_with(
        "switch",
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: sw_entity},
        context=sm._internal_context,
    )

    # 2. PWM turns idle (demand OFF) -> must turn ON switch to close NO valve
    st.state = "off"
    mock_hass.services.async_call.reset_mock()
    sm._local_pwm_state = False
    await sm.async_sync_switches()

    mock_hass.services.async_call.assert_called_with(
        "switch",
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: sw_entity},
        context=sm._internal_context,
    )


@pytest.mark.asyncio
async def test_relay_switch_inverted_no_redundant_call(mock_hass, mock_coordinator):
    """Verify that when inverted switch is already in expected state, no call is sent."""
    sw_entity = "switch.zone_no_valve"
    st = MagicMock()
    st.state = "off"  # already off
    mock_hass.states._states[sw_entity] = st

    sm = ZoneSyncManager(
        hass=mock_hass,
        coordinator=mock_coordinator,
        zone_name="Bedroom",
        entity_id="climate.bedroom",
        climates=[],
        switches=[sw_entity],
        calibrations={},
        invert_switch=True,
    )

    # Demand is active -> expected switch state is "off", matches st.state
    sm._local_pwm_state = True
    await sm.async_sync_switches()
    mock_hass.services.async_call.assert_not_called()


@pytest.mark.asyncio
async def test_proportional_valve_normally_closed_default(mock_hass, mock_coordinator):
    """Standard proportional valve: demand 40% -> position 40%."""
    v_entity = "valve.prop_valve"
    st = MagicMock()
    st.state = "open"
    st.attributes = {"current_position": 0}
    mock_hass.states._states[v_entity] = st

    sm = ZoneSyncManager(
        hass=mock_hass,
        coordinator=mock_coordinator,
        zone_name="Salon",
        entity_id="climate.salon",
        climates=[],
        switches=[],
        calibrations={},
        valves=[v_entity],
        valve_scale=VALVE_SCALE_PERCENT,
        invert_valve=False,
    )

    await sm.async_sync_proportional_valves(HVACMode.HEAT)

    mock_hass.services.async_call.assert_called_with(
        "valve",
        "set_valve_position",
        {ATTR_ENTITY_ID: v_entity, "position": 40},
        context=sm._internal_context,
    )


@pytest.mark.asyncio
async def test_proportional_valve_normally_open_inverted(mock_hass, mock_coordinator):
    """Inverted proportional valve: demand 40% -> position 60% (100 - 40)."""
    v_entity = "valve.prop_valve_inverted"
    st = MagicMock()
    st.state = "open"
    st.attributes = {"current_position": 0}
    mock_hass.states._states[v_entity] = st

    sm = ZoneSyncManager(
        hass=mock_hass,
        coordinator=mock_coordinator,
        zone_name="Studio",
        entity_id="climate.studio",
        climates=[],
        switches=[],
        calibrations={},
        valves=[v_entity],
        valve_scale=VALVE_SCALE_PERCENT,
        invert_valve=True,
    )

    # Demand 40% -> inverted effective percentage = 60%
    await sm.async_sync_proportional_valves(HVACMode.HEAT)

    mock_hass.services.async_call.assert_called_with(
        "valve",
        "set_valve_position",
        {ATTR_ENTITY_ID: v_entity, "position": 60},
        context=sm._internal_context,
    )


@pytest.mark.asyncio
async def test_proportional_valve_inverted_volt_scale(mock_hass, mock_coordinator):
    """Inverted 0-10V valve: demand 30% -> position 7.0 V (10.0 - 3.0)."""
    v_entity = "number.voltage_valve"
    st = MagicMock()
    st.state = "0.0"
    mock_hass.states._states[v_entity] = st

    mock_coordinator.get_zone_demand.return_value = 30.0

    sm = ZoneSyncManager(
        hass=mock_hass,
        coordinator=mock_coordinator,
        zone_name="Studio",
        entity_id="climate.studio",
        climates=[],
        switches=[],
        calibrations={},
        valves=[v_entity],
        valve_scale=VALVE_SCALE_VOLT,
        invert_valve=True,
    )

    await sm.async_sync_proportional_valves(HVACMode.HEAT)

    mock_hass.services.async_call.assert_called_with(
        "number",
        "set_value",
        {ATTR_ENTITY_ID: v_entity, "value": 7.0},
        context=sm._internal_context,
    )
