"""Unit tests validating all Track 1 backend fixes."""
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

from homeassistant.components.climate import HVACMode, HVACAction
from homeassistant.core import Event, Context, State
from homeassistant.const import ATTR_TEMPERATURE

from custom_components.multizone_thermostat.sync_manager import ZoneSyncManager
from custom_components.multizone_thermostat.thermal_model import ThermalObserver
from custom_components.multizone_thermostat.zone_controller import ZoneController
from custom_components.multizone_thermostat.coordinator import MultizoneCoordinator
from custom_components.multizone_thermostat.climate import MultizoneVirtualThermostat
from custom_components.multizone_thermostat.split.split_controller import SplitZoneManager
from custom_components.multizone_thermostat.zone_manager import ZoneManager
from custom_components.multizone_thermostat.safety.watchdog import SensorWatchdog
from custom_components.multizone_thermostat.safety.frost import FrostManager
from custom_components.multizone_thermostat.safety.anti_seize import AntiSeizeManager
from custom_components.multizone_thermostat.boiler.heat_pump_backend import CentralHeatPumpBackend
from custom_components.multizone_thermostat.boiler.plant_orchestrator import PlantOrchestrator
from custom_components.multizone_thermostat.pid import PIDAutotune
from custom_components.multizone_thermostat.const import (
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    HVAC_MODE_OFF,
    CONF_ZONE_NAME,
    CONF_ZONE_SPLIT_CLIMATE,
    CONF_ZONE_SPLIT_ROLE,
    SPLIT_ROLE_COOLING_ONLY,
    make_zone_entity_id,
)


@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.states.get.return_value = None
    hass.services.async_call = AsyncMock()
    def _create_task(coro):
        if asyncio.iscoroutine(coro):
            try:
                loop = asyncio.get_running_loop()
                return loop.create_task(coro)
            except RuntimeError:
                coro.close()
                return MagicMock()
        return MagicMock()
    hass.async_create_task = MagicMock(side_effect=_create_task)
    return hass


# -----------------------------------------------------------------------------
# 1. sync_manager.py
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_sync_manager_trv_lock_unified(mock_hass):
    coord = MagicMock()
    mgr = ZoneSyncManager(mock_hass, coord, "Living", "climate.living", ["climate.trv1"], [], {})
    assert mgr._trv_event_lock is mgr._sync_lock


@pytest.mark.asyncio
async def test_sync_manager_cool_forces_trv_off(mock_hass):
    coord = MagicMock()
    mgr = ZoneSyncManager(mock_hass, coord, "Living", "climate.living", ["climate.trv1"], [], {})
    st = MagicMock()
    st.state = "heat"
    st.attributes = {"hvac_modes": [HVACMode.HEAT, HVACMode.OFF]}
    mock_hass.states.get.return_value = st

    await mgr.async_sync_trvs(HVACMode.COOL, 24.0, 25.0, False, True)

    mock_hass.services.async_call.assert_called_with(
        "climate",
        "set_hvac_mode",
        {"entity_id": "climate.trv1", "hvac_mode": HVACMode.OFF},
        blocking=True,
        context=mgr.internal_context,
    )


@pytest.mark.asyncio
async def test_sync_manager_calib_offset_clamped(mock_hass):
    coord = MagicMock()
    mgr = ZoneSyncManager(mock_hass, coord, "Living", "climate.living", ["climate.trv1"], [], {})
    st = MagicMock()
    st.state = "heat"
    st.attributes = {"current_temperature": 29.0, "target_temp_step": 0.5, ATTR_TEMPERATURE: 20.0}
    mock_hass.states.get.return_value = st

    # master target = 20.0, master current = 20.0, trv current = 29.0
    # raw offset = 29.0 - 20.0 = +9.0, clamped to +3.0 -> trv_target = 23.0
    await mgr.async_sync_trvs(HVACMode.HEAT, 20.0, 20.0, False, True)

    calls = [c for c in mock_hass.services.async_call.call_args_list if c[0][1] == "set_temperature"]
    assert len(calls) == 1
    assert calls[0][0][2]["temperature"] == 23.0


