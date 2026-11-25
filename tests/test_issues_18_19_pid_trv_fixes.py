"""Regression tests for GitHub Issues #18 & #19 plus fork PID/switch reliability fixes (master)."""
from __future__ import annotations

import math
import random
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.components.climate import HVACMode
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    SERVICE_TURN_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)

from custom_components.multizone_thermostat.autotune import PassiveAutotuneObserver
from custom_components.multizone_thermostat.const import (
    CONF_ZONES,
    CONF_ZONE_NAME,
    CONF_ZONE_TEMP_SENSOR,
    DOMAIN,
    KEY_WEATHER_CURVE,
    MODE_OPENTHERM,
    TRV_CALIB_MODE_AUTO,
    TRV_CALIB_MODE_DISABLED,
    TRV_CONTROL_MODE_DEMAND_DRIVEN,
    ZONE_MODE_PRIMARY,
    make_zone_entity_id,
)
from custom_components.multizone_thermostat.coordinator import MultizoneCoordinator
from custom_components.multizone_thermostat.diagnostics import async_get_config_entry_diagnostics
from custom_components.multizone_thermostat.pid import PID
from custom_components.multizone_thermostat.pid_wrapper import MultizonePID
from custom_components.multizone_thermostat.sync_manager import ZoneSyncManager
from custom_components.multizone_thermostat.thermal_model import ThermalObserver
from custom_components.multizone_thermostat.zone_controller import ZoneController


# ---------------------------------------------------------------------------
# 1. PID Least-Squares Derivative, Anti-Windup, Quantization Immunity & Alkis Fixes
# ---------------------------------------------------------------------------


def test_pid_least_squares_derivative_immune_to_quantization_flicker():
    """Alkis PID-001 + quantization guard: 0.1 C sensor flicker produces D == 0 even at Kd=60000."""
    rng = random.Random(7)
    pid = PID(kp=0.0, ki=0.0, kd=60000.0, out_min=0.0, out_max=100.0)
    d_values = []
    for i in range(300):
        t = i * 60.0
        prev_t = (i - 1) * 60.0 if i > 0 else None
        temp = 20.0 + rng.choice((0.0, 0.1))
        pid.calc(temp, 20.0, input_time=t, last_input_time=prev_t)
        d_values.append(abs(pid.derivative))
    assert max(d_values) == 0.0


def test_pid_least_squares_derivative_opposes_real_ramp_and_clears():
    """Real heating ramp produces negative braking D clamped to [-15, +15]; clear_samples empties history."""
    pid = PID(kp=0.0, ki=0.0, kd=5000.0, out_min=0.0, out_max=100.0)
    for i in range(30):
        t = i * 60.0
        prev_t = (i - 1) * 60.0 if i > 0 else None
        temp = 18.0 + 0.02 * i
        pid.calc(temp, 20.0, input_time=t, last_input_time=prev_t)
    assert -15.0 <= pid.derivative < 0.0
    assert len(pid._history) > 0

    pid.clear_samples()
    assert len(pid._history) == 0
    assert pid.derivative == 0.0


def test_pid_nan_anti_windup_max_dt_and_setpoint_rise_preserves_integral():
    """Verify PID-005 (NaN), PID-002 (max_dt), PID-003 (setpoint rise preserves I), and back-calc anti-windup."""
    pid = PID(kp=10.0, ki=0.05, kd=0.0, out_min=0.0, out_max=100.0, max_dt=600.0)
    out1, up1 = pid.calc(19.0, 20.0, input_time=0.0, last_input_time=None)
    assert up1 is True
    out2, up2 = pid.calc(19.0, 20.0, input_time=60.0, last_input_time=0.0)
    assert up2 is True and out2 > out1

    # NaN holds current _output (out2), NOT stale _last_output (out1)
    held, up_nan = pid.calc(math.nan, 20.0, input_time=120.0, last_input_time=60.0)
    assert up_nan is False
    assert held == pytest.approx(out2)

    # Setpoint rise (+2.0 C morning warm-up) preserves learned integral
    integral_before_rise = pid.integral
    assert integral_before_rise > 0.0
    pid.calc(19.0, 22.0, input_time=120.0, last_input_time=60.0)
    assert pid.integral >= integral_before_rise

    # Setpoint drop (-3.0 C night setback) resets integral to 0.0
    pid.calc(19.0, 19.0, input_time=180.0, last_input_time=120.0)
    assert pid.integral == 0.0

    # Back-calculation anti-windup & max_dt=600s check
    pid_aw = PID(kp=50.0, ki=1.0, kd=0.0, out_min=0.0, out_max=100.0, max_dt=600.0)
    out_sat, _ = pid_aw.calc(15.0, 20.0, input_time=100.0, last_input_time=None)
    assert out_sat == 100.0
    assert pid_aw.integral == 0.0  # P=250 >= 100 -> I stays 0


