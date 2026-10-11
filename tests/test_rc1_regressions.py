"""Regression tests for the RC1 consolidation fixes."""
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.multizone_thermostat.boiler.relay_backend import RelayBoilerBackend
from custom_components.multizone_thermostat.boiler.opentherm_backend import OpenThermBoilerBackend
from custom_components.multizone_thermostat.plant_diagnostics.engine import PlantDiagnosticsEngine
from custom_components.multizone_thermostat.plant_diagnostics.const import ANOMALY_SENSOR_TIMEOUT


def _relay(master=True, dhw=False):
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.states.get = MagicMock(return_value=MagicMock(state="off"))
    hass.async_create_task = lambda coro: asyncio.ensure_future(coro)
    coord = MagicMock()
    coord.zones = []
    coord.get_master_state.return_value = master
    coord.is_dhw_active = dhw
    coord.plant_diagnostics._current_boiler_start = None
    return hass, coord, RelayBoilerBackend(hass, coord, "switch.boiler", 0.0, 0.0, 0.05)


@pytest.mark.asyncio
async def test_valve_delay_ok_turns_on():
    hass, coord, b = _relay()
    await b.async_update(50.0, "Z", False)
    await asyncio.sleep(0.15)
    hass.services.async_call.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("master,dhw", [(False, False), (True, True)])
async def test_valve_delay_rechecks_conditions(master, dhw):
    hass, coord, b = _relay(master=master, dhw=dhw)
    await b.async_update(50.0, "Z", False)
    await asyncio.sleep(0.15)
    hass.services.async_call.assert_not_called()


@pytest.mark.asyncio
async def test_valve_delay_demand_dropped_does_not_ignite():
    hass, coord, b = _relay()
    await b.async_update(50.0, "Z", False)
    b._last_demand = 0.0  # demand vanished during the delay (task not cancelled yet)
    await asyncio.sleep(0.15)
    hass.services.async_call.assert_not_called()


@pytest.mark.asyncio
async def test_dhw_overrides_min_cycle_on():
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.states.get = MagicMock(return_value=MagicMock(state="on"))
    coord = MagicMock()
    coord.zones = []
    coord.is_dhw_active = True
    coord.plant_diagnostics._current_boiler_start = 1.0
    b = RelayBoilerBackend(hass, coord, "switch.boiler", 10.0, 0.0, 0.0)
    b._last_boiler_change = time.monotonic()
    await b.async_update(0.0, None, False)
    hass.services.async_call.assert_called_with(
        "switch", "turn_off", {"entity_id": "switch.boiler"}, blocking=False
    )


@pytest.mark.asyncio
async def test_opentherm_number_zero_demand_uses_entity_min():
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.states.get = MagicMock(return_value=MagicMock(state="50", attributes={"min": 0}))
    b = OpenThermBoilerBackend(hass, MagicMock(), "number.ot_setpoint", 35.0, 75.0)
    await b.async_update(0.0, None, False)
    hass.services.async_call.assert_called_once_with(
        "number", "set_value", {"entity_id": "number.ot_setpoint", "value": 0.0}, blocking=False
    )


def test_timeout_with_trv_fallback_is_not_critical():
    coord = MagicMock()
    coord.zones = [{"name": "Z"}]
    eng = PlantDiagnosticsEngine(coord)
    cid = "climate.multizone_z"
    state = eng._zone_anomaly_state.setdefault(cid, {})
    state["active_anomaly"] = ANOMALY_SENSOR_TIMEOUT
    state["fallback_ok"] = True
    assert eng.has_critical_sensor_fault(cid) is False
    state["fallback_ok"] = False
    assert eng.has_critical_sensor_fault(cid) is True
