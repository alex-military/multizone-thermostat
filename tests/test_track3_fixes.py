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

    # Once dedicated HP min cycle values are set, changing boiler min cycle must NOT overwrite HP
    hp.set_min_cycle_on.reset_mock()
    hp.set_min_cycle_off.reset_mock()
    coord.set_min_cycle_on(3.0)
    coord.set_min_cycle_off(2.0)
    assert coord.min_cycle_on == 3.0
    assert coord.min_cycle_off == 2.0
    boiler.set_min_cycle_on.assert_called_with(3)
    boiler.set_min_cycle_off.assert_called_with(2)
    hp.set_min_cycle_on.assert_not_called()
    hp.set_min_cycle_off.assert_not_called()


def test_hp_cooling_candidate_no_substring_collision():
    """Verify _is_zone_cooling_candidate uses exact zone id matching, not substring matching."""
    from custom_components.multizone_thermostat.boiler.heat_pump_backend import CentralHeatPumpBackend

    coord = MagicMock()
    coord.get_zone_mode.return_value = "primary"
    coord.resolve_zone_id.side_effect = lambda x: x
    coord._climate_entities = {
        "climate.multizone_thermostat_bagno_2": SimpleNamespace(hvac_mode="off"),
        "climate.multizone_thermostat_bagno": SimpleNamespace(hvac_mode="cool"),
    }
    coord.split_manager = None

    hp = CentralHeatPumpBackend.__new__(CentralHeatPumpBackend)
    hp.coordinator = coord

    assert hp._is_zone_cooling_candidate({"name": "Bagno"}) is True
    assert hp._is_zone_cooling_candidate({"name": "Bagno 2"}) is False


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


# ==============================================================================
# 5. Beta.9 Regression Tests (6 Logic Bugs)
# ==============================================================================

@pytest.mark.asyncio
async def test_anti_seize_turn_boiler_on_off_uses_backends_not_orchestrator():
    """Bug 1: AntiSeizeManager must call boiler/hp backends, never non-existent orchestrator.async_update."""
    from custom_components.multizone_thermostat.safety.anti_seize import AntiSeizeManager

    hass = MagicMock()
    coord = MagicMock()
    coord.enable_gas_heater = True
    coord.enable_heat_pump = True
    coord.plant_orchestrator = PlantOrchestrator(hass, MagicMock(), MagicMock(), coord)
    coord.boiler_backend = MagicMock()
    coord.boiler_backend.async_update = AsyncMock()
    coord.boiler_backend.async_emergency_off = AsyncMock()
    coord.boiler_backend.status_reason = "OFF - No Demand"
    coord.boiler_backend._status_reason = "OFF - No Demand"
    coord.heat_pump_backend = MagicMock()
    coord.heat_pump_backend.async_update = AsyncMock()
    coord.heat_pump_backend.async_emergency_off = AsyncMock()

    mgr = AntiSeizeManager(hass, coord)
    await mgr._turn_boiler_on()
    coord.boiler_backend.async_update.assert_awaited_once_with(100.0, "Anti-Seize", False)

    await mgr._turn_boiler_off()
    coord.boiler_backend.async_update.assert_awaited_with(0.0, None, False)
    coord.heat_pump_backend.async_emergency_off.assert_awaited_once()


@pytest.mark.asyncio
async def test_options_flow_preserves_grid_export_inverted():
    """Bug 2: OptionsFlow must load, expose in schema, and save CONF_GRID_EXPORT_INVERTED."""
    from custom_components.multizone_thermostat.config_flow.options_flow import MultizoneOptionsFlow
    from custom_components.multizone_thermostat.const import CONF_GRID_EXPORT_INVERTED, CONF_ENERGY_MANAGEMENT_ENABLED

    entry = SimpleNamespace(
        entry_id="e1",
        data={
            CONF_ENERGY_MANAGEMENT_ENABLED: True,
            CONF_GRID_EXPORT_INVERTED: True,
            "zones": [{"name": "Living"}],
        },
        options={},
    )
    flow = MultizoneOptionsFlow()
    flow.hass = MagicMock()
    flow.hass.config_entries = MagicMock()
    flow.config_entry = entry

    await flow.async_step_init(None)
    assert flow._grid_export_inverted is True

    await flow.async_step_edit_energy_management(
        {
            CONF_ENERGY_MANAGEMENT_ENABLED: True,
            CONF_GRID_EXPORT_INVERTED: True,
        }
    )
    saved_data = flow.hass.config_entries.async_update_entry.call_args.kwargs["data"]
    assert saved_data[CONF_GRID_EXPORT_INVERTED] is True


