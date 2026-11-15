"""External Audit Integration Tests for beta.6 fixes across all tracks.
...
"""
from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Clear any mock entries injected by earlier test modules
sys.meta_path[:] = [
    f for f in sys.meta_path if f.__class__.__name__ != "HomeAssistantMockFinder"
]
for _mod_name in (
    "homeassistant.components.select",
    "homeassistant.components.number",
    "homeassistant.components.switch",
    "homeassistant.components.button",
    "homeassistant.components.sensor",
    "homeassistant.helpers.restore_state",
    "homeassistant.helpers.entity",
):
    if _mod_name in sys.modules and isinstance(sys.modules[_mod_name], MagicMock):
        del sys.modules[_mod_name]

import math
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import voluptuous as vol

from homeassistant.core import State
from homeassistant.components.climate import HVACMode

from custom_components.multizone_thermostat import (
    _extract_entity_ids,
    SERVICE_SET_PID_SCHEMA,
    SERVICE_RESET_AUTOTUNE_SCHEMA,
    _async_register_services,
)
from custom_components.multizone_thermostat.const import (
    DOMAIN,
    KEY_HP_MIN_CYCLE_ON,
    KEY_HP_MIN_CYCLE_OFF,
    KEY_MIN_CYCLE_ON,
    KEY_MIN_CYCLE_OFF,
    KEY_VALVE_DELAY,
    CONF_GRID_EXPORT_INVERTED,
    CONF_GRID_EXPORT_SENSOR,
    CONF_ENERGY_MANAGEMENT_ENABLED,
    CONF_SOLAR_EXPORT_THRESHOLD,
    CONF_SOLAR_MIN_RUN_TIME,
    EMITTER_TYPE_UNDERFLOOR,
    EMITTER_TYPE_RADIATOR,
    ZONE_MODE_PRIMARY,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    make_zone_entity_id,
)
from custom_components.multizone_thermostat.coordinator import MultizoneCoordinator
from custom_components.multizone_thermostat.boiler.heat_pump_backend import CentralHeatPumpBackend
from custom_components.multizone_thermostat.boiler.opentherm_backend import OpenThermBoilerBackend
from custom_components.multizone_thermostat.boiler.relay_backend import RelayBoilerBackend
from custom_components.multizone_thermostat.boiler.plant_orchestrator import PlantOrchestrator
from custom_components.multizone_thermostat.demand_aggregator import (
    DemandAggregator,
    DEMAND_STRATEGY_WEIGHTED_AVERAGE,
)
from custom_components.multizone_thermostat.safety.anti_seize import AntiSeizeManager
from custom_components.multizone_thermostat.energy.energy_manager import EnergyManager
from custom_components.multizone_thermostat.number import MultizonePersistentNumber
from custom_components.multizone_thermostat.pid import PID
from custom_components.multizone_thermostat.autotune import PassiveAutotuneObserver
from custom_components.multizone_thermostat.thermal_model import ThermalObserver
from custom_components.multizone_thermostat.listener_manager import ListenerManager


# ==============================================================================
# Item 1: Number live-updating HeatPumpBackend.min_cycle_on (5 min -> 300.0s)
# ==============================================================================
@pytest.mark.asyncio
async def test_audit_number_hp_min_cycle_live_update():
    """Verify MultizonePersistentNumber for KEY_HP_MIN_CYCLE_ON live-updates heat_pump_backend.min_cycle_on."""
    hass = MagicMock()
    coord = MultizoneCoordinator.__new__(MultizoneCoordinator)
    coord.hass = hass
    coord._min_cycle_on = 5.0
    coord._min_cycle_off = 5.0
    coord._valve_delay = 30.0
    coord._hp_min_cycle_on = 5.0
    coord._hp_min_cycle_off = 5.0
    coord.async_set_persistent_data = AsyncMock()

    hp = CentralHeatPumpBackend(hass, coord, "climate", "climate.hp")
    coord.heat_pump_backend = hp
    coord.boiler_backend = None

    number_entity = MultizonePersistentNumber(
        coord,
        "entry_test",
        KEY_HP_MIN_CYCLE_ON,
        "HP Min Cycle On",
        0,
        30,
        1,
        "min",
        "mdi:timer",
        5,
        MagicMock(),
    )
    number_entity.async_write_ha_state = MagicMock()

    # User changes slider to 5 minutes
    await number_entity.async_set_native_value(5.0)

    # Persistent storage and coordinator runtime state updated
    coord.async_set_persistent_data.assert_called_with(KEY_HP_MIN_CYCLE_ON, 5.0)
    assert coord.hp_min_cycle_on == 5.0

    # Heat pump backend runtime min_cycle_on must be 300.0s (5.0 * 60s)
    assert hp.min_cycle_on == 300.0