@pytest.mark.asyncio
async def test_sync_manager_process_trv_tolerance(mock_hass):
    coord = MagicMock()
    mgr = ZoneSyncManager(mock_hass, coord, "Living", "climate.living", ["climate.trv1"], [], {})
    mgr._pending_trv_targets["climate.trv1"] = 21.2

    event = Event("state_changed", {
        "entity_id": "climate.trv1",
        "new_state": State("climate.trv1", "heat", {ATTR_TEMPERATURE: 21.0}),
        "old_state": State("climate.trv1", "heat", {ATTR_TEMPERATURE: 20.0}),
    })
    mode, delta = await mgr.process_trv_change(event, "external_ctx", HVACMode.HEAT, 15.0, 25.0)

    # 21.0 vs 21.2 has difference 0.2 <= 0.55 -> confirmed pending target, no knob delta!
    assert mode is None
    assert delta is None
    assert "climate.trv1" not in mgr._pending_trv_targets


@pytest.mark.asyncio
async def test_sync_manager_pwm_and_valves_cooling_hydronic_guard(mock_hass):
    coord = MagicMock()
    coord.get_master_state.return_value = True
    coord.enable_heat_pump = False
    coord.heat_pump_cooling = False
    coord.get_zone_demand.return_value = 80.0

    mgr = ZoneSyncManager(mock_hass, coord, "Living", "climate.living", [], ["switch.s1"], {}, valves=["valve.v1"])
    mgr._local_pwm_state = True
    mock_hass.states.get.return_value = State("valve.v1", "50")

    # In COOL mode without heat pump cooling allowed:
    changed = await mgr.async_pwm_tick(HVACMode.COOL)
    assert changed is True
    assert mgr.local_pwm_state is False

    await mgr.async_sync_proportional_valves(HVACMode.COOL)
    assert mgr._last_valve_positions.get("valve.v1") == 0.0


# -----------------------------------------------------------------------------
# 2. zone_controller.py & thermal_model.py
# -----------------------------------------------------------------------------
def test_thermal_model_ignores_cooling_mode():
    obs = ThermalObserver("living")
    obs.update(24.0, True, hvac_mode="cool")
    obs.update(26.0, False, hvac_mode="cool")
    assert obs.heating_rate == 0.0
    assert obs.thermal_inertia == 0.0


# -----------------------------------------------------------------------------
# 3. climate.py hvac_action cooling guard & split recursion guard
# -----------------------------------------------------------------------------
def test_climate_cooling_idle_when_master_off(mock_hass):
    coord = MagicMock()
    coord.get_master_state.return_value = False
    coord.can_zone_cool.return_value = True

    climate = MultizoneVirtualThermostat(mock_hass, "entry", {CONF_ZONE_NAME: "Living"})
    climate._coordinator = coord
    climate._hvac_mode = HVACMode.COOL
    climate._current_temperature = 28.0
    climate._target_temperature = 22.0

    assert climate.hvac_action == HVACAction.IDLE


def test_split_controller_ignores_self_as_split(mock_hass):
    coord = MagicMock()
    cid = make_zone_entity_id("Living")
    coord.zones = [{
        CONF_ZONE_NAME: "Living",
        CONF_ZONE_SPLIT_CLIMATE: cid,  # Misconfigured: points to itself
    }]
    split_mgr = SplitZoneManager(mock_hass, coord)
    assert not split_mgr.has_split(cid)


# -----------------------------------------------------------------------------
# 4. zone_manager.py async_set_global_preset
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_zone_manager_preset_does_not_pollute_manual_override(mock_hass):
    coord = MagicMock()
    coord.zones = [{CONF_ZONE_NAME: "Living"}]
    coord.schedule_manager = MagicMock()
    coord.schedule_manager.scheduler_enabled = True
    coord.schedule_manager.manual_overrides = {}

    zm = ZoneManager(mock_hass, coord)
    cid = make_zone_entity_id("Living")
    zm._presets_heat = {"eco": {cid: {"target_temp": 18.0}}}

    await zm.async_set_global_preset("eco")
    coord.schedule_manager.record_manual_override.assert_not_called()


