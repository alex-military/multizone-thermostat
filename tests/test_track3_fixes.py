"""Unit tests for Track 3 beta.6 fixes.

Tests:
1. Coordinator: set_hp_min_cycle_on/off, set_valve_delay, set_min_cycle_on/off delegation, and error handling in async_notify_pid_entities.
2. PlantOrchestrator: avoidance of redundant proactive zone PID evaluation.
3. ListenerManager: plant_orchestrator async refresh handling without _mock_children.
4. __init__.py: _extract_entity_ids, Voluptuous schemas, service calls with entity lists, NaN/inf rejection.
"""
from __future__ import annotations

import math
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import voluptuous as vol

from custom_components.multizone_thermostat import (
    _extract_entity_ids,
    SERVICE_SET_PID_SCHEMA,
    SERVICE_RESET_AUTOTUNE_SCHEMA,
    _async_register_services,
)
from custom_components.multizone_thermostat.const import DOMAIN, HVAC_MODE_HEAT, HVAC_MODE_COOL
from custom_components.multizone_thermostat.coordinator import MultizoneCoordinator
from custom_components.multizone_thermostat.boiler.plant_orchestrator import PlantOrchestrator
from custom_components.multizone_thermostat.listener_manager import ListenerManager


# ==============================================================================
# 1. Coordinator Tests
# ==============================================================================

def test_coordinator_min_cycle_and_valve_delay_delegation():
    """Verify coordinator delegates min cycle and valve delay to both backends cleanly."""
    cfg = SimpleNamespace(
        enable_gas_heater=True,
        enable_heat_pump=True,
        boiler_mode="relay",
        boiler_switch="switch.boiler",
        opentherm_entity=None,
        heat_pump_entity="climate.hp",
        heat_pump_min_temp=25.0,
        heat_pump_max_temp=55.0,
        heat_pump_ch_switch=None,
        heat_pump_cooling=True,
        master_hvac_mode=HVAC_MODE_HEAT,
        energy_management_enabled=False,
        solar_power_sensor=None,
        grid_export_sensor=None,
        battery_soc_sensor=None,
        external_solar_override_entity=None,
        solar_export_threshold=0.0,
        battery_min_reserve_soc=20.0,
        min_cycle_on=5.0,
        min_cycle_off=5.0,
        valve_delay=30.0,
    )

    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {}
    entry.options = {}

    coord = MultizoneCoordinator.__new__(MultizoneCoordinator)
    coord.hass = hass
    coord.entry = entry
    coord._min_cycle_on = cfg.min_cycle_on
    coord._min_cycle_off = cfg.min_cycle_off
    coord._hp_min_cycle_on = cfg.min_cycle_on
    coord._hp_min_cycle_off = cfg.min_cycle_off
    coord._valve_delay = cfg.valve_delay

    boiler = MagicMock()
    hp = MagicMock()
    coord.boiler_backend = boiler
    coord.heat_pump_backend = hp

    # Test set_min_cycle_on
    coord.set_min_cycle_on(10.0)
    assert coord.min_cycle_on == 10.0
    boiler.set_min_cycle_on.assert_called_with(10)
    hp.set_min_cycle_on.assert_called_with(10.0)

    # Test set_min_cycle_off
    coord.set_min_cycle_off(8.0)
    assert coord.min_cycle_off == 8.0
    boiler.set_min_cycle_off.assert_called_with(8)
    hp.set_min_cycle_off.assert_called_with(8.0)

    # Test set_valve_delay
    coord.set_valve_delay(45.0)
    assert coord.valve_delay == 45.0
    boiler.set_valve_delay.assert_called_with(45)
    hp.set_valve_delay.assert_called_with(45)

    # Test set_hp_min_cycle_on / off
    coord.set_hp_min_cycle_on(12.0)
    assert coord.hp_min_cycle_on == 12.0
    hp.set_min_cycle_on.assert_called_with(12.0)

    coord.set_hp_min_cycle_off(7.0)
    assert coord.hp_min_cycle_off == 7.0
    hp.set_min_cycle_off.assert_called_with(7.0)


def test_coordinator_notify_pid_entities_exception_handling():
    """Verify exceptions in PID and climate callbacks are logged at debug level and do not abort."""
    coord = MultizoneCoordinator.__new__(MultizoneCoordinator)
    coord._pid_listeners = []
    coord._climate_callbacks = {}

    calls = []

    def failing_cb():
        calls.append("failing")
        raise RuntimeError("callback explosion")

    def succeeding_cb():
        calls.append("succeeding")

    coord._pid_listeners.append(failing_cb)
    coord._pid_listeners.append(succeeding_cb)
    coord._climate_callbacks["c1"] = failing_cb
    coord._climate_callbacks["c2"] = succeeding_cb

    with patch("custom_components.multizone_thermostat.coordinator._LOGGER.debug") as mock_debug:
        coord.async_notify_pid_entities()
        assert calls == ["failing", "succeeding", "failing", "succeeding"]
        assert mock_debug.call_count == 2


