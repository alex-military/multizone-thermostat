"""Tests for Dual-Track PID & Autotuning and Hydronic/Split Cooling Architecture."""
from __future__ import annotations

import time
import pytest
from unittest.mock import MagicMock, AsyncMock

from homeassistant.const import STATE_ON
from custom_components.multizone_thermostat.const import (
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    HVAC_MODE_OFF,
    SOURCE_PRIORITY_ELECTRIC_ONLY,
    SOURCE_PRIORITY_GAS_ONLY,
    make_zone_entity_id,
)
from custom_components.multizone_thermostat.autotune import PassiveAutotuneObserver
from custom_components.multizone_thermostat.pid_wrapper import MultizonePID
from custom_components.multizone_thermostat.zone_controller import ZoneController
from custom_components.multizone_thermostat.boiler.plant_orchestrator import PlantOrchestrator


def test_cooling_autotune_observer_cycle():
    """Verify PassiveAutotuneObserver computes positive gains from temperature drop cycles."""
    observer = PassiveAutotuneObserver("climate.salotto", required_cycles=2, mode="cool")
    assert observer.mode == "cool"
    assert observer.state == observer.STATE_IDLE

    # Cycle 1: Start cooling at t=1000, temp=26.0°C
    observer.update(current_temp=26.0, is_active=True, now=1000.0)
    assert observer.state == observer.STATE_HEATING  # ACTIVE state
    assert observer.cycle_start_temp == 26.0

    # Temperature drops over 5 minutes (300s) to 24.5°C
    observer.update(current_temp=25.5, is_active=True, now=1120.0)
    observer.update(current_temp=25.0, is_active=True, now=1200.0)
    observer.update(current_temp=24.5, is_active=True, now=1300.0)

    # Stop cooling at t=1400, temp=24.2°C
    observer.update(current_temp=24.2, is_active=False, now=1400.0)
    assert observer.state == observer.STATE_COOLING
    assert len(observer.completed_cycles) == 1
    cycle1 = observer.completed_cycles[0]
    assert cycle1["slope"] > 0.0
    assert cycle1["L"] >= 60.0
    assert cycle1["Kp"] > 0.0
    assert cycle1["Ki"] > 0.0

    # Cycle 2: Start cooling again at t=2000, temp=25.5°C
    observer.update(current_temp=25.5, is_active=True, now=2000.0)
    observer.update(current_temp=25.0, is_active=True, now=2120.0)
    observer.update(current_temp=24.6, is_active=True, now=2200.0)
    observer.update(current_temp=24.2, is_active=True, now=2300.0)
    observer.update(current_temp=24.0, is_active=False, now=2400.0)

    # Should reach completed after required_cycles=2
    assert observer.state == observer.STATE_COMPLETED
    assert observer.kp > 0.0
    assert observer.ki > 0.0
    assert observer.kd > 0.0

    # Test dump and load state
    dumped = observer.dump_state()
    assert dumped["mode"] == "cool"
    assert len(dumped["completed_cycles"]) == 2

    new_observer = PassiveAutotuneObserver("climate.salotto", required_cycles=2, mode="cool")
    new_observer.load_state(dumped)
    assert new_observer.state == new_observer.STATE_COMPLETED
    assert new_observer.kp == observer.kp


def test_cooling_pid_wrapper():
    """Verify MultizonePID in cool mode produces positive demand for hot room and responds to drop."""
    pid_cool = MultizonePID(kp=20.0, ki=0.5, kd=5.0, out_min=0.0, out_max=100.0, zone_id="salotto", action="cool")

    # Room is 25.0°C, setpoint is 22.0°C (hot room: error = +3.0)
    demand1 = pid_cool.calc(current_temp=25.0, target_temp=22.0)
    assert demand1 > 0.0
    assert demand1 <= 100.0

    # Room is 20.0°C, setpoint is 22.0°C (cold room: error = -2.0)
    # Output should be 0.0%
    demand2 = pid_cool.calc(current_temp=20.0, target_temp=22.0)
    assert demand2 == 0.0