# -----------------------------------------------------------------------------
# 5. safety/watchdog.py, safety/frost.py, safety/anti_seize.py
# -----------------------------------------------------------------------------
def test_watchdog_none_last_update():
    wd = SensorWatchdog()
    assert wd.is_sensor_stale(None, 60.0) is True


@pytest.mark.asyncio
async def test_frost_manager_switches_cooling_to_heat(mock_hass):
    coord = MagicMock()
    cid = make_zone_entity_id("Living")
    coord.zones = [{CONF_ZONE_NAME: "Living"}]
    coord.get_persistent_data.side_effect = lambda k, d=None: 5.0 if "temp" in k else True
    coord._async_set_hvac_mode = AsyncMock()

    fm = FrostManager(mock_hass, coord)
    fm.is_zone_in_frost_emergency = MagicMock(return_value=True)

    st = State(cid, "cool", {ATTR_TEMPERATURE: 24.0})
    mock_hass.states.get.return_value = st

    triggered = await fm.async_handle_frost_emergencies()
    assert triggered is True
    coord._async_set_hvac_mode.assert_called_with(cid, HVAC_MODE_HEAT)


@pytest.mark.asyncio
async def test_anti_seize_skips_cooling_only_split(mock_hass):
    coord = MagicMock()
    cid = make_zone_entity_id("AC_Zone")
    coord.zones = [{
        CONF_ZONE_NAME: "AC_Zone",
        CONF_ZONE_SPLIT_ROLE: SPLIT_ROLE_COOLING_ONLY,
    }]
    coord._async_set_hvac_mode = AsyncMock()
    mock_hass.states.get.return_value = State(cid, "off")

    asm = AntiSeizeManager(mock_hass, coord)
    await asm.async_execute()

    coord._async_set_hvac_mode.assert_not_called()


# -----------------------------------------------------------------------------
# 6. boiler/heat_pump_backend.py & plant_orchestrator.py
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_heat_pump_cooling_calculation_and_number_min(mock_hass):
    coord = MagicMock()
    hp = CentralHeatPumpBackend(
        mock_hass, coord, "number", "number.hp_temp",
        min_temp=25.0, max_temp=55.0,
        cool_min_temp=7.0, cool_max_temp=18.0, valve_delay=15,
    )
    assert hp.valve_delay == 15

    # 1. Cooling 50% demand: 18 - 0.5*(18 - 7) = 12.5°C
    st_num = State("number.hp_temp", "18.0", {"min": 5.0, "max": 60.0})
    mock_hass.states.get.return_value = st_num
    await hp.async_update(50.0, "Living", False, hvac_mode="cool")

    mock_hass.services.async_call.assert_called_with(
        "number", "set_value", {"entity_id": "number.hp_temp", "value": 12.5}, blocking=False
    )

    # 2. Shutdown (0% demand): number entity min=5.0 is respected instead of 0.0
    await hp.async_update(0.0, None, False, hvac_mode="cool")
    mock_hass.services.async_call.assert_called_with(
        "number", "set_value", {"entity_id": "number.hp_temp", "value": 5.0}, blocking=False
    )


@pytest.mark.asyncio
async def test_plant_orchestrator_hp_only_auto_mode(mock_hass):
    coord = MagicMock()
    coord.get_master_state.return_value = True
    coord.master_hvac_mode = "heat"
    coord.enable_gas_heater = False
    coord.enable_heat_pump = True
    coord.energy_manager = None

    boiler = MagicMock()
    boiler.async_update = AsyncMock()
    hp = MagicMock()
    hp.async_update = AsyncMock()

    dem_agg = MagicMock()
    agg_res = MagicMock()
    agg_res.demand = 75.0
    agg_res.peak_zone = "Living"
    dem_agg.calculate.return_value = agg_res

    orch = PlantOrchestrator(mock_hass, dem_agg, boiler, coord, heat_pump_backend=hp)
    await orch._async_update_boiler()

    boiler.async_update.assert_called_with(0.0, "Living", False)
    hp.async_update.assert_called_with(75.0, "Living", False, hvac_mode="heat")