# ==============================================================================
# Item 2: OpenTherm mixed underfloor + radiator peak clamped to <= 40.0°C
# ==============================================================================
@pytest.mark.asyncio
async def test_audit_opentherm_mixed_underfloor_radiator_peak_clamped():
    """Verify OpenTherm target_temp is clamped to <= 40.0°C when mixed underfloor is present without mixing valve."""
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    st_ot = State("climate.ot_boiler", "heat", {"temperature": 35.0})
    st_weather = State("weather.home", "sunny", {"temperature": 0.0})
    states_dict = {
        "climate.ot_boiler": st_ot,
        "weather.home": st_weather,
    }
    hass.states.get = lambda eid: states_dict.get(eid)

    coord = MagicMock()
    coord.has_mixing_valve = False
    coord.weather_sensor = "weather.home"
    coord.plant_diagnostics = None
    coord.get_persistent_data = lambda k, d=None: 2.0 if k == "weather_curve" else d

    # Mixed setup: Zone 1 is underfloor, Zone 2 is radiator
    coord.zones = [
        {"name": "Living", "emitter_type": EMITTER_TYPE_UNDERFLOOR},
        {"name": "Bedrooms", "emitter_type": EMITTER_TYPE_RADIATOR},
    ]

    backend = OpenThermBoilerBackend(hass, coord, "climate.ot_boiler", min_temp=30.0, max_temp=75.0)

    # Peak zone is radiator at 0°C outdoor temp -> weather curve wants high temp (>60°C),
    # but underfloor safety ceiling MUST clamp it to <= 40.0°C
    await backend.async_update(demand=100.0, peak_zone="Bedrooms", frost_emergency=False)

    hass.services.async_call.assert_any_call(
        "climate", "set_temperature", {"entity_id": "climate.ot_boiler", "temperature": 40.0}, blocking=False
    )


# ==============================================================================
# Item 3: Weighted Average 70% peak floor + monotonicity
# ==============================================================================
def test_audit_demand_aggregator_weighted_average_peak_floor_and_monotonicity():
    """Verify 70% peak floor and strict monotonicity in weighted average demand aggregation."""
    agg = DemandAggregator(strategy=DEMAND_STRATEGY_WEIGHTED_AVERAGE)
    z_small = agg.register_zone("SmallZone", weight=10.0, mode=ZONE_MODE_PRIMARY)
    z_large = agg.register_zone("LargeZone", weight=90.0, mode=ZONE_MODE_PRIMARY)

    # 1. Peak floor: Small zone active at 100%, Large zone at 0%
    # Raw weighted average = 10%, but peak floor = 0.70 * 100% = 70.0%
    agg.set_zone_demand(z_small, 100.0)
    agg.set_zone_demand(z_large, 0.0)
    res = agg.calculate()
    assert res.demand == 70.0
    assert res.peak_zone == "SmallZone"

    # 2. Monotonicity: Small at 50%, increase Large from 0% to 100%
    agg.set_zone_demand(z_small, 50.0)
    demands = [0.0, 10.0, 25.0, 50.0, 75.0, 90.0, 100.0]
    agg_outputs = []
    for d in demands:
        agg.set_zone_demand(z_large, d)
        out = agg.calculate().demand
        agg_outputs.append(out)

    # Assert non-decreasing monotonicity: D_i <= D_{i+1}
    for i in range(len(agg_outputs) - 1):
        assert agg_outputs[i] <= agg_outputs[i + 1]


