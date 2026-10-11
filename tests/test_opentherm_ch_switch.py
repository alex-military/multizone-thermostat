"""OpenTherm: true OFF via optional CH-enable switch and 'number' fallback (roadmap 1.3)."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.multizone_thermostat.boiler.opentherm_backend import OpenThermBoilerBackend


def _hass(states: dict):
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.states.get = MagicMock(side_effect=lambda eid: states.get(eid))
    return hass


def _calls(hass):
    return [c.args for c in hass.services.async_call.call_args_list]


@pytest.mark.asyncio
async def test_ch_switch_turned_off_at_zero_demand_and_setpoint_kept():
    hass = _hass({
        "number.ot_setpoint": MagicMock(state="50", attributes={"min": 0}),
        "switch.ch": MagicMock(state="on"),
    })
    b = OpenThermBoilerBackend(hass, MagicMock(), "number.ot_setpoint", 35.0, 75.0, "switch.ch")
    await b.async_update(0.0, None, False)
    calls = _calls(hass)
    assert ("switch", "turn_off", {"entity_id": "switch.ch"}) in calls
    # flow setpoint is NOT forced to the entity minimum when a CH switch exists
    assert ("number", "set_value", {"entity_id": "number.ot_setpoint", "value": 35.0}) in calls
    assert not any(c[2].get("value") == 0.0 for c in calls if c[1] == "set_value")
    assert "CH switch off" in b.status_reason


@pytest.mark.asyncio
async def test_ch_switch_turned_on_with_demand():
    hass = _hass({
        "number.ot_setpoint": MagicMock(state="35", attributes={"min": 0}),
        "switch.ch": MagicMock(state="off"),
    })
    b = OpenThermBoilerBackend(hass, MagicMock(), "number.ot_setpoint", 35.0, 75.0, "switch.ch")
    await b.async_update(50.0, "Z", False)
    assert ("switch", "turn_on", {"entity_id": "switch.ch"}) in _calls(hass)


@pytest.mark.asyncio
async def test_ch_switch_not_called_when_already_in_state():
    hass = _hass({
        "number.ot_setpoint": MagicMock(state="35", attributes={}),
        "switch.ch": MagicMock(state="off"),
    })
    b = OpenThermBoilerBackend(hass, MagicMock(), "number.ot_setpoint", 35.0, 75.0, "switch.ch")
    await b.async_update(0.0, None, False)
    assert not any(c[0] == "switch" for c in _calls(hass))


@pytest.mark.asyncio
async def test_ch_switch_also_drives_climate_entity():
    hass = _hass({
        "climate.ot": MagicMock(state="heat", attributes={"temperature": 35.0}),
        "switch.ch": MagicMock(state="on"),
    })
    b = OpenThermBoilerBackend(hass, MagicMock(), "climate.ot", 35.0, 75.0, "switch.ch")
    await b.async_update(0.0, None, False)
    calls = _calls(hass)
    assert ("climate", "set_hvac_mode", {"entity_id": "climate.ot", "hvac_mode": "off"}) in calls
    assert ("switch", "turn_off", {"entity_id": "switch.ch"}) in calls


@pytest.mark.asyncio
@pytest.mark.parametrize("attrs", [{}, {"min": "abc"}, {"min": None}])
async def test_number_without_switch_missing_or_invalid_min_writes_zero(attrs):
    hass = _hass({"number.ot_setpoint": MagicMock(state="50", attributes=attrs)})
    b = OpenThermBoilerBackend(hass, MagicMock(), "number.ot_setpoint", 35.0, 75.0)
    await b.async_update(0.0, None, False)
    hass.services.async_call.assert_called_once_with(
        "number", "set_value", {"entity_id": "number.ot_setpoint", "value": 0.0}, blocking=False
    )