# -----------------------------------------------------------------------------
# 7. pid.py ZeroDivisionError prevention
# -----------------------------------------------------------------------------
def test_pid_zero_division_guard():
    tuner = PIDAutotune(out_step=10, lookback=60)
    tuner._inputs = MagicMock()
    tuner._inputs.maxlen = 10
    tuner._sample_time_calc = [1.0, 1.0, 1.0]  # len <= 5
    tuner._last_sample_time = 100.0

    res = tuner.run(19.0, 20.0, now=101.0)
    assert res is False


# -----------------------------------------------------------------------------
# 8. Additional Track 1 Robustness & Edge-Cases
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_sync_manager_cool_blocks_heat_and_turns_trv_off(mock_hass):
    coord = MagicMock()
    mgr = ZoneSyncManager(mock_hass, coord, "Living", "climate.living", ["climate.trv1"], [], {})
    mgr._authoritative_sync = True

    event = Event("state_changed", {
        "entity_id": "climate.trv1",
        "new_state": State("climate.trv1", "heat", {ATTR_TEMPERATURE: 22.0}),
        "old_state": State("climate.trv1", "off", {ATTR_TEMPERATURE: 20.0}),
    })
    mode, delta = await mgr.process_trv_change(event, "ext_ctx", HVACMode.COOL, 15.0, 25.0)

    assert mode is None
    assert delta is None
    mock_hass.services.async_call.assert_called_with(
        "climate",
        "set_hvac_mode",
        {"entity_id": "climate.trv1", "hvac_mode": HVACMode.OFF},
        context=mgr.internal_context,
    )


@pytest.mark.asyncio
async def test_sync_manager_pwm_tick_bypass(mock_hass):
    coord = MagicMock()
    coord.get_master_state.return_value = True
    coord.get_zone_mode.return_value = "bypass"
    coord.enable_heat_pump = False
    coord.heat_pump_cooling = False
    coord.get_zone_demand.return_value = 80.0

    mgr = ZoneSyncManager(mock_hass, coord, "Living", "climate.living", [], ["switch.s1"], {})
    mgr._local_pwm_state = True

    changed = await mgr.async_pwm_tick(HVACMode.HEAT)
    assert changed is True
    assert mgr.local_pwm_state is False


def test_split_controller_cooling_solar_surplus(mock_hass):
    coord = MagicMock()
    cid = make_zone_entity_id("Salotto")
    coord.zones = [{
        CONF_ZONE_NAME: "Salotto",
        CONF_ZONE_SPLIT_CLIMATE: "climate.split_salotto",
        CONF_ZONE_SPLIT_ROLE: "heat_cool",
    }]
    energy_mgr = MagicMock()
    energy_mgr.solar_overheat_offset = 2.0
    energy_mgr.solar_min_run_time = 0.0
    coord.energy_manager = energy_mgr

    mgr = SplitZoneManager(mock_hass, coord)

    # In cool mode: current=23.0, target=23.0. Without surplus, room demand is 0 -> split OFF
    mode, target, _ = mgr.evaluate_split_state(cid, 23.0, 23.0, HVAC_MODE_COOL, solar_surplus=False)
    assert mode == HVAC_MODE_OFF

    # With solar surplus: effective_target = 23.0 - 2.0 = 21.0 -> split COOL
    mode, target, _ = mgr.evaluate_split_state(cid, 23.0, 23.0, HVAC_MODE_COOL, solar_surplus=True)
    assert mode == HVAC_MODE_COOL
    assert target == 21.0

    # With clamp minimum at 18.0°C
    mode, target, _ = mgr.evaluate_split_state(cid, 20.0, 19.0, HVAC_MODE_COOL, solar_surplus=True)
    assert mode == HVAC_MODE_COOL
    assert target == 18.0