# ==============================================================================
# Item 4: Heat Pump safe cooling min temp ignores zones in heat/off
# ==============================================================================
def test_audit_heat_pump_safe_cooling_min_temp_ignores_inactive_humidity():
    """Verify safe cooling min temp calculation ignores high humidity in zones that are OFF or in HEAT."""
    hass = MagicMock()
    coord = MagicMock()
    coord.hp_cool_min_temp = 7.0
    coord.hp_cool_max_temp = 18.0
    coord.get_zone_mode = MagicMock(return_value="primary")
    coord.split_manager = MagicMock()
    coord.split_manager.has_split.return_value = False
    coord.split_manager.is_split_active.return_value = False

    # Zone 1: Active cooling, normal RH 50%, 24°C -> safe dew point around 13°C
    cid_active = make_zone_entity_id("ActiveCooling")
    climate_active = MagicMock(hvac_mode=HVACMode.COOL)

    # Zone 2: Bathroom or off room, extreme RH 95%, 24°C -> dew point would be ~23°C
    cid_off = make_zone_entity_id("OffBathroom")
    climate_off = MagicMock(hvac_mode=HVACMode.OFF)

    coord._climate_entities = {
        cid_active: climate_active,
        cid_off: climate_off,
    }

    coord.zones = [
        {"name": "ActiveCooling", "emitter_type": EMITTER_TYPE_UNDERFLOOR, "temp_sensor": "sensor.active_temp", "humidity_sensor": "sensor.active_hum"},
        {"name": "OffBathroom", "emitter_type": EMITTER_TYPE_UNDERFLOOR, "temp_sensor": "sensor.off_temp", "humidity_sensor": "sensor.off_hum"},
    ]

    states_dict = {
        "sensor.active_temp": State("sensor.active_temp", "24.0"),
        "sensor.active_hum": State("sensor.active_hum", "50.0"),
        "sensor.off_temp": State("sensor.off_temp", "24.0"),
        "sensor.off_hum": State("sensor.off_hum", "95.0"),
    }
    hass.states.get = lambda eid: states_dict.get(eid)

    hp = CentralHeatPumpBackend(hass, coord, "climate", "climate.hp", cool_min_temp=7.0, cool_max_temp=25.0)

    # Calculate safe cooling min temp: off zone with 95% RH MUST be ignored
    safe_floor_ignored = hp._calculate_safe_cooling_min_temp()

    # Now simulate Zone 2 entering cooling mode: high RH must now trigger protection
    climate_off.hvac_mode = HVACMode.COOL
    safe_floor_active = hp._calculate_safe_cooling_min_temp()

    # Active zone with 95% RH must raise the floor higher than when it was ignored
    assert safe_floor_active > safe_floor_ignored


# ==============================================================================
# Item 5: AntiSeizeManager task guard prevents duplicate tasks
# ==============================================================================
@pytest.mark.asyncio
async def test_audit_anti_seize_task_guard_prevents_duplicate():
    """Verify AntiSeizeManager guards against launching concurrent tasks."""
    hass = MagicMock()
    coord = MagicMock()
    coord.zones = []
    coord.get_persistent_data.return_value = True

    mgr = AntiSeizeManager(hass, coord)

    # Simulate already running task
    active_task = MagicMock()
    active_task.done.return_value = False
    mgr._task = active_task

    # check_anti_seize should bail out immediately
    mgr.check_anti_seize()
    hass.async_create_task.assert_not_called()

    # trigger_manually should return existing task without creating new one
    returned_task = mgr.trigger_manually()
    assert returned_task is active_task
    hass.async_create_task.assert_not_called()


