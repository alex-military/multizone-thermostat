"""Tests for Centralized / Condo Heating (Issue #11)."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from homeassistant.const import STATE_ON, STATE_OFF

from custom_components.multizone_thermostat.const import (
    DOMAIN,
    CONF_BOILER_MODE,
    CONF_BOILER_SWITCH,
    CONF_ZONES,
    CONF_ZONE_NAME,
    CONF_ZONE_CLIMATES,
    CONF_ZONE_SWITCHES,
    MODE_CENTRAL,
    MODE_RELAY,
    MODE_OPENTHERM,
)
from custom_components.multizone_thermostat.boiler.centralized_backend import CentralizedBoilerBackend
from custom_components.multizone_thermostat.config_flow import MultizoneConfigFlow, MultizoneOptionsFlow
from custom_components.multizone_thermostat.coordinator import MultizoneCoordinator


def _mock_hass():
    hass = MagicMock()
    hass.states = MagicMock()
    hass.states.get = MagicMock(return_value=None)
    hass.config_entries = MagicMock()
    hass.config_entries.async_update_entry = MagicMock()
    hass.config_entries.async_reload = AsyncMock()
    hass.async_create_task = MagicMock()
    return hass


@pytest.mark.asyncio
async def test_centralized_boiler_backend():
    """Verify CentralizedBoilerBackend lifecycle and demand tracking."""
    backend = CentralizedBoilerBackend()
    assert backend.status_reason == "CENTRALIZED - Idle"
    assert not backend.is_on

    # Demand active
    await backend.async_update(45.5, "Zone A", False)
    assert "Demand: 45.5%" in backend.status_reason
    assert backend.is_on

    # Demand satisfied (0%)
    await backend.async_update(0.0, None, False)
    assert backend.status_reason == "CENTRALIZED - Idle"
    assert not backend.is_on

    # Emergency off
    await backend.async_emergency_off()
    assert backend.status_reason == "CENTRALIZED - Off"
    assert not backend.is_on


@pytest.mark.asyncio
async def test_config_flow_centralized_mode():
    """Verify that selecting Centralized mode in config flow skips boiler switch step."""
    hass = _mock_hass()
    flow = MultizoneConfigFlow()
    flow.hass = hass

    # Step user with Centralized mode
    result = await flow.async_step_user({CONF_BOILER_MODE: MODE_CENTRAL})
    assert result["type"] == "form"
    assert result["step_id"] == "add_zone"
    assert flow._boiler_mode == MODE_CENTRAL
    assert flow._boiler_switch is None


@pytest.mark.asyncio
async def test_options_flow_change_to_centralized():
    """Verify switching to centralized boiler mode in Options Flow."""
    hass = _mock_hass()
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {
        CONF_BOILER_MODE: MODE_RELAY,
        CONF_BOILER_SWITCH: "switch.old_boiler",
        CONF_ZONES: [],
    }
    entry.options = {}

    flow = MultizoneOptionsFlow()
    flow.hass = hass
    flow.config_entry = entry
    flow._zones = []
    flow._boiler_mode = MODE_RELAY
    flow._boiler_switch = "switch.old_boiler"

    # User changes boiler mode to Centralized
    result = await flow.async_step_change_boiler({CONF_BOILER_MODE: MODE_CENTRAL})
    assert result["type"] == "create_entry"
    assert flow._boiler_mode == MODE_CENTRAL
    assert flow._boiler_switch == ""

    # Verify updated entry data passed to async_update_entry
    calls = hass.config_entries.async_update_entry.call_args_list
    assert len(calls) > 0
    saved_data = calls[-1][1]["data"]
    assert saved_data[CONF_BOILER_MODE] == MODE_CENTRAL
    assert CONF_BOILER_SWITCH not in saved_data


@pytest.mark.asyncio
async def test_coordinator_centralized_initialization():
    """Verify MultizoneCoordinator boots properly in Centralized mode without boiler switch."""
    hass = _mock_hass()
    entry = MagicMock()
    entry.entry_id = "test_central_entry"
    entry.data = {
        CONF_BOILER_MODE: MODE_CENTRAL,
        CONF_ZONES: [
            {
                CONF_ZONE_NAME: "Living Room",
                CONF_ZONE_CLIMATES: ["climate.trv_living"],
                CONF_ZONE_SWITCHES: ["switch.valve_living"],
            }
        ],
    }
    entry.options = {}

    coord = MultizoneCoordinator(hass, entry)
    assert coord.boiler_mode == MODE_CENTRAL
    assert coord.boiler_switch is None
    assert isinstance(coord.boiler_backend, CentralizedBoilerBackend)
    assert coord.boiler_status_reason == "CENTRALIZED - Idle"
