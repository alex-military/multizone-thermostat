import sys
from unittest.mock import MagicMock
import importlib.abc
import importlib.machinery

# A custom finder to mock ANY homeassistant.* module


import pytest
import asyncio
import time
from unittest.mock import AsyncMock

from custom_components.multizone_thermostat.boiler.relay_backend import RelayBoilerBackend
from custom_components.multizone_thermostat.boiler.opentherm_backend import OpenThermBoilerBackend

@pytest.mark.asyncio
async def test_relay_backend_pwm():
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.states.get = MagicMock(return_value=MagicMock(state="off"))
    
    coordinator = MagicMock()
    coordinator.zones = []
    coordinator.record_diagnostic_event = MagicMock()
    coordinator.plant_diagnostics = MagicMock()
    coordinator.plant_diagnostics._current_boiler_start = None
    
    backend = RelayBoilerBackend(hass, coordinator, "switch.boiler", 0.0, 0.0, 0.0)
    
    await backend.async_update(50.0, "Zone1", False)
    
    hass.services.async_call.assert_called_once_with(
        "switch", "turn_on", {"entity_id": "switch.boiler"}, blocking=False
    )
    
    await backend.async_emergency_off()
    hass.services.async_call.assert_called_with(
        "switch", "turn_off", {"entity_id": "switch.boiler"}, blocking=False
    )

@pytest.mark.asyncio
async def test_relay_backend_min_cycle_off():
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.states.get = MagicMock(return_value=MagicMock(state="off"))
    
    coordinator = MagicMock()
    coordinator.zones = []
    
    backend = RelayBoilerBackend(hass, coordinator, "switch.boiler", 0.0, 5.0, 0.0)
    backend._last_boiler_change = time.monotonic()
    
    await backend.async_update(50.0, "Zone1", False)
    
    hass.services.async_call.assert_not_called()
    assert "HOLD_OFF" in backend.status_reason

@pytest.mark.asyncio
async def test_opentherm_backend():
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.states.get = MagicMock()
    
    coordinator = MagicMock()
    
    backend = OpenThermBoilerBackend(hass, coordinator, "climate.opentherm", 35.0, 75.0)
    
    await backend.async_update(50.0, "Zone1", False)
    
    hass.services.async_call.assert_any_call(
        "climate", "set_temperature", {"entity_id": "climate.opentherm", "temperature": 55.0}, blocking=False
    )