# ==============================================================================
# Item 6: PID monotonic, non-finite rejection, max_dt=600.0, dt<1.0, high Kd step
# ==============================================================================
def test_audit_pid_monotonic_inf_max_dt_derivative():
    """Verify PID monotonic time, non-finite rejection, max_dt=600s windup clamp, and derivative filtering."""
    pid = PID(kp=10.0, ki=0.1, kd=1000.0, max_dt=600.0)

    # 1. Monotonic normal sample
    out, updated = pid.calc(input_val=19.0, set_point=20.0, input_time=100.0, last_input_time=None)
    assert updated is True
    assert out > 0.0

    # 2. Inf / NaN rejection
    out_nan, up_nan = pid.calc(input_val=float("nan"), set_point=20.0, input_time=110.0, last_input_time=100.0)
    assert up_nan is False
    assert out_nan == out

    out_inf, up_inf = pid.calc(input_val=float("inf"), set_point=20.0, input_time=110.0, last_input_time=100.0)
    assert up_inf is False

    # 3. max_dt = 600.0 windup clamp: gap of 3600s with error=1.0
    # Integral accumulation must use dt = 600.0s, NOT 3600.0s!
    pid_windup = PID(kp=0.0, ki=0.01, kd=0.0, max_dt=600.0)
    pid_windup.calc(input_val=19.0, set_point=20.0, input_time=1000.0, last_input_time=None)
    assert pid_windup.integral == 0.0

    pid_windup.calc(input_val=19.0, set_point=20.0, input_time=4600.0, last_input_time=1000.0)  # dt = 3600s
    expected_integral = 0.01 * 1.0 * 600.0  # 6.0
    assert pid_windup.integral == pytest.approx(expected_integral)

    # 4. High Kd step: 0.1°C jump with Kd=1000.0 over 10s
    # raw_derivative = -(1000 * 0.1) / 10 = -10.0
    # Filtered and clamped to [-15, 15]
    pid_deriv = PID(kp=0.0, ki=0.0, kd=1000.0)
    pid_deriv.calc(input_val=20.0, set_point=20.0, input_time=0.0, last_input_time=None)
    pid_deriv.calc(input_val=20.1, set_point=20.0, input_time=10.0, last_input_time=0.0)
    assert abs(pid_deriv.derivative) <= 15.0

    # Extreme jump (drop 5°C in 1s) -> raw = +5000 -> clamped to exactly 15.0
    pid_deriv.calc(input_val=15.1, set_point=20.0, input_time=11.0, last_input_time=10.0)
    assert pid_deriv.derivative == pytest.approx(15.0)

    # 5. dt < 1.0s: derivative must be reset to 0.0
    pid_deriv.calc(input_val=15.1, set_point=20.0, input_time=11.5, last_input_time=11.0)
    assert pid_deriv.derivative == 0.0


# ==============================================================================
# Item 7: Autotune limits, false start block, drift clamp [0.5x, 2.0x], rollback
# ==============================================================================
def test_audit_autotune_limits_and_weekly_clamping():
    """Verify Autotune L up to 14400s, Ti>=600s, Kd<=500, weekly ramp blocking, drift clamp, and rollback."""
    tuner = PassiveAutotuneObserver("climate.test", required_cycles=1)
    t0 = 1_000_000.0

    # 1. Complete 1 cycle to reach COMPLETED state with baseline
    tuner.completed_cycles.append({
        "L": 180.0, "slope": 0.001, "Kp": 60.0, "Ki": 0.02, "Kd": 250.0, "timestamp": t0
    })
    tuner.state = tuner.STATE_COMPLETED
    tuner._compute_final_pid()
    assert tuner.baseline_kp == 60.0
    assert tuner.baseline_ki == 0.02
    assert tuner.baseline_kd == 250.0

    # 2. False start prevention: active at demand 40% -> was_idle_before_ramp is False
    tuner.update(20.0, is_active=True, now=t0 + 10.0, demand=40.0)
    assert tuner._was_idle_before_ramp is False
    # Now demand jumps to 90%: ramp MUST NOT start because system was not idle
    tuner.update(20.1, is_active=True, now=t0 + 20.0, demand=90.0)
    assert tuner._ramp_active is False

    # 3. Weekly drift clamp: candidates suggest wildly high gains
    # Candidate values: Kp=300 (5x baseline), Ki=0.2, Kd=1000
    tuner.weekly_candidates = [
        {"Kp": 300.0, "Ki": 0.2, "Kd": 1000.0, "L": 180.0, "slope": 0.005},
        {"Kp": 300.0, "Ki": 0.2, "Kd": 1000.0, "L": 180.0, "slope": 0.005},
        {"Kp": 300.0, "Ki": 0.2, "Kd": 1000.0, "L": 180.0, "slope": 0.005},
    ]
    tuner.last_weekly_update = t0 - 700000.0  # Force > 1 week elapsed
    tuner.update(20.0, is_active=False, now=t0 + 800000.0, demand=0.0)

    # Learned Kp must be clamped to <= 2.0 * baseline_kp (120.0)
    assert tuner._learned_kp <= 2.0 * tuner.baseline_kp
    assert tuner._learned_kp >= 0.5 * tuner.baseline_kp

    # 4. Rollback to baseline
    tuner._learned_kp = 115.0
    tuner._sync_effective_pid()
    assert tuner.kp == 115.0
    tuner.rollback_to_baseline()
    assert tuner.kp == 60.0
    assert tuner._learned_kp == 60.0