@pytest.mark.asyncio
async def test_plant_orchestrator_max_zone_delta_ignores_off_and_bypass_zones():
    """Bug 3: max_zone_delta for COMBINED boost must exclude OFF and BYPASS zones."""
    from custom_components.multizone_thermostat.const import ZONE_MODE_BYPASS, ZONE_MODE_PRIMARY

    hass = MagicMock()
    hass.states = MagicMock()
    hass.states.get.return_value = None

    demand_agg = MagicMock()
    demand_agg._zone_demands = {"climate.active": 30.0, "climate.off_zone": 0.0, "climate.bypass_zone": 0.0}
    demand_agg.calculate.return_value = SimpleNamespace(demand=30.0, peak_zone="climate.active")

    boiler = MagicMock()
    boiler.async_update = AsyncMock()
    hp = MagicMock()
    hp.hp_entity = None
    hp.async_update = AsyncMock()

    coord = MagicMock()
    coord.get_master_state.return_value = True
    coord.master_hvac_mode = HVAC_MODE_HEAT
    coord.enable_gas_heater = True
    coord.enable_heat_pump = True
    coord.is_dhw_active = False
    coord.zones = []
    coord.zone_controller = None
    coord.frost_manager = None
    coord.plant_diagnostics = None
    coord.energy_manager = SimpleNamespace(
        get_heat_source_priority=lambda: "combined",
        is_solar_surplus=lambda: False,
    )
    coord.get_zone_mode.side_effect = lambda cid: ZONE_MODE_BYPASS if cid == "climate.bypass_zone" else ZONE_MODE_PRIMARY
    coord._climate_entities = {
        "climate.active": SimpleNamespace(hvac_mode="heat", current_temperature=19.8, target_temperature=20.0),
        "climate.off_zone": SimpleNamespace(hvac_mode="off", current_temperature=14.0, target_temperature=21.0),
        "climate.bypass_zone": SimpleNamespace(hvac_mode="heat", current_temperature=15.0, target_temperature=22.0),
    }

    orch = PlantOrchestrator(hass, demand_agg, boiler, coord, heat_pump_backend=hp)
    await orch._async_update_boiler()

    # Only climate.active (delta 0.2°C) should be considered, NOT 7.0°C from off/bypass zones
    assert orch.last_plant_command is not None
    assert orch.last_plant_command.reason == "COMBINED_BASE"
    assert orch.last_plant_command.hp_demand == 0.0


def test_frost_l5_supports_numeric_sensor_entity():
    """Bug 4: Frost L5 outdoor fallback must read numeric state from sensor.* entities."""
    from custom_components.multizone_thermostat.safety.frost import FrostManager
    from custom_components.multizone_thermostat.const import KEY_ANTI_FROST_ENABLED

    hass = MagicMock()
    sensor_state = SimpleNamespace(state="0.5", domain="sensor", attributes={})
    hass.states.get.side_effect = lambda eid: sensor_state if eid == "sensor.outdoor_temp" else None

    coord = MagicMock()
    coord.weather_sensor_id = "sensor.outdoor_temp"
    coord.plant_diagnostics.has_critical_sensor_fault.return_value = True
    coord.zone_manager.get_zone.return_value = None
    coord.get_persistent_data.side_effect = lambda k, d=None: True if k == KEY_ANTI_FROST_ENABLED else d

    fm = FrostManager(hass, coord)
    assert fm.is_zone_in_frost_emergency("climate.multizone_thermostat_living") is True