@pytest.mark.asyncio
async def test_zone_controller_dual_track_pid_and_autotune():
    """Verify ZoneController manages independent heat and cool PIDs and autotuners."""
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.zones = [{"name": "Salotto", "temp_sensor": "sensor.salotto_temp"}]
    coordinator.get_master_state.return_value = True
    coordinator.get_zone_mode.return_value = "primary"
    coordinator.enable_gas_heater = True
    coordinator.enable_heat_pump = True
    coordinator.heat_pump_cooling = True
    coordinator.weather_sensor_id = None
    coordinator.is_dhw_active = False
    coordinator.split_manager = None
    coordinator.plant_diagnostics.has_critical_sensor_fault.return_value = False

    demand_dict = {}
    coordinator.demand_aggregator.set_zone_demand.side_effect = lambda cid, dem: demand_dict.update({cid: dem})
    coordinator.demand_aggregator.get_zone_demand.side_effect = lambda cid: demand_dict.get(cid, 0.0)

    zc = ZoneController(hass, coordinator)
    cid = make_zone_entity_id("Salotto")

    assert cid in zc.pids
    assert cid in zc.pids_cool
    assert cid in zc.autotuners
    assert cid in zc.autotuners_cool

    # 1. State update in COOL mode: room is 26°C, target is 23°C
    mock_cool_state = MagicMock()
    mock_cool_state.state = HVAC_MODE_COOL
    mock_cool_state.attributes = {"current_temperature": 26.0, "temperature": 23.0}

    demand_cool = await zc.async_update_zone(cid, mock_cool_state)
    assert demand_cool > 0.0
    assert demand_dict[cid] == demand_cool

    # 2. State update in HEAT mode: room is 26°C, target is 20°C (warm room, no heating)
    mock_heat_state = MagicMock()
    mock_heat_state.state = HVAC_MODE_HEAT
    mock_heat_state.attributes = {"current_temperature": 26.0, "temperature": 20.0}

    demand_heat = await zc.async_update_zone(cid, mock_heat_state)
    assert demand_heat == 0.0
    assert demand_dict[cid] == 0.0


@pytest.mark.asyncio
async def test_zone_controller_seasonal_storage_load_save():
    """Verify loading seasonal heat and cool autotuner profiles."""
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.zones = [{"name": "Camera"}]
    zc = ZoneController(hass, coordinator)
    cid = make_zone_entity_id("Camera")

    seasonal_storage = {
        "heat": {
            cid: {
                "completed_cycles": [
                    {"Kp": 80.0, "Ki": 0.04, "Kd": 15.0, "L": 120.0, "slope": 0.01, "timestamp": time.time()}
                    for _ in range(3)
                ],
                "mode": "heat",
            }
        },
        "cool": {
            cid: {
                "completed_cycles": [
                    {"Kp": 140.0, "Ki": 0.02, "Kd": 30.0, "L": 240.0, "slope": 0.005, "timestamp": time.time()}
                    for _ in range(3)
                ],
                "mode": "cool",
            }
        },
    }

    zc.load_state(seasonal_storage, {})

    # Heat track should have Kp=80.0
    assert zc.get_autotuner(cid, "heat").state == "completed"
    assert zc.get_pid(cid, "heat")._pid._Kp == 80.0

    # Cool track should have Kp=140.0
    assert zc.get_autotuner(cid, "cool").state == "completed"
    assert zc.get_pid(cid, "cool")._pid._Kp == 140.0


@pytest.mark.asyncio
async def test_plant_orchestrator_single_heat_pump_full_electric():
    """Verify single heat pump scenario (enable_gas_heater=False, enable_heat_pump=True)."""
    hass = MagicMock()
    demand_aggregator = MagicMock()
    boiler_backend = AsyncMock()
    hp_backend = AsyncMock()
    coordinator = MagicMock()

    coordinator.get_master_state.return_value = True
    coordinator.enable_gas_heater = False  # Full Electric
    coordinator.enable_heat_pump = True
    coordinator.heat_pump_cooling = True
    coordinator.is_dhw_active = False
    coordinator.frost_manager = None
    coordinator._climate_callbacks = {}
    coordinator.plant_diagnostics = None
    coordinator.energy_manager.get_heat_source_priority.return_value = SOURCE_PRIORITY_ELECTRIC_ONLY
    coordinator.energy_manager.is_solar_surplus.return_value = False

    # Simulate 65% aggregated heating demand
    agg_result = MagicMock()
    agg_result.demand = 65.0
    agg_result.peak_zone = "climate.salotto"
    demand_aggregator.calculate.return_value = agg_result

    orch = PlantOrchestrator(hass, demand_aggregator, boiler_backend, coordinator, hp_backend)

    # 1. Heating tick
    coordinator.master_hvac_mode = HVAC_MODE_HEAT
    await orch._async_update_boiler()

    # Gas boiler must be 0.0% demand because gas is disabled
    boiler_backend.async_update.assert_called_with(0.0, "climate.salotto", False)
    # Heat Pump must receive 65.0% heating demand
    hp_backend.async_update.assert_called_with(65.0, "climate.salotto", False, hvac_mode=HVAC_MODE_HEAT)

    # 2. Cooling tick
    coordinator.master_hvac_mode = HVAC_MODE_COOL
    # Simulate zone cooling demand in demand_aggregator
    demand_aggregator.get_zone_demand.return_value = 55.0
    mock_ent = MagicMock()
    mock_ent.hvac_mode = HVAC_MODE_COOL
    coordinator._climate_entities = {"climate.salotto": mock_ent}

    await orch._async_update_boiler()
    # Gas boiler strictly 0.0 in cooling
    boiler_backend.async_update.assert_called_with(0.0, None, False)
    # Heat Pump receives 55.0% cooling demand
    hp_backend.async_update.assert_called_with(55.0, "climate.salotto", False, hvac_mode=HVAC_MODE_COOL)