# ==============================================================================
# Item 8: ThermalObserver updating heating_rate at demand=45.0%
# ==============================================================================
def test_audit_thermal_observer_heating_rate_at_45_percent_demand():
    """Verify ThermalObserver updates heating rate at demand=45.0% with duty normalization."""
    obs = ThermalObserver("climate.zone_test")
    obs._last_temp = 19.0
    obs._last_temp_time = 1000.0
    obs._is_heating = True

    # After 1800s (0.5 hr), temp rises from 19.0 to 19.45 (+0.45°C) at demand=45.0%
    # raw_rate = 0.45 / 0.5 = 0.90 °C/hr
    # normalized by duty 0.45 -> 0.90 / 0.45 = 2.0 °C/hr
    with patch("time.monotonic", return_value=2800.0):
        obs.update(19.45, is_heating=True, demand=45.0)
        assert obs.heating_rate == pytest.approx(2.0, rel=1e-2)


# ==============================================================================
# Item 9: E2E Event Propagation -> zone_controller.async_update_zone called 1 time
# ==============================================================================
@pytest.mark.asyncio
async def test_audit_e2e_event_propagation_single_zone_update():
    """Verify ListenerManager -> PlantOrchestrator.async_refresh calls async_update_zone ONCE (not twice)."""
    hass = MagicMock()
    demand_agg = DemandAggregator()
    cid = make_zone_entity_id("Salotto")
    demand_agg.register_zone("Salotto", 100.0)

    coord = MultizoneCoordinator.__new__(MultizoneCoordinator)
    coord.hass = hass
    coord.demand_aggregator = demand_agg
    coord._climate_entities = {cid: MagicMock(entity_id=cid)}
    coord.zones = [{"name": "Salotto"}]
    coord.resolve_zone_id = lambda x: x
    coord.get_master_state = lambda: True
    coord._master_state = True
    coord.dhw_sensor = None
    coord.frost_manager = None
    coord.plant_diagnostics = None
    coord.enable_heat_pump = False
    coord.enable_gas_heater = True
    coord._climate_callbacks = {cid: lambda: None}
    coord._pid_listeners = []
    coord._unsub_listeners = []

    boiler_backend = MagicMock()
    boiler_backend.async_update = AsyncMock()
    coord.boiler_backend = boiler_backend
    coord.heat_pump_backend = None

    pid_mock = MagicMock()
    pid_mock._last_input_time = 12345.0

    zone_ctrl = MagicMock()
    zone_ctrl.async_update_zone = AsyncMock(return_value=65.0)
    zone_ctrl.get_pid = MagicMock(return_value=pid_mock)
    coord.zone_controller = zone_ctrl

    orch = PlantOrchestrator(hass, demand_agg, boiler_backend, coord)
    coord.plant_orchestrator = orch

    lm = ListenerManager(coord)
    new_state = State(cid, "heat", {"current_temperature": 19.5, "temperature": 21.0})
    event = MagicMock(data={"entity_id": cid, "new_state": new_state})

    # Trigger event
    await lm.async_on_climate_state_changed(event)

    # zone_controller.async_update_zone must have been called exactly ONCE:
    # by ListenerManager directly, and NOT re-evaluated by PlantOrchestrator._async_refresh_zones_proactively!
    assert zone_ctrl.async_update_zone.call_count == 1
    assert demand_agg.get_zone_demand(cid) == 65.0


