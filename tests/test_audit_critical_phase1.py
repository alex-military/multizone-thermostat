"""Unit tests verifying the critical bugfixes identified in REVISIONE_CODICE_AGGIORNATO.md.

Covers:
1. L1 - Monotonic demand aggregation across primary zones in WEIGHTED_AVERAGE.
2. Preset safety hard clamping on emitter FlowCurve (t_max for underfloor cannot exceed 40°C even if backend specifies 75°C).
3. Indoor zone dew-point condensation calculation.
4. Heat pump valve-delay: avoiding premature _current_running_state = True and spurious HOLD_ON.
"""
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock
from homeassistant.core import State

from custom_components.multizone_thermostat.demand_aggregator import (
    DemandAggregator,
    DEMAND_STRATEGY_WEIGHTED_AVERAGE,
    ZONE_MODE_PRIMARY,
)
from custom_components.multizone_thermostat.boiler.flow_curve import (
    create_flow_curve_for_emitter,
    EMITTER_UNDERFLOOR,
    EMITTER_RADIATOR,
)
from custom_components.multizone_thermostat.boiler.heat_pump_backend import CentralHeatPumpBackend


def test_l1_monotonic_weighted_average():
    """Verify that adding demand in any zone strictly increases or maintains aggregated demand (L1)."""
    da = DemandAggregator(strategy=DEMAND_STRATEGY_WEIGHTED_AVERAGE)
    z_a = da.register_zone("Zone A", "climate.a", weight=1.0, mode=ZONE_MODE_PRIMARY)
    z_b = da.register_zone("Zone B", "climate.b", weight=1.0, mode=ZONE_MODE_PRIMARY)

    da.set_zone_demand(z_a, 100.0)
    da.set_zone_demand(z_b, 0.0)
    res_single = da.calculate()
    assert res_single.demand == 50.0  # 100 * 1.0 / (1.0 + 1.0)

    # When Zone B wakes up with tiny 1% demand, total demand must NOT drop to 70% or less!
    da.set_zone_demand(z_b, 1.0)
    res_both = da.calculate()
    assert res_both.demand == 50.5
    assert res_both.demand >= res_single.demand, "Monotonicity violated!"


def test_emitter_preset_hard_safety_ceiling():
    """Verify that underfloor flow curve never exceeds preset safety max (40°C) even with generic 35-75°C config."""
    curve = create_flow_curve_for_emitter(
        emitter_type=EMITTER_UNDERFLOOR,
        t_min=35.0,
        t_max=75.0,  # Generic backend default
        curve_multiplier=1.0,
        has_mixing_valve=False,
    )
    # At 0°C outdoor temp, ceiling must NOT reach 64.9°C!
    ceiling_0c = curve.ceiling(0.0)
    assert ceiling_0c <= 40.0, f"Underfloor temperature ceiling {ceiling_0c}°C exceeds 40°C safety cap!"
    assert curve.flow_for_demand(100.0, 0.0) <= 40.0


@pytest.mark.asyncio
async def test_indoor_zone_dew_point_calculation():
    """Verify dew point is calculated from indoor room sensors (temp + humidity), protecting floors."""
    hass = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()

    # Living room: 26°C and 70% indoor humidity -> Dew point is approx 20.0°C -> Safe floor >= 22.0°C
    room_temp_st = State("sensor.living_temp", "26.0")
    room_hum_st = State("sensor.living_humidity", "70.0")
    hp_st = State("climate.hp", "cool", {"temperature": 18.0})

    def get_state(eid):
        if eid == "sensor.living_temp":
            return room_temp_st
        if eid == "sensor.living_humidity":
            return room_hum_st
        return hp_st

    hass.states.get = get_state

    coord = MagicMock()
    coord.zones = [
        {
            "name": "Living",
            "temp_sensor": "sensor.living_temp",
            "humidity_sensor": "sensor.living_humidity",
            "emitter_type": EMITTER_UNDERFLOOR,
        }
    ]
    coord._climate_entities = {}

    backend = CentralHeatPumpBackend(
        hass=hass,
        coordinator=coord,
        hp_type="climate",
        hp_entity="climate.hp",
        cool_min_temp=7.0,
        cool_max_temp=18.0,
        reversible_cooling=True,
    )

    safe_floor = backend._calculate_safe_cooling_min_temp()
    assert safe_floor >= 22.0, f"Expected safe floor >= 22.0°C against indoor condensation, got {safe_floor}°C"