def test_split_sensor_injection_proportional_when_ceiling_not_stratified():
    """Bug 5: When ceiling probe <= room sensor, push must scale proportionally instead of flat +1.5°C."""
    from custom_components.multizone_thermostat.split.split_controller import SplitZoneManager

    hass = MagicMock()
    hass.states.get.return_value = SimpleNamespace(attributes={"current_temperature": 19.8})
    coord = MagicMock()
    coord.zones = [{"name": "Salotto", "split_climate_entity": "climate.split_salotto", "split_sensor_injection": True}]

    mgr = SplitZoneManager(hass, coord)
    # 0.2°C deficit with aligned ceiling probe -> 20.0 + 0.2 = 20.2°C (not 21.5°C)
    injected = mgr.calculate_injected_target("climate.multizone_thermostat_salotto", 19.8, 20.0)
    assert injected == 20.2


@pytest.mark.asyncio
async def test_smart_return_completion_skips_non_cooling_zones_in_cool_mode():
    """Bug 6: Smart Return completion in COOL mode must not wake zones that cannot cool."""
    from custom_components.multizone_thermostat.schedule.manager import ScheduleProfileManager

    hass = MagicMock()
    coord = MagicMock()
    coord.hass = hass
    coord.master_hvac_mode = "cool"
    coord.zones = [{"name": "Radiatori"}, {"name": "SplitRoom"}]
    coord.can_zone_cool.side_effect = lambda cid: cid == "climate.multizone_thermostat_splitroom"
    coord.get_zone_mode.return_value = "primary"
    coord.get_master_state.return_value = True

    mgr = ScheduleProfileManager(coord)
    mgr.scheduler_enabled = False
    mgr.smart_return = {"arrival_time": "2026-01-01T10:00:00+00:00", "preset": "comfort", "zones": None}
    mgr._async_wake_zone = AsyncMock()
    mgr.async_save_to_storage = AsyncMock()
    mgr.coordinator.zone_manager = MagicMock()
    mgr.coordinator.zone_manager.async_set_global_preset = AsyncMock()

    from datetime import datetime, timezone
    await mgr.async_evaluate_schedule(now=datetime(2026, 1, 1, 10, 5, tzinfo=timezone.utc))

    mgr._async_wake_zone.assert_awaited_once_with("climate.multizone_thermostat_splitroom")


# ==============================================================================
# 6. Second-Pass Audit Regression Tests (Bugs 7–11)
# ==============================================================================

@pytest.mark.asyncio
async def test_plant_orchestrator_updates_last_aggregate_in_cooling_mode():
    """Bug 7: Master Demand Sensor depends on last_aggregate being updated during HVAC_MODE_COOL."""
    hass = MagicMock()
    hass.states = MagicMock()
    hass.states.get.return_value = None

    demand_agg = MagicMock()
    demand_agg._zone_demands = {"climate.salotto": 75.0}

    boiler = MagicMock()
    boiler.async_update = AsyncMock()
    hp = MagicMock()
    hp.async_update = AsyncMock()

    coord = MagicMock()
    coord.get_master_state.return_value = True
    coord.master_hvac_mode = HVAC_MODE_COOL
    coord.enable_heat_pump = True
    coord.heat_pump_cooling = True
    coord.zones = []
    coord.zone_controller = None
    coord.frost_manager = None
    coord.plant_diagnostics = None
    coord.energy_manager = None
    coord.split_manager = None
    coord.get_zone_mode.return_value = "primary"
    coord._climate_entities = {
        "climate.salotto": SimpleNamespace(hvac_mode=HVAC_MODE_COOL, current_temperature=26.5, target_temperature=24.0)
    }
    demand_agg.get_zone_demand.return_value = 75.0

    orch = PlantOrchestrator(hass, demand_agg, boiler, coord, heat_pump_backend=hp)
    await orch._async_update_boiler()

    assert orch.last_aggregate is not None
    assert orch.last_aggregate.demand == 75.0
    assert orch.last_aggregate.peak_zone == "climate.salotto"
    assert orch.last_aggregate.strategy == "cooling"