# ==============================================================================
# Item 10: Services entity_id list + NaN/inf/out-of-range kp rejection
# ==============================================================================
@pytest.mark.asyncio
async def test_audit_services_list_entities_and_nan_inf_rejection():
    """Verify services accept entity_id list and reject NaN, inf, and out-of-range values."""
    # 1. Schema rejection
    with pytest.raises(vol.Invalid):
        SERVICE_SET_PID_SCHEMA({"entity_id": "climate.test", "kp": float("nan")})

    with pytest.raises(vol.Invalid):
        SERVICE_SET_PID_SCHEMA({"entity_id": "climate.test", "kp": float("inf")})

    with pytest.raises(vol.Invalid):
        SERVICE_SET_PID_SCHEMA({"entity_id": "climate.test", "kp": 0.05})  # min 0.1

    with pytest.raises(vol.Invalid):
        SERVICE_SET_PID_SCHEMA({"entity_id": "climate.test", "kp": 600.0})  # max 500.0

    # 2. Service execution with list of entity IDs
    hass = MagicMock()
    hass.data = {DOMAIN: {}}

    coord = MagicMock()
    coord.resolve_zone_id = lambda x: x
    coord.zones = [{"name": "Soggiorno"}]
    coord.async_set_pid_manual_unlock = AsyncMock()
    coord.async_notify_pid_entities = MagicMock()
    coord.plant_orchestrator._async_update_boiler = AsyncMock()

    zc = MagicMock()
    zc.async_set_zone_pid = AsyncMock(return_value=True)
    zc.async_reset_zone_autotuner = AsyncMock(return_value=True)
    coord.zone_controller = zc

    hass.data[DOMAIN]["entry1"] = {"coordinator": coord}

    handlers = {}
    hass.services.async_register = lambda domain, svc, h, schema=None: handlers.update({svc: h})

    await _async_register_services(hass)

    # Test set_pid_parameters with list of entity_id
    set_pid_h = handlers["set_pid_parameters"]
    await set_pid_h(SimpleNamespace(data={"entity_id": ["climate.multizone_thermostat_soggiorno"], "kp": 110.0}))
    zc.async_set_zone_pid.assert_called_once_with("climate.multizone_thermostat_soggiorno", kp=110.0, ki=None, kd=None, lock_param=None)

    # Test reset_autotune with list of entity_id
    reset_h = handlers["reset_autotune"]
    await reset_h(SimpleNamespace(data={"entity_id": ["climate.multizone_thermostat_soggiorno"]}))
    zc.async_reset_zone_autotuner.assert_called_once_with("climate.multizone_thermostat_soggiorno", keep_manual_overrides=False)


# ==============================================================================
# Item 11: RelayBoilerBackend log deduplication inside parentheses
# ==============================================================================
def test_audit_relay_boiler_log_throttling():
    """Verify RelayBoilerBackend logs INFO on state category transitions, but DEBUG on numeric countdown changes."""
    hass = MagicMock()
    coord = MagicMock()
    backend = RelayBoilerBackend(hass, coord, "switch.boiler", min_cycle_on=5.0, min_cycle_off=5.0, valve_delay=0)

    with patch("custom_components.multizone_thermostat.boiler.relay_backend._LOGGER") as mock_log:
        # Category transition -> INFO
        backend._status_reason = "HOLD_OFF - min_cycle_off active (300s remaining)"
        mock_log.info.assert_called_once()
        mock_log.debug.assert_not_called()

        # Countdown change -> DEBUG only
        mock_log.reset_mock()
        backend._status_reason = "HOLD_OFF - min_cycle_off active (299s remaining)"
        mock_log.info.assert_not_called()
        mock_log.debug.assert_called_once()

        # Category transition -> INFO
        mock_log.reset_mock()
        backend._status_reason = "OFF - No Demand"
        mock_log.info.assert_called_once()


# ==============================================================================
# Item 12: EnergyManager inverted export + hysteresis & min run time hold
# ==============================================================================
def test_audit_energy_manager_grid_export_inverted_and_hysteresis_hold():
    """Verify EnergyManager inverted grid export (-W = export), hysteresis threshold, and hold duration."""
    hass = MagicMock()
    coord = MagicMock()
    config = {
        CONF_ENERGY_MANAGEMENT_ENABLED: True,
        CONF_GRID_EXPORT_SENSOR: "sensor.export",
        CONF_GRID_EXPORT_INVERTED: True,
        CONF_SOLAR_EXPORT_THRESHOLD: 500.0,
        CONF_SOLAR_MIN_RUN_TIME: 15,
    }
    em = EnergyManager(hass, coord, config)

    # 1. Negative sensor value: -800W -> 800W export (> 500W threshold) -> surplus True
    hass.states.get.return_value = MagicMock(state="-800.0")
    assert em.get_grid_export() == 800.0
    assert em.is_solar_surplus() is True

    # 2. Hysteresis: drops to -400W (< 500W threshold, but > 0.7*500=350W off threshold)
    hass.states.get.return_value = MagicMock(state="-400.0")
    assert em.is_solar_surplus() is True

    # 3. Drops to 0W (< 350W off threshold): held active by solar_min_run_time (15 min)
    hass.states.get.return_value = MagicMock(state="0.0")
    assert em.is_solar_surplus() is True

    # 4. Fast forward 16 minutes (> 15 min run time) -> surplus expires
    em._surplus_active_since -= 960.0
    assert em.is_solar_surplus() is False