# ---------------------------------------------------------------------------
# 2. PID Diagnostics Breakdown & Weather FF OpenTherm / 0.0 Fixes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pid_diagnostics_and_weather_ff_fixes():
    """Verify pid_state diagnostics breakdown + weather_curve=0 and OpenTherm FF skip."""
    wrapper = MultizonePID(kp=50.0, ki=0.5, kd=0.0, out_min=0.0, out_max=100.0, zone_id="climate.cucina")
    with patch("time.monotonic", return_value=1000.0):
        wrapper.update_sensor_timestamp()
        wrapper.calc(19.5, 20.0)
    with patch("time.monotonic", return_value=1200.0):
        wrapper.update_sensor_timestamp()
        wrapper.calc(19.5, 20.0)

    diag = wrapper.get_diagnostics()
    assert diag["p_contribution"] == pytest.approx(25.0)
    assert diag["i_contribution"] == pytest.approx(50.0)
    assert diag["integral_accumulator"] == pytest.approx(50.0)
    assert diag["d_contribution"] == pytest.approx(0.0)
    assert diag["pid_raw_output"] == pytest.approx(75.0)
    assert diag["pid_clamped_output"] == pytest.approx(75.0)
    assert diag["pid_error"] == pytest.approx(0.5)
    assert diag["pid_target"] == pytest.approx(20.0)
    assert diag["dt_seconds"] == pytest.approx(200.0)

    # ThermalObserver weather multiplier == 0.0 when curve == 0.0
    tm = ThermalObserver("climate.cucina")
    assert tm.get_weather_multiplier(0.0) == 0.0

    # OpenTherm mode skips ZoneController FF even if weather_curve > 0
    hass = MagicMock()
    hass.states.get.side_effect = lambda eid: (
        MagicMock(state="-5.0", attributes={}) if eid == "sensor.outdoor" else None
    )
    entry = MagicMock()
    entry.entry_id = "diag_pid_entry"
    entry.version = 1
    entry.domain = DOMAIN
    entry.title = "Diag Master Test"
    entry.data = {CONF_ZONES: [{CONF_ZONE_NAME: "Cucina", CONF_ZONE_TEMP_SENSOR: "sensor.t_cucina"}]}
    entry.options = {}
    coord = MultizoneCoordinator(hass, entry)
    coord.boiler_mode = MODE_OPENTHERM
    coord.weather_sensor_id = "sensor.outdoor"
    coord.set_persistent_data = MagicMock()
    coord._persistent_store = {KEY_WEATHER_CURVE: 1.5}
    coord.get_persistent_data = lambda k, d=None: coord._persistent_store.get(k, d)
    coord.zone_controller = ZoneController(hass, coord)
    coord._pids = coord.zone_controller.pids
    hass.data = {DOMAIN: {entry.entry_id: {"coordinator": coord}}}

    cid = make_zone_entity_id("Cucina")
    coord.zone_controller.get_autotuner(cid).seed_learned_pid(kp=20.0, ki=0.0, kd=0.0)
    coord.zone_controller.get_pid(cid).set_pid_param(kp=20.0, ki=0.0, kd=0.0)
    st = MagicMock(state="heat", attributes={"current_temperature": 19.0, "temperature": 20.0})
    demand = await coord.zone_controller.async_update_zone(cid, st)
    assert demand == pytest.approx(20.0)  # pure P=20%, NO +37.5% OpenTherm double-FF

    result = await async_get_config_entry_diagnostics(hass, entry)
    zone_diag = result["zones"][cid]
    assert "pid_state" in zone_diag
    for key in (
        "p_contribution",
        "i_contribution",
        "d_contribution",
        "integral_accumulator",
        "pid_raw_output",
        "pid_clamped_output",
        "pid_error",
        "pid_target",
        "dt_seconds",
    ):
        assert key in zone_diag["pid_state"]


# ---------------------------------------------------------------------------
# 3. Autotuner Cucina Regression (Issue #19 Root Cause)
# ---------------------------------------------------------------------------


