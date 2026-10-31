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
    coordinator.reset_last_active_time.assert_called()

    await backend.async_update(0.0, None, False)
    assert backend.status_reason == "OFF - No Demand"

    await backend.async_emergency_off()
    assert backend.status_reason == "OFF - Emergency/Master OFF"


@pytest.mark.asyncio
async def test_plant_orchestrator_calls_frost_manager():
    from custom_components.multizone_thermostat.boiler.plant_orchestrator import PlantOrchestrator

    hass = MagicMock()
    demand_aggregator = MagicMock()
    demand_aggregator.calculate.return_value = MagicMock(demand=100.0, peak_zone="Frost Emergency")
    boiler_backend = MagicMock()
    boiler_backend.async_update = AsyncMock()
    boiler_backend.async_emergency_off = AsyncMock()

    coordinator = MagicMock()
    coordinator.get_master_state.return_value = False
    coordinator.is_dhw_active = False
    coordinator.frost_manager = MagicMock()
    coordinator.frost_manager.async_handle_frost_emergencies = AsyncMock(return_value=True)

    orch = PlantOrchestrator(hass, demand_aggregator, boiler_backend, coordinator)
    await orch._async_update_boiler()

    coordinator.frost_manager.async_handle_frost_emergencies.assert_awaited_once()
    boiler_backend.async_emergency_off.assert_not_called()
    boiler_backend.async_update.assert_awaited_once_with(100.0, "Frost Emergency", True)


def test_pid_preserves_integral_on_minor_inertia_setpoint_shift():
    from custom_components.multizone_thermostat.pid import PID

    pid = PID(kp=20.0, ki=0.1, kd=0.0, out_min=0.0, out_max=100.0)
    # Initial sample
    pid.calc(input_val=19.0, set_point=20.0, input_time=100.0, last_input_time=None)
    # Second sample after 60s builds integral
    pid.calc(input_val=19.0, set_point=20.0, input_time=160.0, last_input_time=100.0)
    assert pid.integral > 0.0
    prev_integral = pid.integral

    # Minor thermal-inertia effective_target shift (e.g. 20.0 -> 19.95) must NOT wipe integral
    pid.calc(input_val=19.0, set_point=19.95, input_time=220.0, last_input_time=160.0)
    assert pid.integral > prev_integral

    # Large setpoint change (>= 1.5°C) resets integral
    pid.calc(input_val=19.0, set_point=17.0, input_time=280.0, last_input_time=220.0)
    assert pid.integral == 0.0


def test_autotune_clamps_kp_before_ki_kd():
    from custom_components.multizone_thermostat.autotune import PassiveAutotuneObserver

    obs = PassiveAutotuneObserver("climate.z1", required_cycles=1)
    obs.cycle_start_time = 0.0
    obs.cycle_start_temp = 18.0
    # 5 points with a gentle slope that produces raw Kp > 500 if unclamped
    obs.history.extend([
        (0.0, 18.0),
        (50.0, 18.0),
        (100.0, 18.0),
        (250.0, 18.03),
        (400.0, 18.06),  # slope = 0.06 / 300 = 0.0002 °C/s -> raw Kp = 120 / (0.0002 * 100) = 6000 -> clamped to 500
    ])
    obs._stop_heating(400.0, 18.06)
    assert len(obs.completed_cycles) == 1
    cycle = obs.completed_cycles[0]
    assert cycle["Kp"] == 500.0
    # Verify Ki = Kp / (2 * L) and Kd = Kp * (0.5 * L) use clamped Kp=500.0
    L = cycle["L"]
    assert abs(cycle["Ki"] - (500.0 / (2.0 * L))) < 1e-6
    assert abs(cycle["Kd"] - (500.0 * 0.5 * L)) < 1e-6


@pytest.mark.asyncio
async def test_relay_backend_skips_when_unavailable_fix_a():
    """Fix A: Verify relay backend does not call HA services if boiler switch is unavailable/unknown."""
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    coordinator = MagicMock()
    coordinator.zones = []

    backend = RelayBoilerBackend(hass, coordinator, "switch.boiler", 0.0, 0.0, 0.0)

    # 1. State is None (missing at boot)
    hass.states.get = MagicMock(return_value=None)
    await backend._force_boiler_on()
    await backend._force_boiler_off()
    await backend.async_emergency_off()
    hass.services.async_call.assert_not_called()

    # 2. State is "unavailable" (Z2M still starting)
    hass.states.get = MagicMock(return_value=MagicMock(state="unavailable"))
    await backend._force_boiler_on()
    await backend._force_boiler_off()
    await backend.async_emergency_off()
    hass.services.async_call.assert_not_called()

    # 3. State is "unknown"
    hass.states.get = MagicMock(return_value=MagicMock(state="unknown"))
    await backend._force_boiler_on()
    await backend._force_boiler_off()
    await backend.async_emergency_off()
    hass.services.async_call.assert_not_called()


@pytest.mark.asyncio
async def test_relay_backend_avoids_redundant_off_fix_b():
    """Fix B: Verify emergency off and force_off skip turn_off when already OFF."""
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    coordinator = MagicMock()
    coordinator.zones = []
    coordinator.record_diagnostic_event = MagicMock()

    backend = RelayBoilerBackend(hass, coordinator, "switch.boiler", 0.0, 0.0, 0.0)

    # Boiler is already OFF in HA state machine
    hass.states.get = MagicMock(return_value=MagicMock(state="off"))

    # Calling emergency_off multiple times (simulating 10s tick loop)
    await backend.async_emergency_off()
    await backend.async_emergency_off()
    await backend.async_emergency_off()

    # No service calls and no diagnostic noise
    hass.services.async_call.assert_not_called()
    coordinator.record_diagnostic_event.assert_not_called()

    # Now boiler is ON
    hass.states.get = MagicMock(return_value=MagicMock(state="on"))
    await backend.async_emergency_off()

    # Service called ONCE
    hass.services.async_call.assert_called_once_with(
        "switch", "turn_off", {"entity_id": "switch.boiler"}, blocking=False
    )
    coordinator.record_diagnostic_event.assert_called_once_with(
        "BOILER_SWITCH_OFF", {"switch": "switch.boiler", "reason": backend.status_reason}
    )


@pytest.mark.asyncio
async def test_opentherm_backend_skips_when_unavailable_fix_a():
    """Fix A: Verify OpenTherm backend skips when entity is unavailable."""
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    coordinator = MagicMock()

    backend = OpenThermBoilerBackend(hass, coordinator, "climate.opentherm", 35.0, 75.0, ch_switch="switch.ch")

    # State is unavailable
    hass.states.get = MagicMock(return_value=MagicMock(state="unavailable"))
    await backend.async_update(50.0, "Zone1", False)
    await backend.async_emergency_off()
    hass.services.async_call.assert_not_called()