@pytest.mark.asyncio
async def test_heat_pump_valve_delay_no_spurious_hold_on():
    """Verify that demand falling during valve delay does not lock heat pump into spurious HOLD_ON."""
    hass = MagicMock()
    hass.states = MagicMock()
    hp_st = State("switch.hp", "off")
    hass.states.get = lambda eid: hp_st

    coord = MagicMock()
    coord.zones = []
    coord._min_cycle_on = 300.0
    coord._min_cycle_off = 180.0

    backend = CentralHeatPumpBackend(
        hass=hass,
        coordinator=coord,
        hp_type="switch",
        hp_entity="switch.hp",
        valve_delay=120,
    )

    # 1. Demand 60% arrives -> Heat pump enters valve delay wait
    await backend.async_update(demand=60.0, peak_zone="Zone 1", frost_emergency=False)
    assert backend._current_running_state is False
    assert "WAITING_VALVES" in backend._status_reason

    # 2. Demand ends (drops to 0.0%) before 120s delay finishes
    await backend.async_update(demand=0.0, peak_zone=None, frost_emergency=False)
    # Must NOT engage HOLD_ON or turn on the heat pump!
    assert backend._current_running_state is False
    assert not backend._status_reason.startswith("HOLD_ON")
    assert backend._status_reason == "OFF - No Demand"


@pytest.mark.asyncio
async def test_architecture_decoupling_and_clean_coordinator():
    """Verify architectural decoupling: fault_checker, cancel_pending_tasks, PlantOrchestrator properties."""
    from custom_components.multizone_thermostat.boiler.relay_backend import RelayBoilerBackend
    from custom_components.multizone_thermostat.boiler.plant_orchestrator import PlantOrchestrator

    # 1. DemandAggregator with fault_checker zeroes demand of faulty zone without .coordinator
    faulty_cid = "climate.zone_faulty"
    healthy_cid = "climate.zone_healthy"

    def check_fault(cid: str) -> bool:
        return cid == faulty_cid

    da = DemandAggregator(fault_checker=check_fault)
    da.register_zone("Zone Faulty", faulty_cid, mode=ZONE_MODE_PRIMARY)
    da.register_zone("Zone Healthy", healthy_cid, mode=ZONE_MODE_PRIMARY)

    da.set_zone_demand(faulty_cid, 80.0)
    da.set_zone_demand(healthy_cid, 60.0)

    # Must NOT have coordinator attribute
    assert not hasattr(da, "coordinator")

    res = da.calculate()
    assert res.demand == 60.0
    assert res.peak_zone == "Zone Healthy"

    # 2. RelayBoilerBackend.cancel_pending_tasks() cancels pending task correctly
    mock_hass = MagicMock()
    mock_coord = MagicMock()
    mock_coord._min_cycle_on = 0
    mock_coord._min_cycle_off = 0
    mock_coord._valve_delay = 100
    mock_coord.get_master_state = MagicMock(return_value=True)

    relay = RelayBoilerBackend(
        hass=mock_hass,
        coordinator=mock_coord,
        boiler_switch="switch.boiler",
        min_cycle_on=0,
        min_cycle_off=0,
        valve_delay=100,
    )

    async def dummy_pending():
        await asyncio.sleep(60)

    task = asyncio.create_task(dummy_pending())
    relay._pending_boiler_task = task
    assert not task.done()

    relay.cancel_pending_tasks()
    assert relay._pending_boiler_task is None
    assert task.cancelling() > 0 or task.cancelled()
    try:
        await task
    except asyncio.CancelledError:
        pass
    assert task.cancelled()

    # 3. PlantOrchestrator has async_refresh, is_dhw_active, is_modulating_plant, boiler_status_reason
    assert hasattr(PlantOrchestrator, "async_refresh")
    assert callable(getattr(PlantOrchestrator, "async_refresh"))
    assert hasattr(PlantOrchestrator, "is_dhw_active")
    assert isinstance(getattr(PlantOrchestrator, "is_dhw_active"), property)
    assert hasattr(PlantOrchestrator, "is_modulating_plant")
    assert isinstance(getattr(PlantOrchestrator, "is_modulating_plant"), property)
    assert hasattr(PlantOrchestrator, "boiler_status_reason")
    assert isinstance(getattr(PlantOrchestrator, "boiler_status_reason"), property)


