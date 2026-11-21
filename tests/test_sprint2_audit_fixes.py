"""Regression tests for Sprint 2 audit fixes (control loop, scheduling, energy, diagnostics, frost)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sys
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import zoneinfo

import pytest

# Ensure dummy_ha modules are used cleanly if earlier tests injected mocks
sys.meta_path[:] = [
    f for f in sys.meta_path if f.__class__.__name__ != "HomeAssistantMockFinder"
]
for _mod_name in (
    "homeassistant.components.select",
    "homeassistant.helpers.restore_state",
    "homeassistant.helpers.entity",
):
    if _mod_name in sys.modules and isinstance(sys.modules[_mod_name], MagicMock):
        del sys.modules[_mod_name]

from homeassistant.components.climate import HVACMode
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import Context, Event, State
import homeassistant.util.dt as dt_util

from custom_components.multizone_thermostat.autotune import PassiveAutotuneObserver, PIDAutotune
from custom_components.multizone_thermostat.boiler.plant_orchestrator import PlantOrchestrator
from custom_components.multizone_thermostat.calendar_manager import CalendarManager
from custom_components.multizone_thermostat.calendar_parser import parse_calendar_event
from custom_components.multizone_thermostat.climate import MultizoneVirtualThermostat
from custom_components.multizone_thermostat.const import (
    CONF_MASTER_HVAC_MODE,
    CONF_ZONE_NAME,
    CONF_ZONE_SENSOR_TIMEOUT,
    CONF_ZONE_TEMP_SENSOR,
    DOMAIN,
    GLOBAL_PRESET_AWAY,
    GLOBAL_PRESET_COMFORT,
    GLOBAL_PRESET_ECO,
    GLOBAL_PRESET_MANUAL,
    GLOBAL_PRESET_SLEEP,
    HEAT_SOURCE_PRIORITIES,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    KEY_ANTI_FROST_ENABLED,
    KEY_AUTO_NIGHT_MODE,
    KEY_DEMAND_STRATEGY,
    KEY_FROST_PROTECTION_TEMP,
    KEY_HEAT_SOURCE_PRIORITY,
    KEY_MORNING_TIME,
    KEY_NIGHT_TIME,
    KEY_PRE_AWAY_PRESET,
    KEY_PRE_NIGHT_PRESET,
    KEY_WEATHER_CURVE,
    ZONE_MODE_BYPASS,
    ZONE_MODE_PRIMARY,
    ZONE_MODE_SECONDARY,
    make_zone_entity_id,
)
from custom_components.multizone_thermostat.cooling_policy import CoolingPolicy
from custom_components.multizone_thermostat.demand_aggregator import DemandAggregator
from custom_components.multizone_thermostat.energy.energy_manager import EnergyManager
from custom_components.multizone_thermostat.pid import PID
from custom_components.multizone_thermostat.pid_wrapper import MultizonePID
from custom_components.multizone_thermostat.plant_diagnostics.anomalies import evaluate_zone_anomalies
from custom_components.multizone_thermostat.plant_diagnostics.const import (
    ANOMALY_LOW_BATTERY,
    ANOMALY_NONE,
    ANOMALY_SENSOR_FAULT,
    ANOMALY_SENSOR_TIMEOUT,
)
from custom_components.multizone_thermostat.plant_diagnostics.engine import PlantDiagnosticsEngine
from custom_components.multizone_thermostat.pwm_engine import PWMEngine
from custom_components.multizone_thermostat.routine_manager import RoutineManager
from custom_components.multizone_thermostat.safety.frost import FrostManager
from custom_components.multizone_thermostat.schedule.manager import ScheduleProfileManager
from custom_components.multizone_thermostat.schedule.slot_engine import ScheduleSlotEngine
from custom_components.multizone_thermostat.schedule.smart_return import SmartReturnPlanner
from custom_components.multizone_thermostat.schedule.storage import ScheduleProfileStorage
from custom_components.multizone_thermostat.select import (
    MultizoneDemandStrategySelect,
    MultizoneHeatSourcePrioritySelect,
    MultizoneMasterOperationModeSelect,
    MultizoneScheduleProfileSelect,
    MultizoneZoneSelect,
)
from custom_components.multizone_thermostat.thermal_model import ThermalObserver
from custom_components.multizone_thermostat.zone_controller import ZoneController


# ---------------------------------------------------------------------------
# 1. PID & MultizonePID fixes
# ---------------------------------------------------------------------------

def test_pid_sample2_throttle_and_conditional_anti_windup():
    """Sample 2 respects sampling_period; saturated P freezes positive I without inverting sign."""
    pid = PID(kp=50.0, ki=1.0, kd=0.0, out_min=0.0, out_max=100.0, sampling_period=60.0)
    t = [1000.0]
    with patch("custom_components.multizone_thermostat.pid.monotonic", side_effect=lambda: t[0]):
        out1, updated1 = pid.calc(input_val=15.0, set_point=20.0)
        assert updated1 is True
        assert out1 == 100.0
        # P=250 >= 100 -> integral frozen at 0 (no windup, never inverted negative!)
        assert pid.integral == 0.0

        # Sample 2 only 10s later (< 60s sampling_period) MUST be throttled!
        t[0] = 1010.0
        out2, updated2 = pid.calc(input_val=16.0, set_point=20.0)
        assert updated2 is False
        assert out2 == out1

        # Later when P=40 and positive I=80 overflows 100, back-calc trims I to 60 without going negative
        t[0] = 1080.0
        pid.integral = 80.0
        out3, updated3 = pid.calc(input_val=19.2, set_point=20.0)
        assert updated3 is True
        assert out3 == pytest.approx(100.0)
        assert 0.0 <= pid.integral <= 65.0


def test_pid_wrapper_clear_samples_and_dead_sensor_timeout():
    """clear_samples() keeps dead-sensor timer unless reset requested; timeout resets PID state."""
    wrapper = MultizonePID(kp=50.0, ki=0.5, kd=0.0, sensor_timeout=600.0, zone_id="climate.living")
    with patch("time.monotonic", return_value=1000.0):
        wrapper.update_sensor_timestamp()
        wrapper.calc(19.0, 20.0)

    with patch("time.monotonic", return_value=1500.0):
        wrapper.calc(19.0, 20.0)
        assert wrapper._pid.integral > 0.0
        wrapper.clear_samples(reset_sensor_timer=False)
        assert wrapper.last_sensor_update == 1000.0
        assert wrapper._pid.integral == 0.0

    # At t=1700 (>600s since 1000), timeout triggers and clears integral & _last_input_time
    wrapper._pid.integral = 25.0
    wrapper._last_input_time = 1500.0
    with patch("time.monotonic", return_value=1700.0):
        demand = wrapper.calc(19.0, 20.0)
        assert demand == 0.0
        assert wrapper._pid.integral == 0.0
        assert wrapper._last_input_time is None


# ---------------------------------------------------------------------------
# 2. Autotune fixes
# ---------------------------------------------------------------------------

def test_autotune_seed_uppercase_keys_and_t0_clamp():
    """seed_learned_pid keys match _compute_final_pid; _analyze_reaction_curve clamps t0."""
    observer = PassiveAutotuneObserver("Living", required_cycles=3, mode="heat")
    observer.seed_learned_pid(kp=40.0, ki=0.05, kd=100.0)
    assert all("Kp" in c and "Ki" in c and "Kd" in c for c in observer.completed_cycles)

    # Also verifies defensive fallback on legacy lowercase cycle dicts
    observer.completed_cycles.append({"kp": 40.0, "ki": 0.05, "kd": 100.0})
    observer._compute_final_pid()
    assert observer._learned_kp == pytest.approx(40.0)

    # Verify t0 clamped <= max_slope_t when initial droop puts max_slope_temp < start_temp
    observer_fresh = PassiveAutotuneObserver("Living", required_cycles=1, mode="heat")
    history = [
        (0.0, 20.5),
        (100.0, 19.5),
        (200.0, 19.6),
        (380.0, 20.2),
        (500.0, 20.4),
    ]
    res = observer_fresh._analyze_reaction_curve(history, start_time=0.0, start_temp=20.5)
    assert res is not None and res["Kp"] > 0
    # max_slope_t for (200, 19.6)->(380, 20.2) is 290.0; unclamped t0 would be 470.0 -> clamped to 290.0
    assert res["L"] == pytest.approx(290.0)


def test_pid_autotune_incremental_peaks_and_asymmetrical_step():
    """PIDAutotune retains peak history, uses maxlen>=3, and computes asymmetrical _Ku properly."""
    tuner = PIDAutotune(out_step=50.0, lookback=10.0, out_min=0.0, out_max=100.0, noiseband=0.2)
    tuner._sampletime = 20.0  # sampletime > lookback -> must still yield maxlen >= 3
    tuner._inputs = __import__("collections").deque(maxlen=max(3, round(tuner._lookback / tuner._sampletime)))
    tuner._inputs_timestamps = __import__("collections").deque(maxlen=tuner._inputs.maxlen)
    assert tuner._inputs.maxlen == 3

    # Run a steady triangle wave oscillating +/-1.0 around 20.0 with dt=20s
    import math
    converged = False
    for i in range(60):
        now = 1000.0 + i * 20.0
        # Period = 160s (8 samples) so peaks repeat consistently every 4 samples
        val = 20.0 + math.sin(2.0 * math.pi * i / 8.0)
        if tuner.run(val, 20.0, now=now):
            converged = True
            break

    assert converged is True
    assert tuner.state == PIDAutotune.STATE_SUCCEEDED
    # Step amplitude with out_min=0, out_max=100, initial=0, step=50 is 0.5*(50-0) = 25 (NOT 50!)
    expected_ku = 4.0 * 25.0 / (tuner._induced_amplitude * math.pi)
    assert tuner._Ku == pytest.approx(expected_ku, rel=1e-4)


# ---------------------------------------------------------------------------
# 3. ThermalObserver & CoolingPolicy fixes
# ---------------------------------------------------------------------------

def test_thermal_observer_cool_rate_low_demand_inertia_and_weather_multiplier():
    """ThermalObserver learns active_cooling_rate, clears _shutdown_time on resume, normalizes Ke."""
    obs = ThermalObserver("climate.studio", temp_delta_threshold=0.1)
    assert obs.get_weather_multiplier(0.0) == 0.0

    t = [1000.0]
    with patch("time.monotonic", side_effect=lambda: t[0]):
        # Cool mode learns active_cooling_rate
        obs.update(25.0, is_heating=False, hvac_mode="cool", demand=100.0)
        t[0] += 1800.0  # 0.5 hr
        obs.update(24.0, is_heating=False, hvac_mode="cool", demand=100.0)
        assert obs.active_cooling_rate == pytest.approx(2.0, abs=0.05)

        dumped = obs.dump_state()
        assert dumped["active_cooling_rate"] == pytest.approx(2.0, abs=0.05)

        # Heat mode: demand < 10% starts inertia shutdown tracking; resuming clears _shutdown_time
        obs.update(19.0, is_heating=True, hvac_mode="heat", demand=80.0)
        t[0] += 60.0
        obs.update(19.2, is_heating=True, hvac_mode="heat", demand=5.0)
        assert obs._shutdown_time is not None
        t[0] += 60.0
        obs.update(19.3, is_heating=True, hvac_mode="heat", demand=60.0)
        assert obs._shutdown_time is None

    # Normalized around 0.15 baseline: cooling=0.15, heating=1.0 -> adaptive=0.15 -> bend=1.0
    obs.heating_rate = 1.0
    obs.cooling_rate = 0.15
    assert obs.get_weather_multiplier(2.0) == pytest.approx(2.0)

    coord = MagicMock()
    coord.schedule_manager = None
    coord.zone_controller.thermal_models = {"climate.studio": obs}
    policy = CoolingPolicy(coord)
    assert policy.get_zone_cooling_rate("climate.studio") == pytest.approx(obs.active_cooling_rate)


# ---------------------------------------------------------------------------
# 4. PWMEngine fixes
# ---------------------------------------------------------------------------

def test_pwm_engine_fixes():
    """PWMEngine advances cycle at 99%, zeroes trickle demand, holds OFF phase proportional floor."""
    t = [1000.0]
    with patch("time.monotonic", side_effect=lambda: t[0]):
        pwm = PWMEngine(pwm_interval=900.0, min_on=300.0, min_off=180.0)

        # Trickle demand: (100 * 300 / 3600) * 0.25 = 2.083% -> 1.0% zeroed out
        assert pwm.calculate(1.0) is False

        # Continuous >= 99% advances cycle_start_time past pwm_interval
        assert pwm.calculate(100.0) is True
        t[0] = 2000.0
        assert pwm.calculate(99.5) is True
        assert pwm.cycle_start_time == 2000.0

        # Anti-phase-jump floor during OFF phase
        pwm2 = PWMEngine(pwm_interval=900.0, min_on=0.0, min_off=0.0)
        pwm2.cycle_start_time = 1000.0
        t[0] = 1000.0
        assert pwm2.calculate(50.0) is True  # time_on = 450
        t[0] = 1460.0
        assert pwm2.calculate(50.0) is False  # enters OFF phase, _last_cycle_on=450
        # Demand bumps to 60% -> required cycle = 450/0.6 = 750s; t_passed=500 < 750 -> stays OFF!
        t[0] = 1500.0
        assert pwm2.calculate(60.0) is False


# ---------------------------------------------------------------------------
# 5. ZoneController & DemandAggregator fixes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_zone_controller_timeout_nan_cleanup_weather_gate_and_cool_observer():
    """ZoneController honors per-zone timeout, rejects NaN, cleans OFF state, feeds COOL thermal model."""
    hass = MagicMock()
    hass.config = SimpleNamespace(units=SimpleNamespace(temperature_unit=UnitOfTemperature.CELSIUS))
    hass.states = MagicMock()
    hass.states.get = MagicMock(return_value=None)

    coord = MagicMock()
    coord.hass = hass
    cid = make_zone_entity_id("Salone")
    coord.zones = [{CONF_ZONE_NAME: "Salone", CONF_ZONE_SENSOR_TIMEOUT: 15}]
    coord.zone_manager.get_zone_mode.return_value = ZONE_MODE_PRIMARY
    coord.demand_aggregator = MagicMock()
    coord.demand_aggregator.get_zone_demand.return_value = 0.0
    coord.plant_diagnostics.has_critical_sensor_fault.return_value = False
    coord.is_dhw_active = False
    coord.is_modulating_plant = False
    coord.enable_heat_pump = False
    coord.heat_pump_cooling = False
    coord.split_manager = MagicMock()
    coord.split_manager.has_split.return_value = False
    coord.weather_sensor_id = "weather.home"
    coord.get_persistent_data.return_value = 0.0
    coord.storage = None
    coord._climate_entities = {}

    zc = ZoneController(hass, coord)
    assert zc.pids[cid].sensor_timeout == pytest.approx(900.0)

    # NaN temperature -> forced 0.0 safely
    nan_st = MagicMock(state="heat", attributes={"current_temperature": float("nan"), "temperature": 21.0})
    assert await zc.async_update_zone(cid, nan_st) == 0.0

    # Active learning gets cleaned on HVACMode.OFF
    zc._autotuners_heat[cid].state = zc._autotuners_heat[cid].STATE_HEATING
    zc.pids[cid]._pid.integral = 40.0
    off_st = MagicMock(state="off", attributes={"current_temperature": 20.0, "temperature": 21.0})
    assert await zc.async_update_zone(cid, off_st) == 0.0
    assert zc.pids[cid]._pid.integral == 0.0

    # Weather curve 0.0 must never touch weather sensor
    hass.states.get.reset_mock()
    zc._autotuners_heat[cid].state = zc._autotuners_heat[cid].STATE_COMPLETED
    heat_st = MagicMock(state="heat", attributes={"current_temperature": 19.0, "temperature": 21.0})
    await zc.async_update_zone(cid, heat_st)
    for call in hass.states.get.call_args_list:
        assert call.args[0] != "weather.home"

    # COOL mode updates ThermalObserver (learns active_cooling_rate)
    coord.split_manager.has_split.return_value = True
    cool_st1 = MagicMock(state="cool", attributes={"current_temperature": 26.0, "temperature": 23.0})
    cool_st2 = MagicMock(state="cool", attributes={"current_temperature": 24.5, "temperature": 23.0})
    t = [1000.0]
    with patch("time.monotonic", side_effect=lambda: t[0]):
        await zc.async_update_zone(cid, cool_st1)
        t[0] = 4600.0
        await zc.async_update_zone(cid, cool_st2)
    assert zc.thermal_models[cid].active_cooling_rate > 0.0


def test_demand_aggregator_excludes_faulted_zones_from_weights_and_activity():
    """Faulted primary/secondary zones do not dilute weights or appear active."""
    z1 = make_zone_entity_id("Z1")
    z2 = make_zone_entity_id("Z2")
    z3 = make_zone_entity_id("Z3")
    faulted = {z1, z3}
    agg = DemandAggregator(fault_checker=lambda cid: cid in faulted)
    agg.set_zone_mode(z1, ZONE_MODE_PRIMARY)
    agg.set_zone_mode(z2, ZONE_MODE_PRIMARY)
    agg.set_zone_mode(z3, ZONE_MODE_SECONDARY)
    agg.set_zone_weight(z1, 3.0)
    agg.set_zone_weight(z2, 1.0)
    agg.set_zone_demand(z1, 100.0)
    agg.set_zone_demand(z2, 60.0)
    agg.set_zone_demand(z3, 90.0)
    agg.strategy = "weighted_average"

    res = agg.calculate([{CONF_ZONE_NAME: "Z1"}, {CONF_ZONE_NAME: "Z2"}])
    assert res.demand == pytest.approx(60.0)
    assert agg.has_active_primary_demand() is True
    assert agg.has_active_secondary_demand() is False

    faulted.add(z2)
    assert agg.has_active_primary_demand() is False


# ---------------------------------------------------------------------------
# 6. CalendarManager, CalendarParser, Climate, Select & EnergyManager fixes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_calendar_parser_bounds_and_manager_fixes():
    """CalendarParser rejects NaN/years; CalendarManager supports set_temp_override, away lock, Smart Start."""
    p_bad = parse_calendar_event("2026")
    assert p_bad["global_temperature"] is None
    p_zone_bad = parse_calendar_event("Living: nan, Kitchen: 99, Hall: 21.5")
    assert p_zone_bad["overrides"]["living"].temperature is None
    assert p_zone_bad["overrides"]["kitchen"].temperature is None
    assert p_zone_bad["overrides"]["hall"].temperature == 21.5

    coord = MagicMock()
    coord.hass = MagicMock()
    coord.zones = [{CONF_ZONE_NAME: "Living"}]
    cid = make_zone_entity_id("Living")
    coord.zone_manager = MagicMock()
    coord.zone_manager.current_global_preset = GLOBAL_PRESET_ECO
    coord.zone_manager.async_set_global_preset = AsyncMock()
    coord.zone_manager.get_preset_temperature = MagicMock(return_value=18.0)
    coord._climate_callbacks = {}
    coord._climate_entities = {}
    coord._select_entities = {}

    obs = ThermalObserver(cid)
    obs.heating_rate = 1.0
    coord.zone_controller = SimpleNamespace(thermal_models={cid: obs})
    coord._thermal_models = {}

    cal = CalendarManager(coord)
    now = datetime(2026, 11, 10, 8, 0, tzinfo=timezone.utc)
    coord.hass.states.get.return_value = SimpleNamespace(attributes={"current_temperature": 19.0})

    with patch("custom_components.multizone_thermostat.calendar_manager.dt_util") as m_dt:
        m_dt.DEFAULT_TIME_ZONE = timezone.utc
        m_dt.as_local.side_effect = lambda d: d
        m_dt.parse_datetime.side_effect = lambda s: datetime.fromisoformat(s)

        # Future event 1 at +30m is Eco (18°C, below current 19°C -> skips); Event 2 at +45m is 22°C -> Smart Start triggers!
        fut = [
            {"start": (now + timedelta(minutes=30)).isoformat(), "summary": "Living: 18"},
            {"start": (now + timedelta(minutes=45)).isoformat(), "summary": "Living: 22"},
        ]
        await cal._async_process_calendar_events([], fut, now)
        assert cal.smart_start_overrides[cid] == 22.0
        cal.set_temp_override(cid, 22.5)
        assert cal.smart_start_overrides[cid] == 22.5
        cal.clear_temp_override(cid)
        assert cid not in cal.temp_overrides

        # Overlapping event transition without preset restores prior preset
        cur1 = [{"start": (now - timedelta(minutes=10)).isoformat(), "end": (now + timedelta(hours=1)).isoformat(), "summary": "comfort"}]
        await cal._async_process_calendar_events(cur1, [], now)
        assert cal.active_global_preset == "comfort"
        cur2 = [{"start": (now - timedelta(minutes=5)).isoformat(), "end": (now + timedelta(hours=1)).isoformat(), "summary": "Living: 21"}]
        await cal._async_process_calendar_events(cur2, [], now)
        coord.zone_manager.async_set_global_preset.assert_any_call(GLOBAL_PRESET_ECO)
        assert cal.active_global_preset is None

        # Geofencing AWAY locks calendar from switching preset to comfort
        coord.zone_manager.async_set_global_preset.reset_mock()
        coord.zone_manager.current_global_preset = GLOBAL_PRESET_AWAY
        await cal._async_process_calendar_events(cur1, [], now)
        coord.zone_manager.async_set_global_preset.assert_not_called()


@pytest.mark.asyncio
async def test_climate_nan_guard_and_trv_manual_preset_protection():
    """Virtual climate rejects NaN set_temperature and routes TRV knob edits during scheduled overrides to manual."""
    hass = MagicMock()
    hass.async_create_task = MagicMock()
    coord = MagicMock()
    coord.hass = hass
    coord.get_global_preset.return_value = "eco"
    coord.calendar_manager = CalendarManager(coord)
    coord.schedule_manager = MagicMock()
    coord.schedule_manager.scheduler_enabled = True
    coord.schedule_manager.manual_overrides = {}
    coord.zone_controller = None
    coord.get_zone_mode.return_value = ZONE_MODE_PRIMARY
    hass.data = {DOMAIN: {"e1": {"coordinator": coord}}}

    def _rec(cid, temp):
        coord.schedule_manager.manual_overrides[cid] = {"target_temp": temp}

    coord.schedule_manager.record_manual_override.side_effect = _rec

    ent = MultizoneVirtualThermostat(
        hass=hass,
        entry_id="e1",
        zone_data={CONF_ZONE_NAME: "Living"},
    )
    ent.entity_id = make_zone_entity_id("Living")
    ent.async_write_ha_state = MagicMock()
    ent._trigger_trv_sync = AsyncMock()
    ent._hvac_mode = HVACMode.HEAT
    ent._target_temperature = 20.0
    ent._sync_manager = MagicMock()
    ent._sync_manager.process_trv_change = AsyncMock(return_value=(None, 1.0))

    # NaN must be ignored cleanly
    await ent.async_set_temperature(**{ATTR_TEMPERATURE: float("nan")})
    assert ent._target_temperature == 20.0

    # Simulate TRV external delta (+1.0) while scheduler is enabled
    await ent._async_on_trv_changed(Event("state_changed", {}))
    coord.zone_manager.update_preset_temperature.assert_called_with(
        GLOBAL_PRESET_MANUAL, ent.entity_id, 21.0
    )


@pytest.mark.asyncio
async def test_select_entities_safe_restore_and_validation():
    """Select entities validate profiles, preserve coordinator modes, and restore passively."""
    aggregator = DemandAggregator()
    settings = {}
    coord = MagicMock()
    coord.zones = [{CONF_ZONE_NAME: "Living"}]
    coord.demand_aggregator = aggregator
    coord._settings = settings
    coord._select_entities = {}
    coord.get_persistent_data = lambda k, d=None: settings.get(k, d)
    coord.async_set_persistent_data = AsyncMock(side_effect=lambda k, v: settings.__setitem__(k, v))
    coord.register_select = lambda k, e: coord._select_entities.__setitem__(k, e)
    coord.set_zone_mode = MagicMock()
    coord.async_set_master_hvac_mode = AsyncMock()
    coord.energy_manager = MagicMock()
    coord.energy_manager.async_set_heat_source_priority = AsyncMock()
    coord.schedule_manager = MagicMock()
    coord.schedule_manager.profiles = {"standard": {}}
    coord.schedule_manager.async_activate_profile = AsyncMock()

    # Demand strategy persists fallback HA state into storage
    ds = MultizoneDemandStrategySelect(coord, "e1")
    ds.async_get_last_state = AsyncMock(return_value=SimpleNamespace(state="sum_capped"))
    await ds.async_added_to_hass()
    assert settings[KEY_DEMAND_STRATEGY] == "sum_capped"

    # Zone mode select does not overwrite storage mode when last_state is None
    zs = MultizoneZoneSelect(coord, "e1", "Living")
    zs.async_get_last_state = AsyncMock(return_value=None)
    await zs.async_added_to_hass()
    coord.set_zone_mode.assert_not_called()

    # Invalid schedule profile option is rejected
    ps = MultizoneScheduleProfileSelect(coord, "e1")
    ps.async_write_ha_state = MagicMock()
    await ps.async_select_option("nonexistent")
    coord.schedule_manager.async_activate_profile.assert_not_called()

    # HeatSourcePriority & MasterOperationMode restore passively without calling active setters
    hs = MultizoneHeatSourcePrioritySelect(coord, "e1")
    hs.async_get_last_state = AsyncMock(return_value=SimpleNamespace(state=HEAT_SOURCE_PRIORITIES[-1]))
    await hs.async_added_to_hass()
    coord.energy_manager.async_set_heat_source_priority.assert_not_called()
    assert settings[KEY_HEAT_SOURCE_PRIORITY] == HEAT_SOURCE_PRIORITIES[-1]

    ms = MultizoneMasterOperationModeSelect(coord, "e1")
    ms.async_get_last_state = AsyncMock(return_value=SimpleNamespace(state=HVAC_MODE_COOL))
    await ms.async_added_to_hass()
    coord.async_set_master_hvac_mode.assert_not_called()
    assert settings[CONF_MASTER_HVAC_MODE] == HVAC_MODE_COOL


def test_energy_manager_readonly_diagnostics_disabled_and_saturation_import_guard():
    """EnergyManager handles None units, disabled external override, readonly diagnostics, and grid import."""
    hass = MagicMock()
    coord = MagicMock()
    states = {
        "sensor.pv": State("sensor.pv", "500", {"unit_of_measurement": None}),
        "sensor.export": State("sensor.export", "-500", {"unit_of_measurement": "W"}),
        "sensor.soc": State("sensor.soc", "98", {}),
        "binary_sensor.emhass": State("binary_sensor.emhass", "on", {}),
    }
    hass.states.get = lambda eid: states.get(eid)

    cfg = {
        "energy_management_enabled": False,
        "solar_power_sensor": "sensor.pv",
        "grid_export_sensor": "sensor.export",
        "battery_soc_sensor": "sensor.soc",
        "external_solar_override_entity": "binary_sensor.emhass",
    }
    mgr = EnergyManager(hass, coord, cfg)
    assert mgr.get_solar_power() == 500.0
    # Disabled blocks external override
    assert mgr.is_solar_surplus() is False

    mgr.enabled = True
    states["binary_sensor.emhass"] = State("binary_sensor.emhass", "off", {})
    # Grid importing (-500W < -100W) blocks battery saturation false positive!
    assert mgr.is_solar_surplus() is False

    # Readonly diagnostics does not mutate _last_surplus_state or _surplus_hold_active
    states["sensor.export"] = State("sensor.export", "1500", {"unit_of_measurement": "W"})
    mgr._last_surplus_state = False
    diag = mgr.get_diagnostics()
    assert diag["is_solar_surplus"] is True
    assert mgr._last_surplus_state is False
    assert mgr._surplus_hold_active is False


# ---------------------------------------------------------------------------
# 7. ScheduleProfileManager, SmartReturnPlanner, Storage, SlotEngine, RoutineManager fixes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scheduler_external_presets_hvac_forwarding_persistence_and_malformed_guards():
    """Scheduler respects AWAY/SLEEP/Calendar, forwards hvac_mode, persists cleared overrides, handles bad blocks."""
    hass = MagicMock()
    hass.states = MagicMock()
    hass.states.get.return_value = None
    coord = MagicMock()
    coord.hass = hass
    cid = make_zone_entity_id("Living")
    coord.zones = [{CONF_ZONE_NAME: "Living"}]
    coord.master_hvac_mode = "heat"
    coord.zone_manager = MagicMock()
    coord.zone_manager.current_global_preset = GLOBAL_PRESET_AWAY
    coord.zone_manager.get_zone_mode.return_value = ZONE_MODE_PRIMARY
    coord.zone_manager.get_preset_temperature.side_effect = (
        lambda preset, zone_id, hvac_mode="heat": 24.5 if hvac_mode == "cool" else 20.5
    )
    coord._climate_entities = {cid: SimpleNamespace(hvac_mode=HVACMode.HEAT, _hvac_mode=HVACMode.HEAT)}
    coord._select_entities = {}
    coord.routine_manager = None
    coord.calendar_manager = SimpleNamespace(active_global_preset=None)
    coord.get_persistent_data = MagicMock(side_effect=lambda k, d=None: False if k == KEY_AUTO_NIGHT_MODE else d)
    coord.async_set_persistent_data = AsyncMock()

    mgr = ScheduleProfileManager(coord)
    mgr.async_save_to_storage = AsyncMock()
    mgr.scheduler_enabled = True
    mgr.profiles["standard"] = {
        "name": "Standard",
        "baseline_preset": "eco",
        "days": {"mon": {cid: [{"start": "08:00", "end": "20:00", "preset": "comfort"}]}},
    }
    now_mon = datetime(2026, 11, 9, 10, 0, tzinfo=timezone.utc)

    # 1. Manual/external AWAY prevents weekly slot overwrite and never overwrites AWAY
    await mgr.async_evaluate_schedule(now_mon)
    assert cid not in mgr.schedule_overrides
    assert coord.zone_manager.set_global_preset.call_count == 0

    # 2. Auto-Night SLEEP prevents weekly slot overwrite
    coord.zone_manager.current_global_preset = GLOBAL_PRESET_SLEEP
    coord.get_persistent_data = MagicMock(side_effect=lambda k, d=None: True if k == KEY_AUTO_NIGHT_MODE else d)
    await mgr.async_evaluate_schedule(now_mon)
    assert cid not in mgr.schedule_overrides

    # 3. Calendar active_global_preset prevents weekly slot overwrite
    coord.zone_manager.current_global_preset = GLOBAL_PRESET_COMFORT
    coord.calendar_manager.active_global_preset = "comfort"
    await mgr.async_evaluate_schedule(now_mon)
    assert cid not in mgr.schedule_overrides

    # 4. Expired manual override triggers storage save
    coord.calendar_manager.active_global_preset = None
    mgr.manual_overrides[cid] = {
        "target_temp": 23.0,
        "until": (now_mon - timedelta(minutes=5)).isoformat(),
        "slot_id": "mon_08:00_20:00_comfort",
    }
    mgr.async_save_to_storage.reset_mock()
    await mgr.async_evaluate_schedule(now_mon)
    assert cid not in mgr.manual_overrides
    mgr.async_save_to_storage.assert_awaited()

    # 5. Smart Return planner forwards hvac_mode="cool", accepts HH:MM:SS, handles DST UTC subtraction
    assert mgr.calculate_smart_return_plan("18:30:00", preset="comfort", now=now_mon, hvac_mode="cool")[cid]["target_temp"] == 24.5

    # 6. Malformed manual override and malformed schedule block do not crash
    storage = ScheduleProfileStorage(coord)
    storage.manual_overrides[cid] = {"target_temp": float("nan"), "slot_id": "s1"}
    assert storage.get_valid_manual_override(cid, "s1", now_mon) is None
    engine = ScheduleSlotEngine()
    s_dt, e_dt = engine.parse_block_times({"start": "invalid", "end": "99:99"}, now_mon)
    assert s_dt == e_dt


@pytest.mark.asyncio
async def test_routine_manager_away_sleep_and_morning_fixes():
    """RoutineManager preserves pre_away when already away, checks AUTO_NIGHT_MODE, restores Morning only from SLEEP."""
    hass = MagicMock()
    coros = []
    hass.async_create_task = MagicMock(side_effect=lambda c: coros.append(c) or MagicMock())
    saved = {}
    cur_preset = [GLOBAL_PRESET_AWAY]

    def get_data(k, d=None):
        if k == KEY_AUTO_NIGHT_MODE:
            return False
        if k == KEY_NIGHT_TIME:
            return "22:30"
        if k == KEY_MORNING_TIME:
            return "07:00"
        if k == KEY_PRE_AWAY_PRESET:
            return GLOBAL_PRESET_COMFORT
        return saved.get(k, d)

    async def set_data(k, v):
        saved[k] = v

    set_preset = AsyncMock()
    rm = RoutineManager(hass, "person.a", get_data, set_data, lambda: cur_preset[0], set_preset)

    # Already AWAY when presence flips to not_home -> must NOT clobber KEY_PRE_AWAY_PRESET with "away"
    ev_left = MagicMock(data={"old_state": MagicMock(state="home"), "new_state": MagicMock(state="not_home")})
    rm._async_on_presence_changed(ev_left)
    for c in coros:
        await c
    coros.clear()
    assert KEY_PRE_AWAY_PRESET not in saved

    # Return at 23:00 with AUTO_NIGHT_MODE=False -> restores pre_away (comfort), NOT sleep!
    with patch("custom_components.multizone_thermostat.routine_manager.dt_util.now", return_value=datetime(2026, 1, 1, 23, 0)):
        ev_ret = MagicMock(data={"old_state": MagicMock(state="not_home"), "new_state": MagicMock(state="home")})
        rm._async_on_presence_changed(ev_ret)
        for c in coros:
            await c
        coros.clear()
        set_preset.assert_called_with(GLOBAL_PRESET_COMFORT)

    # Morning check when already in MANUAL (user woke up early) must NOT overwrite MANUAL with pre_night!
    cur_preset[0] = GLOBAL_PRESET_MANUAL
    set_preset.reset_mock()
    rm._get_persistent_data = MagicMock(
        side_effect=lambda k, d=None: True if k == KEY_AUTO_NIGHT_MODE else ("07:00" if k == KEY_MORNING_TIME else d)
    )
    with patch("custom_components.multizone_thermostat.routine_manager.dt_util.now", return_value=datetime(2026, 1, 2, 7, 1)):
        rm._async_check_schedule(datetime(2026, 1, 2, 7, 1))
    assert len(coros) == 0


# ---------------------------------------------------------------------------
# 8. Diagnostics, PlantOrchestrator COOL diagnostics & FrostManager fixes
# ---------------------------------------------------------------------------

def test_diagnostics_low_battery_spike_throttle_bypass_and_timeout_24h():
    """Diagnostics prioritizes critical faults over low battery, throttles spikes, updates on bypass."""
    hass = MagicMock()
    hass.data = {}
    cid = make_zone_entity_id("Studio")
    now_wall = 1700000000.0
    reported = MagicMock()
    reported.timestamp.return_value = now_wall - 100000.0  # >24h silent!

    temp_st = State("sensor.studio_temp", "20.0", {"battery": 5}, last_reported=reported)
    zone_st = State(cid, "heat", {"current_temperature": 20.0, "temperature": 21.0})

    def get_st(eid):
        if eid == "sensor.studio_temp":
            return temp_st
        if eid == cid:
            return zone_st
        return None

    hass.states.get = MagicMock(side_effect=get_st)
    coord = MagicMock()
    zone_info = {"name": "Studio", "temp_sensor": "sensor.studio_temp", "sensor_timeout_min": 60, "climates": []}
    coord.zone_manager.get_zone.return_value = zone_info
    coord.zone_manager.is_passive_heat_allowed.return_value = False
    coord.get_zone_mode.return_value = "primary"
    coord.get_zone_demand.return_value = 50.0

    engine = PlantDiagnosticsEngine(coord)
    with patch("time.monotonic", return_value=1000.0), patch("time.time", return_value=now_wall):
        a_type, _ = evaluate_zone_anomalies(coordinator=coord, hass=hass, climate_id=cid, state=engine._zone_anomaly_state.setdefault(cid, {}), boiler_on=True)
        # Critical >24h timeout wins over low battery AND has_critical_sensor_fault is True without TRV fallback
        assert a_type == ANOMALY_SENSOR_TIMEOUT
        assert engine.has_critical_sensor_fault(cid) is True

    # Low battery alone is non-critical
    reported.timestamp.return_value = now_wall - 60.0
    with patch("time.monotonic", return_value=1010.0), patch("time.time", return_value=now_wall):
        a_type2, _ = evaluate_zone_anomalies(coord, hass, cid, engine._zone_anomaly_state[cid], boiler_on=True)
        assert a_type2 == ANOMALY_LOW_BATTERY
        assert engine.has_critical_sensor_fault(cid) is False

    # Bypass mode still updates last_temp_seen; same-tick spikes (<1s) don't increment past 1
    temp_st = State("sensor.studio_temp", "22.5", {}, last_reported=reported)
    zone_st = State(cid, "heat", {"current_temperature": 22.5, "temperature": 21.0})
    coord.get_zone_mode.return_value = "bypass"
    engine._zone_anomaly_state[cid]["last_temp_seen"] = 20.0
    engine._zone_anomaly_state[cid]["last_temp_time"] = 500.0
    with patch("time.monotonic", return_value=1020.0), patch("time.time", return_value=now_wall):
        evaluate_zone_anomalies(coord, hass, cid, engine._zone_anomaly_state[cid], boiler_on=True)
        assert engine._zone_anomaly_state[cid]["last_temp_seen"] == 22.5

    # Same-tick rapid spikes do not accept an un-sustained spike in <1s
    coord.get_zone_mode.return_value = "primary"
    zone_st = State(cid, "heat", {"current_temperature": 31.0, "temperature": 21.0})
    temp_st = State("sensor.studio_temp", "31.0", {}, last_reported=reported)
    with patch("time.monotonic", return_value=1025.0), patch("time.time", return_value=now_wall):
        a1, _ = evaluate_zone_anomalies(coord, hass, cid, engine._zone_anomaly_state[cid], boiler_on=True)
        assert a1 == ANOMALY_SENSOR_FAULT
    with patch("time.monotonic", return_value=1025.2), patch("time.time", return_value=now_wall):
        a2, _ = evaluate_zone_anomalies(coord, hass, cid, engine._zone_anomaly_state[cid], boiler_on=True)
        assert a2 == ANOMALY_SENSOR_FAULT
    with patch("time.monotonic", return_value=1025.4), patch("time.time", return_value=now_wall):
        a3, _ = evaluate_zone_anomalies(coord, hass, cid, engine._zone_anomaly_state[cid], boiler_on=True)
        assert a3 == ANOMALY_SENSOR_FAULT
        assert engine._zone_anomaly_state[cid]["spike_count"] == 1


@pytest.mark.asyncio
async def test_orchestrator_cool_runs_diagnostics_and_skips_faulted_zones():
    """PlantOrchestrator runs evaluate_zone_anomalies before COOL and excludes faulted zones."""
    hass = MagicMock()
    hass.states = MagicMock()
    hass.states.get.return_value = None
    coord = MagicMock()
    coord.hass = hass
    cid = make_zone_entity_id("Living")
    coord.zones = [{CONF_ZONE_NAME: "Living"}]
    coord.get_master_state.return_value = True
    coord.master_hvac_mode = HVAC_MODE_COOL
    coord.enable_heat_pump = True
    coord.heat_pump_cooling = True
    coord.get_zone_mode.return_value = ZONE_MODE_PRIMARY
    coord.demand_aggregator = DemandAggregator()
    coord.demand_aggregator.set_zone_demand(cid, 80.0)
    coord.frost_manager = None
    coord.is_zone_in_frost_emergency = None
    coord._climate_entities = {
        cid: SimpleNamespace(hvac_mode=HVAC_MODE_COOL, current_temperature=28.0, target_temperature=23.0)
    }
    coord.plant_diagnostics.evaluate_zone_anomalies = MagicMock(return_value=(ANOMALY_SENSOR_FAULT, "fault"))
    coord.plant_diagnostics.has_critical_sensor_fault = MagicMock(return_value=True)

    hp = MagicMock()
    hp.async_update = AsyncMock()
    orch = PlantOrchestrator(hass, coord.demand_aggregator, None, coord, heat_pump_backend=hp)
    orch._async_refresh_zones_proactively = AsyncMock()

    await orch._async_update_boiler()
    coord.plant_diagnostics.evaluate_zone_anomalies.assert_called_with(cid)
    hp.async_update.assert_awaited_with(0.0, None, False, hvac_mode=HVAC_MODE_COOL)


@pytest.mark.asyncio
async def test_frost_manager_restores_mode_and_preserves_low_target():
    """FrostManager guards None plant_diagnostics, restores OFF/COOL mode, preserves <= frost_target."""
    hass = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    cid = make_zone_entity_id("Garage")
    states = {cid: State(cid, HVAC_MODE_OFF, {"current_temperature": 3.0, "temperature": 5.0})}
    hass.states.get = lambda eid: states.get(eid)

    store = {KEY_ANTI_FROST_ENABLED: True, KEY_FROST_PROTECTION_TEMP: 7.0}
    coord = MagicMock()
    coord.zones = [{CONF_ZONE_NAME: "Garage"}]
    coord.plant_diagnostics = None
    coord.weather_sensor_id = None
    coord._settings = store
    coord.get_persistent_data = lambda k, d=None: store.get(k, d)
    coord.async_set_persistent_data = AsyncMock(side_effect=lambda k, v: store.update({k: v}))
    coord._async_set_hvac_mode = AsyncMock()

    fm = FrostManager(hass, coord)
    assert await fm.async_handle_frost_emergencies() is True
    coord._async_set_hvac_mode.assert_any_call(cid, HVAC_MODE_HEAT)
    assert fm._pre_frost_targets[cid] == 5.0
    assert fm._pre_frost_modes[cid] == HVAC_MODE_OFF

    # Recovery warms > 8.5°C -> restores 5.0°C target and OFF mode
    coord._async_set_hvac_mode.reset_mock()
    hass.services.async_call.reset_mock()
    states[cid] = State(cid, HVAC_MODE_HEAT, {"current_temperature": 10.0, "temperature": 10.0})
    assert await fm.async_handle_frost_emergencies() is False
    coord._async_set_hvac_mode.assert_called_with(cid, HVAC_MODE_OFF)
    hass.services.async_call.assert_called_with(
        "climate",
        "set_temperature",
        {"entity_id": cid, "temperature": 5.0},
        blocking=False,
    )