@pytest.mark.asyncio
async def test_plant_orchestrator_cooling_solar_boost(mock_hass):
    coord = MagicMock()
    coord.get_master_state.return_value = True
    coord.master_hvac_mode = "cool"
    coord.enable_gas_heater = True
    coord.enable_heat_pump = True
    coord.heat_pump_cooling = True

    energy_mgr = MagicMock()
    energy_mgr.is_solar_surplus.return_value = True
    energy_mgr.is_external_override_active.return_value = False
    coord.energy_manager = energy_mgr

    boiler = MagicMock()
    boiler.async_update = AsyncMock()
    hp = MagicMock()
    hp.async_update = AsyncMock()

    dem_agg = MagicMock()
    orch = PlantOrchestrator(mock_hass, dem_agg, boiler, coord, heat_pump_backend=hp)
    orch._calculate_cooling_demand = MagicMock(return_value=(30.0, "Salotto"))

    await orch._async_update_boiler()

    boiler.async_update.assert_called_with(0.0, None, False)
    # Solar surplus boosts cooling demand to 100%
    hp.async_update.assert_called_with(100.0, "Salotto", False, hvac_mode="cool")


@pytest.mark.asyncio
async def test_heat_pump_backend_none_protection_and_input_number(mock_hass):
    coord = MagicMock()
    hp = CentralHeatPumpBackend(
        mock_hass, coord, "number", "input_number.target_flow",
        min_temp=None, max_temp=None, cool_min_temp=None, cool_max_temp=None
    )
    assert hp.min_temp == 25.0
    assert hp.max_temp == 55.0
    assert hp.cool_min_temp == 7.0
    assert hp.cool_max_temp == 18.0

    st = State("input_number.target_flow", "20.0")
    mock_hass.states.get.return_value = st

    await hp.async_update(50.0, "Living", False, hvac_mode="heat")
    # In heat mode at 50% demand: 25.0 + 0.5 * (55.0 - 25.0) = 40.0°C
    mock_hass.services.async_call.assert_called_with(
        "input_number", "set_value", {"entity_id": "input_number.target_flow", "value": 40.0}, blocking=False
    )


@pytest.mark.asyncio
async def test_heat_pump_backend_water_heater_power_off(mock_hass):
    coord = MagicMock()
    hp = CentralHeatPumpBackend(
        mock_hass, coord, "water_heater", "water_heater.pdc", min_temp=30.0
    )

    # 1. wanted_on == False with "off" in operation_list
    st1 = State("water_heater.pdc", "heat_pump", {"operation_list": ["heat_pump", "off"], "temperature": 45.0})
    mock_hass.states.get.return_value = st1
    await hp.async_update(0.0, None, False, hvac_mode="heat")
    mock_hass.services.async_call.assert_called_with(
        "water_heater", "set_operation_mode", {"entity_id": "water_heater.pdc", "operation_mode": "off"}, blocking=False
    )

    # 2. wanted_on == False without "off" in operation_list -> lowers setpoint to min_temp
    st2 = State("water_heater.pdc", "heat_pump", {"operation_list": ["heat_pump", "eco"], "min_temp": 28.0, "temperature": 45.0})
    mock_hass.states.get.return_value = st2
    await hp.async_update(0.0, None, False, hvac_mode="heat")
    mock_hass.services.async_call.assert_called_with(
        "water_heater", "set_temperature", {"entity_id": "water_heater.pdc", "temperature": 28.0}, blocking=False
    )


@pytest.mark.asyncio
async def test_coordinator_master_off_stops_heat_pump(mock_hass):
    coord = MagicMock()
    coord.zones = []
    coord.plant_orchestrator = MagicMock()
    coord.plant_orchestrator.boiler_backend.async_emergency_off = AsyncMock()
    coord.heat_pump_backend = MagicMock()
    coord.heat_pump_backend.async_emergency_off = AsyncMock()

    await MultizoneCoordinator.async_apply_master_off(coord)

    coord.plant_orchestrator.boiler_backend.async_emergency_off.assert_called_once()
    coord.heat_pump_backend.async_emergency_off.assert_called_once()