def test_diagnostics_cycles_and_runtime_support_heat_pump_only_plants():
    """Bug 8: Heat-pump-only plants must report non-zero cycles/h and runtime without generator_id."""
    from custom_components.multizone_thermostat.plant_diagnostics.engine import PlantDiagnosticsEngine

    coord = MagicMock()
    coord.zones = []
    coord.enable_gas_heater = False
    coord.enable_heat_pump = True

    diag = PlantDiagnosticsEngine(coord)
    diag.record_generator_state("heat_pump", True)
    assert diag.get_boiler_cycles_per_hour() == 1
    assert diag.get_boiler_daily_runtime_hours() >= 0.0
    diag.record_generator_state("heat_pump", False)
    assert diag.get_boiler_cycles_per_hour() == 1


@pytest.mark.asyncio
async def test_persistent_number_syncs_hp_cycle_on_startup():
    """Bug 9: MultizonePersistentNumber syncs persisted HP min cycle ON/OFF to coordinator on boot."""
    from custom_components.multizone_thermostat.number import MultizonePersistentNumber
    from custom_components.multizone_thermostat.const import KEY_HP_MIN_CYCLE_ON, KEY_HP_MIN_CYCLE_OFF

    coord = MagicMock()
    coord.get_persistent_data.side_effect = lambda k, d=None: 14.0 if k == KEY_HP_MIN_CYCLE_ON else (9.0 if k == KEY_HP_MIN_CYCLE_OFF else d)
    coord.set_hp_min_cycle_on = MagicMock()
    coord.set_hp_min_cycle_off = MagicMock()

    dev_info = MagicMock()
    num_on = MultizonePersistentNumber(coord, "e1", KEY_HP_MIN_CYCLE_ON, "HP On", 0, 30, 1, "min", "mdi:timer", 5, dev_info)
    num_on.hass = MagicMock()
    await num_on.async_added_to_hass()
    coord.set_hp_min_cycle_on.assert_called_once_with(14.0)

    num_off = MultizonePersistentNumber(coord, "e1", KEY_HP_MIN_CYCLE_OFF, "HP Off", 0, 30, 1, "min", "mdi:timer", 5, dev_info)
    num_off.hass = MagicMock()
    await num_off.async_added_to_hass()
    coord.set_hp_min_cycle_off.assert_called_once_with(9.0)


def test_window_open_clears_split_manual_and_zeroes_demand():
    """Bug 10: Opening a window zeroes demand, clears local split manual override, and turns off zone if no select."""
    from custom_components.multizone_thermostat.zone_manager import ZoneManager

    hass = MagicMock()
    hass.async_create_task = MagicMock(side_effect=lambda coro: coro.close() if hasattr(coro, "close") else None)
    coord = MagicMock()
    coord.zones = [{"name": "Salotto", "window_sensor": "binary_sensor.win_salotto"}]
    coord._select_entities = {}
    coord._climate_entities = {}
    coord._climate_callbacks = {}
    coord._settings = {}
    coord.is_zone_in_frost_emergency.return_value = False
    coord.demand_aggregator = MagicMock()
    coord.split_manager = MagicMock()
    coord._async_set_hvac_mode = AsyncMock()
    coord.async_save_storage = AsyncMock()
    coord.async_set_persistent_data = AsyncMock()

    zm = ZoneManager(hass, coord)
    event = SimpleNamespace(data={"entity_id": "binary_sensor.win_salotto", "new_state": SimpleNamespace(state="on")})
    zm.async_on_window_state_changed(event)

    coord.demand_aggregator.set_zone_demand.assert_called_with("climate.multizone_thermostat_salotto", 0.0)
    coord.split_manager.set_local_manual_on.assert_called_with("climate.multizone_thermostat_salotto", False)


@pytest.mark.asyncio
async def test_master_controller_apply_master_off_guards_missing_boiler_backend():
    """Bug 11: MasterController.async_apply_master_off handles missing plant_orchestrator/boiler_backend safely."""
    from custom_components.multizone_thermostat.master_controller import MasterController

    coord = MagicMock()
    coord.hass = MagicMock()
    coord.hass.states = MagicMock()
    coord.hass.states.get.return_value = None
    coord.zones = []
    coord.plant_orchestrator = None
    coord.boiler_backend = None
    coord.heat_pump_backend = None

    mc = MasterController(coord)
    await mc.async_apply_master_off()