@pytest.mark.asyncio
async def test_frost_manager_pre_frost_targets_persistence_and_restore_after_restart():
    """Verify pre_frost_targets persists across coordinator/FrostManager restarts."""
    from custom_components.multizone_thermostat.safety.frost import FrostManager
    from custom_components.multizone_thermostat.const import (
        KEY_ANTI_FROST_ENABLED,
        KEY_FROST_PROTECTION_TEMP,
        CONF_ZONE_NAME,
        make_zone_entity_id,
    )

    hass = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()

    cid = make_zone_entity_id("Salone")
    zone_st = State(cid, "heat", {"current_temperature": 4.0, "temperature": 22.5})
    hass.states.get = MagicMock(return_value=zone_st)

    persistent_store = {
        KEY_ANTI_FROST_ENABLED: True,
        KEY_FROST_PROTECTION_TEMP: 7.0,
    }

    coord = MagicMock()
    coord.zones = [{CONF_ZONE_NAME: "Salone"}]
    coord.plant_diagnostics.has_critical_sensor_fault.return_value = False
    coord._settings = persistent_store
    coord.get_persistent_data = lambda k, default=None: persistent_store.get(k, default)
    coord.async_set_persistent_data = AsyncMock(
        side_effect=lambda k, v: persistent_store.update({k: v})
    )
    coord._async_set_hvac_mode = AsyncMock()

    # 1. Trigger frost emergency on initial manager
    mgr = FrostManager(hass, coord)
    res = await mgr.async_handle_frost_emergencies()
    assert res is True
    assert mgr._pre_frost_targets[cid] == 22.5
    assert persistent_store.get("pre_frost_targets", {}).get(cid) == 22.5

    # 2. Simulate HA restart: create a new FrostManager reading the same persistent storage
    new_mgr = FrostManager(hass, coord)
    assert new_mgr._pre_frost_targets.get(cid) == 22.5

    # 3. Temp rises back to safe level (9.5°C >= 7.0 + 1.5°C) -> emergency ends and restores 22.5°C
    zone_st.attributes["current_temperature"] = 9.5
    res2 = await new_mgr.async_handle_frost_emergencies()
    assert res2 is False
    assert cid not in new_mgr._pre_frost_targets
    assert cid not in persistent_store.get("pre_frost_targets", {})

    hass.services.async_call.assert_any_call(
        "climate",
        "set_temperature",
        {"entity_id": cid, "temperature": 22.5},
        blocking=False,
    )


def test_pid_controller_validation_exceptions():
    """Verify PID/PIDController raises explicit ValueError and TypeError instead of assert."""
    from custom_components.multizone_thermostat.pid import PID, PIDController

    assert PIDController is PID
    controller = PIDController(kp=10.0, ki=0.1, kd=1.0)

    # Mode validation
    with pytest.raises(ValueError, match="Invalid PID mode"):
        controller.mode = "INVALID_MODE"
    with pytest.raises(ValueError, match="Invalid PID mode"):
        controller.mode = 999

    controller.mode = "off"
    assert controller.mode == "OFF"
    controller.mode = "AUTO"
    assert controller.mode == "AUTO"

    # Integral validation
    with pytest.raises(TypeError, match="integral must be int or float"):
        controller.integral = "not_a_float"
    with pytest.raises(TypeError, match="integral must be int or float"):
        controller.integral = None

    controller.integral = 12.5
    assert controller.integral == 12.5


def test_heat_source_priorities_includes_gas_and_electric():
    """Verify SOURCE_PRIORITY_GAS and SOURCE_PRIORITY_ELECTRIC are in HEAT_SOURCE_PRIORITIES."""
    from custom_components.multizone_thermostat.const import (
        HEAT_SOURCE_PRIORITIES,
        SOURCE_PRIORITY_GAS,
        SOURCE_PRIORITY_ELECTRIC,
    )

    assert SOURCE_PRIORITY_GAS in HEAT_SOURCE_PRIORITIES
    assert SOURCE_PRIORITY_ELECTRIC in HEAT_SOURCE_PRIORITIES
    assert SOURCE_PRIORITY_GAS == "gas_priority"
    assert SOURCE_PRIORITY_ELECTRIC == "electric_priority"