# ==============================================================================
# 2. PlantOrchestrator Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_plant_orchestrator_skips_already_evaluated_zones():
    """Verify proactive zone refresh skips zones that already have active demand or an evaluated PID."""
    hass = MagicMock()
    demand_agg = MagicMock()
    demand_agg._zone_demands = {
        "zone.active_demand": 50.0,
        "zone.pid_evaluated": 0.0,
        "zone.uninitialized": 0.0,
    }
    demand_agg.set_zone_demand = MagicMock()

    coord = MagicMock()
    coord.resolve_zone_id = lambda cid: cid
    coord._climate_entities = {
        "zone.active_demand": MagicMock(entity_id="zone.active_demand"),
        "zone.pid_evaluated": MagicMock(entity_id="zone.pid_evaluated"),
        "zone.uninitialized": MagicMock(entity_id="zone.uninitialized"),
    }
    coord.zones = []

    pid_evaluated = MagicMock()
    pid_evaluated._last_input_time = 12345.67

    pid_uninitialized = MagicMock()
    pid_uninitialized._last_input_time = None

    def _get_pid(cid, mode="heat"):
        if cid == "zone.pid_evaluated":
            return pid_evaluated
        if cid == "zone.uninitialized":
            return pid_uninitialized
        return None

    zone_ctrl = MagicMock()
    zone_ctrl.get_pid = MagicMock(side_effect=_get_pid)
    zone_ctrl.async_update_zone = AsyncMock(return_value=100.0)
    coord.zone_controller = zone_ctrl

    orch = PlantOrchestrator(hass, demand_agg, MagicMock(), coord)

    # Proactive refresh with force=False: should only update zone.uninitialized
    await orch._async_refresh_zones_proactively(force=False)

    assert zone_ctrl.async_update_zone.call_count == 1
    zone_ctrl.async_update_zone.assert_called_once()
    assert zone_ctrl.async_update_zone.call_args[0][0] == "zone.uninitialized"
    demand_agg.set_zone_demand.assert_called_once_with("zone.uninitialized", 100.0)

    # When force=True, all 3 zones must be updated
    zone_ctrl.async_update_zone.reset_mock()
    demand_agg.set_zone_demand.reset_mock()

    await orch._async_refresh_zones_proactively(force=True)
    assert zone_ctrl.async_update_zone.call_count == 3


# ==============================================================================
# 3. ListenerManager Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_listener_manager_orch_dispatch_without_mock_children():
    """Verify ListenerManager triggers async_refresh / _async_update_boiler cleanly on orchestrator."""
    coord = MagicMock()
    coord.zone_controller.async_update_zone = AsyncMock(return_value=30.0)
    coord.demand_aggregator.set_zone_demand = MagicMock()

    # Case A: plant_orchestrator has coroutine async_refresh
    orch_a = MagicMock()
    orch_a.async_refresh = AsyncMock()
    coord.plant_orchestrator = orch_a

    lm = ListenerManager(coord)
    event = MagicMock(data={"entity_id": "climate.test", "new_state": MagicMock()})
    await lm.async_on_climate_state_changed(event)
    orch_a.async_refresh.assert_awaited_once()

    # Case B: plant_orchestrator has coroutine _async_update_boiler (like test mock)
    orch_b = MagicMock()
    orch_b.async_refresh = MagicMock()  # ordinary unconfigured MagicMock (not coroutine)
    orch_b._async_update_boiler = AsyncMock()
    coord.plant_orchestrator = orch_b

    await lm.async_on_climate_state_changed(event)
    orch_b._async_update_boiler.assert_awaited_once()


# ==============================================================================
# 4. __init__.py Service Schemas & Helpers Tests
# ==============================================================================

def test_extract_entity_ids():
    """Test _extract_entity_ids helper with single, multiple, and invalid inputs."""
    # Single string
    assert _extract_entity_ids({"climate_entity": "climate.living"}) == ["climate.living"]
    assert _extract_entity_ids({"entity_id": "climate.bed"}) == ["climate.bed"]

    # Multiple strings (list, tuple, set)
    assert _extract_entity_ids({"climate_entity": ["climate.living", "climate.bed"]}) == [
        "climate.living",
        "climate.bed",
    ]
    assert _extract_entity_ids({"entity_id": ("climate.a", "climate.b")}) == [
        "climate.a",
        "climate.b",
    ]

    # Strips whitespace
    assert _extract_entity_ids({"climate_entity": "  climate.zone  "}) == ["climate.zone"]
    assert _extract_entity_ids({"entity_id": [" climate.a ", "  "]}) == ["climate.a"]

    # Missing keys
    with pytest.raises(vol.Invalid):
        _extract_entity_ids({})

    # Empty string or empty list
    with pytest.raises(vol.Invalid):
        _extract_entity_ids({"climate_entity": ""})

    with pytest.raises(vol.Invalid):
        _extract_entity_ids({"entity_id": []})

    # Non-string / invalid type
    with pytest.raises(vol.Invalid):
        _extract_entity_ids({"climate_entity": 12345})