def test_autotuner_median_fopdt_blocks_ki_kd_explosion():
    """One fast-start anomalous cycle (L=60s) + two normal cycles must NOT produce Ki=1.251 or Kd=36621."""
    tuner = PassiveAutotuneObserver("Cucina", required_cycles=3)

    fast_hist = [
        (0.0, 19.0),
        (60.0, 19.01),
        (180.0, 19.5),
        (300.0, 20.0),
        (420.0, 20.5),
    ]
    res_fast = tuner._analyze_reaction_curve(fast_hist, start_time=0.0, start_temp=19.0)
    assert res_fast is not None
    assert res_fast["Ki"] <= 0.15
    assert res_fast["Kd"] <= 500.0
    tuner.completed_cycles.append(res_fast)

    for _ in range(2):
        normal_hist = [
            (0.0, 18.5),
            (1500.0, 18.5),
            (3000.0, 18.52),
            (3300.0, 18.9),
            (3600.0, 19.3),
        ]
        res_norm = tuner._analyze_reaction_curve(normal_hist, start_time=0.0, start_temp=18.5)
        assert res_norm is not None
        tuner.completed_cycles.append(res_norm)

    tuner._compute_final_pid()
    assert tuner.ki <= 0.15
    assert tuner.kd <= 500.0
    assert (tuner.kp / tuner.ki) >= 900.0 - 1.0
    assert (tuner.kd / tuner.kp) <= 60.0 + 0.1


# ---------------------------------------------------------------------------
# 4. TRV Disabled Mode, Offset Spam Fix & Matter Anti-Ratchet (Issue #18)
# ---------------------------------------------------------------------------


def _make_trv_sync_mgr(*, calibration_mode=TRV_CALIB_MODE_AUTO, control_mode=TRV_CONTROL_MODE_DEMAND_DRIVEN):
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    states = {}
    hass.states.get.side_effect = lambda eid: states.get(eid)
    coord = MagicMock()
    coord.get_persistent_data.return_value = True
    coord.get_master_state.return_value = True
    coord.get_zone_mode.return_value = ZONE_MODE_PRIMARY
    coord.get_zone_demand.return_value = 60.0
    mgr = ZoneSyncManager(
        hass=hass,
        coordinator=coord,
        zone_name="Soggiorno",
        entity_id="climate.soggiorno",
        climates=["climate.eve_thermo"],
        switches=[],
        calibrations={"climate.eve_thermo": "number.eve_thermo_temperature_offset"},
        calibration_mode=calibration_mode,
        trv_control_mode=control_mode,
    )
    return mgr, hass, states


@pytest.mark.asyncio
async def test_trv_calibration_disabled_allows_demand_driven_without_offset_writes():
    """TRV_CALIB_MODE_DISABLED suppresses all offset/external pushes while bounded overdrive still works."""
    mgr, hass, states = _make_trv_sync_mgr(calibration_mode=TRV_CALIB_MODE_DISABLED)
    states["climate.eve_thermo"] = MagicMock(
        state=HVACMode.HEAT,
        attributes={ATTR_TEMPERATURE: 20.0, "current_temperature": 19.5, "min_temp": 5.0, "max_temp": 35.0},
    )
    states["number.eve_thermo_temperature_offset"] = MagicMock(
        state="0.0", attributes={"min": -2.5, "max": 2.5}
    )

    await mgr.async_sync_trvs(
        master_hvac_mode=HVACMode.HEAT,
        master_target_temp=20.0,
        master_current_temp=19.2,
        safety_fallback_active=False,
        has_external_sensor=True,
        zone_demand=60.0,
    )
    await mgr.async_external_temp_heartbeat(19.2, False, True)

    assert [c for c in hass.services.async_call.call_args_list if c.args[0] == "number"] == []
    climate_calls = [
        c for c in hass.services.async_call.call_args_list
        if c.args[0] == "climate" and c.args[1] == "set_temperature"
    ]
    assert len(climate_calls) == 1
    assert climate_calls[0].args[2]["temperature"] == pytest.approx(21.0)
    assert mgr.trv_health["climate.eve_thermo"]["ext_temp_feed_mode"] == TRV_CALIB_MODE_DISABLED