@pytest.mark.asyncio
async def test_modulating_backends_read_frost_flow_temp():
    """Verify modulating backends read configured KEY_FROST_FLOW_TEMP from persistent storage."""
    from custom_components.multizone_thermostat.boiler.opentherm_backend import OpenThermBoilerBackend
    from custom_components.multizone_thermostat.boiler.heat_pump_backend import CentralHeatPumpBackend
    from custom_components.multizone_thermostat.const import KEY_FROST_FLOW_TEMP

    hass = MagicMock()
    hass.states = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    ot_st = State("number.ot_flow", "40.0")
    hp_st = State("number.hp_flow", "35.0")
    hass.states.get = lambda eid: ot_st if "ot" in eid else hp_st

    storage_data = {KEY_FROST_FLOW_TEMP: 50.0}
    coord = MagicMock()
    coord.has_mixing_valve = False
    coord.zones = []
    coord.weather_sensor_id = None
    coord.get_persistent_data = lambda k, default=None: storage_data.get(k, default)

    # 1. OpenTherm backend reads 50.0°C from persistent data
    ot = OpenThermBoilerBackend(
        hass=hass,
        coordinator=coord,
        opentherm_entity="number.ot_flow",
        min_temp=25.0,
        max_temp=75.0,
    )
    await ot.async_update(demand=0.0, peak_zone=None, frost_emergency=True)
    assert "50.0°C" in ot.status_reason
    hass.services.async_call.assert_any_call(
        "number",
        "set_value",
        {"entity_id": "number.ot_flow", "value": 50.0},
        blocking=False,
    )

    # 2. CentralHeatPumpBackend reads 38.0°C from persistent data
    storage_data[KEY_FROST_FLOW_TEMP] = 38.0
    hp = CentralHeatPumpBackend(
        hass=hass,
        coordinator=coord,
        hp_type="number",
        hp_entity="number.hp_flow",
        min_temp=20.0,
        max_temp=55.0,
    )
    await hp.async_update(demand=0.0, peak_zone=None, frost_emergency=True)
    assert "38.0°C" in hp.status_reason
    hass.services.async_call.assert_any_call(
        "number",
        "set_value",
        {"entity_id": "number.hp_flow", "value": 38.0},
        blocking=False,
    )


def test_coordinator_heat_pump_cycle_propagation():
    """Verify coordinator propagates min cycle times to Heat Pump backend if present."""
    from custom_components.multizone_thermostat.boiler.heat_pump_backend import CentralHeatPumpBackend
    from custom_components.multizone_thermostat.coordinator import MultizoneCoordinator

    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {
        "boiler_mode": "relay",
        "zones": [],
    }

    coord = MultizoneCoordinator(hass, entry)
    coord.heat_pump_backend = MagicMock(spec=CentralHeatPumpBackend)

    coord.set_min_cycle_on(7.5)
    assert coord.min_cycle_on == 7.5
    coord.heat_pump_backend.set_min_cycle_on.assert_called_once_with(7.5)

    coord.set_min_cycle_off(4.0)
    assert coord.min_cycle_off == 4.0
    coord.heat_pump_backend.set_min_cycle_off.assert_called_once_with(4.0)