def test_service_schemas_validation():
    """Test Voluptuous schemas for set_pid_parameters and reset_autotune."""
    # Valid set_pid_parameters
    valid_data = {
        "climate_entity": "climate.living",
        "kp": 120.0,
        "ki": 0.05,
        "kd": 100.0,
        "lock_parameter": "Kp",
        "unlock": True,
        "mode": "heat",
    }
    validated = SERVICE_SET_PID_SCHEMA(valid_data)
    assert validated["kp"] == 120.0

    # NaN / inf rejection
    with pytest.raises(vol.Invalid):
        SERVICE_SET_PID_SCHEMA({"climate_entity": "climate.living", "kp": float("nan")})

    with pytest.raises(vol.Invalid):
        SERVICE_SET_PID_SCHEMA({"climate_entity": "climate.living", "kp": float("inf")})

    # Out of range values
    with pytest.raises(vol.Invalid):
        SERVICE_SET_PID_SCHEMA({"climate_entity": "climate.living", "kp": 0.05})  # min 0.1

    with pytest.raises(vol.Invalid):
        SERVICE_SET_PID_SCHEMA({"climate_entity": "climate.living", "ki": 15.0})  # max 10.0

    # Missing target entity
    with pytest.raises(vol.Invalid):
        SERVICE_SET_PID_SCHEMA({"kp": 100.0})

    # Valid reset_autotune
    valid_reset = {
        "entity_id": ["climate.living", "climate.bed"],
        "keep_manual_overrides": True,
        "mode": "cool",
    }
    validated_reset = SERVICE_RESET_AUTOTUNE_SCHEMA(valid_reset)
    assert validated_reset["keep_manual_overrides"] is True


@pytest.mark.asyncio
async def test_service_handlers_with_list_of_entities():
    """Verify handle_set_pid_parameters and handle_reset_autotune process lists of entity IDs."""
    hass = MagicMock()
    hass.data = {DOMAIN: {}}

    coord = MagicMock()
    coord.resolve_zone_id = lambda cid: cid
    coord.zones = [{"zone_name": "Living"}, {"zone_name": "Bed"}]
    coord.async_set_pid_manual_unlock = AsyncMock()
    coord.async_notify_pid_entities = MagicMock()
    coord.plant_orchestrator._async_update_boiler = AsyncMock()

    zc = MagicMock()
    zc.async_set_zone_pid = AsyncMock(return_value=True)
    zc.async_reset_zone_autotuner = AsyncMock(return_value=True)
    coord.zone_controller = zc

    hass.data[DOMAIN]["entry1"] = {"coordinator": coord}

    handlers = {}

    def fake_register(domain, service, handler, schema=None):
        handlers[service] = handler

    hass.services.async_register = fake_register

    await _async_register_services(hass)

    # 1. Test set_pid_parameters with list of entity IDs
    set_pid_fn = handlers["set_pid_parameters"]
    call_set = SimpleNamespace(
        data={
            "entity_id": ["climate.living", "climate.bed"],
            "kp": 150.0,
            "unlock": True,
        }
    )
    await set_pid_fn(call_set)

    assert zc.async_set_zone_pid.call_count == 2
    zc.async_set_zone_pid.assert_any_call("climate.living", kp=150.0, ki=None, kd=None, lock_param=None)
    zc.async_set_zone_pid.assert_any_call("climate.bed", kp=150.0, ki=None, kd=None, lock_param=None)
    assert coord.async_notify_pid_entities.call_count >= 1

    # 2. Test reset_autotune with list of entity IDs
    reset_fn = handlers["reset_autotune"]
    call_reset = SimpleNamespace(
        data={
            "climate_entity": ["climate.living", "climate.bed"],
            "keep_manual_overrides": False,
        }
    )
    await reset_fn(call_reset)

    assert zc.async_reset_zone_autotuner.call_count == 2
    zc.async_reset_zone_autotuner.assert_any_call("climate.living", keep_manual_overrides=False)
    zc.async_reset_zone_autotuner.assert_any_call("climate.bed", keep_manual_overrides=False)