@pytest.mark.asyncio
async def test_offset_calibration_no_zero_spam_deadband_cooldown_and_matter_anti_ratchet():
    """Fix 0.0 spam, deadband, 180s cooldown, and Matter-bound unresponsive TRV anti-ratchet."""
    mgr, hass, states = _make_trv_sync_mgr(calibration_mode=TRV_CALIB_MODE_AUTO)
    trv_st = MagicMock(
        state=HVACMode.HEAT,
        attributes={ATTR_TEMPERATURE: 21.0, "current_temperature": 20.0, "min_temp": 5.0, "max_temp": 35.0},
    )
    calib_st = MagicMock(state="0.0", attributes={"min": -2.5, "max": 2.5})
    states["climate.eve_thermo"] = trv_st
    states["number.eve_thermo_temperature_offset"] = calib_st

    clock = {"now": 1000.0}
    with patch("custom_components.multizone_thermostat.sync_manager.time.monotonic", side_effect=lambda: clock["now"]):
        await mgr.async_sync_trvs(HVACMode.HEAT, 21.0, 20.0, False, True, zone_demand=60.0)
        assert [c for c in hass.services.async_call.call_args_list if c.args[0] == "number"] == []

        await mgr.async_sync_trvs(HVACMode.HEAT, 21.0, 20.15, False, True, zone_demand=60.0)
        assert [c for c in hass.services.async_call.call_args_list if c.args[0] == "number"] == []

        await mgr.async_sync_trvs(HVACMode.HEAT, 21.0, 20.8, False, True, zone_demand=60.0)
        num_calls = [c for c in hass.services.async_call.call_args_list if c.args[0] == "number"]
        assert len(num_calls) == 1
        assert num_calls[0].args[2]["value"] == pytest.approx(0.8)
        calib_st.state = "0.8"

        hass.services.async_call.reset_mock()
        clock["now"] = 1010.0
        trv_st.attributes["current_temperature"] = 19.9
        await mgr.async_sync_trvs(HVACMode.HEAT, 21.0, 20.8, False, True, zone_demand=60.0)
        assert [c for c in hass.services.async_call.call_args_list if c.args[0] == "number"] == []

        clock["now"] = 1200.0
        trv_st.attributes["current_temperature"] = 20.0
        await mgr.async_sync_trvs(HVACMode.HEAT, 21.0, 20.8, False, True, zone_demand=60.0)
        for c in hass.services.async_call.call_args_list:
            if c.args[0] == "number":
                assert c.args[2]["value"] == pytest.approx(0.8)

        hass.services.async_call.reset_mock()
        clock["now"] = 1310.0
        await mgr.async_sync_trvs(HVACMode.HEAT, 21.0, 20.8, False, True, zone_demand=60.0)
        num_calls = [c for c in hass.services.async_call.call_args_list if c.args[0] == "number"]
        assert len(num_calls) == 1
        assert num_calls[0].args[2]["value"] == pytest.approx(1.6)
        calib_st.state = "1.6"

        hass.services.async_call.reset_mock()
        clock["now"] = 1620.0
        await mgr.async_sync_trvs(HVACMode.HEAT, 21.0, 20.8, False, True, zone_demand=60.0)
        assert mgr._offset_stalled["climate.eve_thermo"] is True
        assert mgr.trv_health["climate.eve_thermo"]["offset_stalled"] is True
        assert [c for c in hass.services.async_call.call_args_list if c.args[0] == "number"] == []

        calib_st.state = "0.0"
        clock["now"] = 1650.0
        await mgr.async_sync_trvs(HVACMode.HEAT, 21.0, 20.8, False, True, zone_demand=60.0)
        assert mgr._offset_stalled["climate.eve_thermo"] is False


# ---------------------------------------------------------------------------
# 5. Alkis Fork Reliability Fix: STATE_UNKNOWN Switches/Valves & Level-Triggered Sync
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_zone_switches_and_valves_command_unknown_and_level_resync():
    """Zone switches/valves in STATE_UNKNOWN are commanded; STATE_UNAVAILABLE skipped; pwm tick level-resyncs."""
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    states = {
        "switch.mqtt_valve": MagicMock(state=STATE_UNKNOWN),
        "switch.offline_valve": MagicMock(state=STATE_UNAVAILABLE),
        "valve.prop_1": MagicMock(state=STATE_UNKNOWN, attributes={}),
    }
    hass.states.get.side_effect = lambda eid: states.get(eid)
    coord = MagicMock()
    coord.get_master_state.return_value = True
    coord.get_zone_mode.return_value = ZONE_MODE_PRIMARY
    coord.get_zone_demand.return_value = 100.0

    sm = ZoneSyncManager(
        hass=hass,
        coordinator=coord,
        zone_name="Bedroom",
        entity_id="climate.bedroom",
        climates=[],
        switches=["switch.mqtt_valve", "switch.offline_valve"],
        calibrations={},
        valves=["valve.prop_1"],
    )
    sm._local_pwm_state = True
    await sm.async_sync_switches()
    hass.services.async_call.assert_any_call(
        "switch", SERVICE_TURN_ON, {ATTR_ENTITY_ID: "switch.mqtt_valve"}, context=sm._internal_context
    )
    assert all(
        c.args[2].get(ATTR_ENTITY_ID) != "switch.offline_valve"
        for c in hass.services.async_call.call_args_list
    )

    hass.services.async_call.reset_mock()
    states["switch.mqtt_valve"].state = "off"
    changed = await sm.async_pwm_tick(HVACMode.HEAT)
    assert changed is False
    hass.services.async_call.assert_any_call(
        "switch", SERVICE_TURN_ON, {ATTR_ENTITY_ID: "switch.mqtt_valve"}, context=sm._internal_context
    )

    hass.services.async_call.reset_mock()
    await sm.async_sync_proportional_valves(HVACMode.HEAT)
    hass.services.async_call.assert_any_call(
        "valve",
        "set_valve_position",
        {ATTR_ENTITY_ID: "valve.prop_1", "position": 100},
        context=sm._internal_context,
    )