def test_plant_config_zone_helpers():
    """Verify safe dict access helpers in plant_config.py."""
    from custom_components.multizone_thermostat.plant_config import (
        get_zone_name,
        get_zone_climates,
        get_zone_switches,
        get_zone_valves,
    )

    valid_zone = {
        "name": "Studio",
        "zone_climates": ["climate.studio"],
        "zone_switches": ["switch.studio"],
        "zone_valves": ["valve.studio"],
    }
    assert get_zone_name(valid_zone) == "Studio"
    assert get_zone_climates(valid_zone) == ["climate.studio"]
    assert get_zone_switches(valid_zone) == ["switch.studio"]
    assert get_zone_valves(valid_zone) == ["valve.studio"]

    # Legacy / alias keys
    legacy_zone = {
        "zone_name": "Soggiorno",
        "climates": ["climate.soggiorno"],
        "switches": ["switch.soggiorno"],
        "valves": ["valve.soggiorno"],
    }
    assert get_zone_name(legacy_zone) == "Soggiorno"
    assert get_zone_climates(legacy_zone) == ["climate.soggiorno"]
    assert get_zone_switches(legacy_zone) == ["switch.soggiorno"]
    assert get_zone_valves(legacy_zone) == ["valve.soggiorno"]

    # Fallbacks and invalid types
    assert get_zone_name({}) == ""
    assert get_zone_name(None) == ""
    assert get_zone_climates({}) == []
    assert get_zone_switches(None) == []
    assert get_zone_valves({}) == []


def test_sensor_watchdog_fallback_reading():
    """Verify SensorWatchdog calculates fallback TRV average using get_zone_climates."""
    from custom_components.multizone_thermostat.safety.watchdog import SensorWatchdog

    hass = MagicMock()
    st1 = State("climate.trv_1", "heat", {"current_temperature": 21.0})
    st2 = State("climate.trv_2", "heat", {"current_temperature": 23.0})
    hass.states.get = lambda eid: st1 if eid == "climate.trv_1" else (st2 if eid == "climate.trv_2" else None)

    wd = SensorWatchdog(hass)
    zone = {"zone_climates": ["climate.trv_1", "climate.trv_2"]}
    avg = wd.get_zone_trv_fallback_temp(zone)
    assert avg == 22.0

    # Unavailable states are skipped
    st_unavail = State("climate.trv_2", "unavailable", {"current_temperature": 5.0})
    hass.states.get = lambda eid: st1 if eid == "climate.trv_1" else st_unavail
    avg2 = wd.get_zone_trv_fallback_temp(zone)
    assert avg2 == 21.0


def test_schedule_storage_manual_override_expiration():
    """Verify ScheduleProfileStorage.get_valid_manual_override handles validity and expiry."""
    from datetime import datetime, timezone
    from custom_components.multizone_thermostat.schedule.storage import ScheduleProfileStorage

    coord = MagicMock()
    storage = ScheduleProfileStorage(coord)

    now = datetime(2026, 11, 11, 10, 0, 0, tzinfo=timezone.utc)
    cid = "climate.living"

    # 1. Valid override with matching slot
    storage.manual_overrides[cid] = {
        "target_temp": 22.5,
        "slot_id": "slot_morning",
        "until": "2026-11-11T12:00:00+00:00",
    }
    assert storage.get_valid_manual_override(cid, "slot_morning", now) == 22.5
    assert cid in storage.manual_overrides

    # 2. Slot changed -> override dropped
    assert storage.get_valid_manual_override(cid, "slot_afternoon", now) is None
    assert cid not in storage.manual_overrides

    # 3. Expired override -> dropped
    storage.manual_overrides[cid] = {
        "target_temp": 22.5,
        "slot_id": "slot_morning",
        "until": "2026-11-11T09:00:00+00:00",
    }
    assert storage.get_valid_manual_override(cid, "slot_morning", now) is None
    assert cid not in storage.manual_overrides


def test_heat_pump_dedicated_min_cycles():
    """Verify CentralHeatPumpBackend reads dedicated hp_min_cycle_on/off keys."""
    from custom_components.multizone_thermostat.boiler.heat_pump_backend import CentralHeatPumpBackend
    from custom_components.multizone_thermostat.const import KEY_HP_MIN_CYCLE_ON, KEY_HP_MIN_CYCLE_OFF

    hass = MagicMock()
    coord = MagicMock()
    data = {
        KEY_HP_MIN_CYCLE_ON: 12.0,
        KEY_HP_MIN_CYCLE_OFF: 8.0,
    }
    coord.get_persistent_data = lambda k, default=None: data.get(k, default)

    hp = CentralHeatPumpBackend(
        hass=hass,
        coordinator=coord,
        hp_type="climate",
        hp_entity="climate.hp",
    )
    assert hp.min_cycle_on == 12.0
    assert hp.min_cycle_off == 8.0