def test_coordinator_can_zone_cool_matrix(mock_hass):
    coord = MagicMock()
    coord.can_central_cool.return_value = True
    coord.split_manager = MagicMock()
    coord.split_manager.has_split.return_value = False

    cid_rad = make_zone_entity_id("Radiators")
    cid_floor = make_zone_entity_id("Floor")
    cid_fc = make_zone_entity_id("Fancoil")
    cid_explicit = make_zone_entity_id("ExplicitNoCool")

    coord.zones = [
        {
            CONF_ZONE_NAME: "Radiators",
            "climate_entities": ["climate.trv1"],
            "switch_entities": [],
            "valve_entities": [],
            "trv_preset_sync": True,
        },
        {
            CONF_ZONE_NAME: "Floor",
            "climate_entities": [],
            "switch_entities": ["switch.valve_floor"],
            "valve_entities": [],
        },
        {
            CONF_ZONE_NAME: "Fancoil",
            "climate_entities": ["climate.trv2"],
            "fancoil": True,
        },
        {
            CONF_ZONE_NAME: "ExplicitNoCool",
            "allow_cooling": False,
            "switch_entities": ["switch.valve_floor"],
        },
    ]

    # Radiator-only zone cannot cool centrally
    assert MultizoneCoordinator.can_zone_cool(coord, cid_rad) is False
    # Floor zone can cool centrally
    assert MultizoneCoordinator.can_zone_cool(coord, cid_floor) is True
    # Fancoil zone can cool centrally
    assert MultizoneCoordinator.can_zone_cool(coord, cid_fc) is True
    # Explicitly disabled cannot cool
    assert MultizoneCoordinator.can_zone_cool(coord, cid_explicit) is False


def test_climate_exposes_cooling_rate(mock_hass):
    coord = MagicMock()
    coord.get_master_state.return_value = True
    coord.can_zone_cool.return_value = False
    coord.get_zone_cooling_rate.return_value = 0.42
    coord.schedule_manager = None

    climate = MultizoneVirtualThermostat(mock_hass, "entry", {CONF_ZONE_NAME: "Living"})
    climate._coordinator = coord
    climate._current_temperature = 21.0
    climate._target_temperature = 20.0

    attrs = climate.extra_state_attributes
    assert attrs.get("cooling_rate") == 0.42


def test_plant_diagnostics_anomalies_ghost_heating_ignored_in_cool(mock_hass):
    from custom_components.multizone_thermostat.plant_diagnostics.anomalies import (
        evaluate_zone_anomalies,
        ANOMALY_GHOST_HEATING,
        ANOMALY_NONE,
    )
    coord = MagicMock()
    coord.get_zone_mode.return_value = "primary"
    coord.master_hvac_mode = "cool"
    coord.get_zone_demand.return_value = 0.0
    coord.zone_manager.get_zone.return_value = {}
    coord.zone_manager.is_passive_heat_allowed.return_value = False

    cid = "climate.living"
    state_dict = {}

    # 1st tick at 22.0°C
    st1 = State(cid, "cool", {"current_temperature": 22.0, "temperature": 24.0})
    mock_hass.states.get.return_value = st1
    anomaly, _ = evaluate_zone_anomalies(coord, mock_hass, cid, state_dict, True)
    assert anomaly != ANOMALY_GHOST_HEATING

    # 2nd tick at 24.5°C (> 0.8°C rise while boiler/hp is on with 0% demand)
    st2 = State(cid, "cool", {"current_temperature": 24.5, "temperature": 24.0})
    mock_hass.states.get.return_value = st2
    anomaly, _ = evaluate_zone_anomalies(coord, mock_hass, cid, state_dict, True)
    assert anomaly != ANOMALY_GHOST_HEATING
    assert anomaly == ANOMALY_NONE
