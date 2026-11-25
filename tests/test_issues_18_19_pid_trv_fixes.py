"""Regression tests for GitHub Issues #18 & #19 plus fork PID/switch reliability fixes (beta)."""
from __future__ import annotations

import math
import random
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.components.climate import HVACMode
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)

from custom_components.multizone_thermostat.autotune import PassiveAutotuneObserver
from custom_components.multizone_thermostat.const import (
    CONF_ZONES,
    CONF_ZONE_NAME,
    CONF_ZONE_TEMP_SENSOR,
    DOMAIN,
    TRV_CALIB_MODE_AUTO,
    TRV_CALIB_MODE_DISABLED,
    TRV_CONTROL_MODE_DEMAND_DRIVEN,
    make_zone_entity_id,
)
from custom_components.multizone_thermostat.coordinator import MultizoneCoordinator
from custom_components.multizone_thermostat.diagnostics import async_get_config_entry_diagnostics
from custom_components.multizone_thermostat.pid import PID
from custom_components.multizone_thermostat.pid_wrapper import MultizonePID
from custom_components.multizone_thermostat.sync_manager import ZoneSyncManager
from custom_components.multizone_thermostat.zone_controller import ZoneController


# ---------------------------------------------------------------------------
# 1. PID Least-Squares Derivative, Quantization Immunity & Setpoint/NaN Rules
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
        temp = 18.0 + 0.02 * i  # +1.2 C/h ramp
        pid.calc(temp, 20.0, input_time=t, last_input_time=prev_t)
    assert -15.0 <= pid.derivative < 0.0
    assert len(pid._history) > 0

    pid.clear_samples()
    assert len(pid._history) == 0
    assert pid.derivative == 0.0


def test_pid_nan_holds_current_output_and_setpoint_rise_preserves_integral():
    """Alkis PID-005 (NaN holds _output) & PID-003 (warm-up rise preserves integral; drop resets)."""
    pid = PID(kp=10.0, ki=0.05, kd=0.0, out_min=0.0, out_max=100.0)
    out1, up1 = pid.calc(19.0, 20.0, input_time=0.0, last_input_time=None)
    assert up1 is True
    out2, up2 = pid.calc(19.0, 20.0, input_time=60.0, last_input_time=0.0)
    assert up2 is True and out2 > out1

    # NaN must return held current output (out2), NOT stale _last_output (out1)
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


# ---------------------------------------------------------------------------
# 2. PID Diagnostics Breakdown (Issue #19 Feature Request)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pid_diagnostics_breakdown_and_saturation_raw_output():
    """Expose P/I/D contributions, integral accumulator, raw output, clamped output, error, target, dt."""
    wrapper = MultizonePID(kp=50.0, ki=0.5, kd=0.0, out_min=0.0, out_max=100.0, zone_id="climate.cucina")
    with patch("time.monotonic", return_value=1000.0):
        wrapper.update_sensor_timestamp()
        wrapper.calc(19.5, 20.0)  # P = 25.0, I = 0.0

    with patch("time.monotonic", return_value=1200.0):
        wrapper.update_sensor_timestamp()
        # error = 0.5 -> P = 25.0, delta_i = 0.5*0.5*200 = +50.0 -> total 75.0 (unsaturated)
        wrapper.calc(19.5, 20.0)

    diag_unsat = wrapper.get_diagnostics()
    assert diag_unsat["p_contribution"] == pytest.approx(25.0)
    assert diag_unsat["i_contribution"] == pytest.approx(50.0)
    assert diag_unsat["integral_accumulator"] == pytest.approx(50.0)
    assert diag_unsat["d_contribution"] == pytest.approx(0.0)
    assert diag_unsat["pid_raw_output"] == pytest.approx(75.0)
    assert diag_unsat["pid_clamped_output"] == pytest.approx(75.0)
    assert diag_unsat["pid_error"] == pytest.approx(0.5)
    assert diag_unsat["pid_target"] == pytest.approx(20.0)
    assert diag_unsat["dt_seconds"] == pytest.approx(200.0)

    # Saturate: error = 2.0 -> P = 100.0, previous I = 50.0 -> raw > 100 while clamped == 100
    with patch("time.monotonic", return_value=1260.0):
        wrapper.update_sensor_timestamp()
        wrapper.calc(18.0, 20.0)

    diag_sat = wrapper.get_diagnostics()
    assert diag_sat["pid_raw_output"] > 100.0
    assert diag_sat["pid_clamped_output"] == pytest.approx(100.0)

    # Cooling target sign should remain positive in diagnostics
    cool_wrapper = MultizonePID(kp=20.0, ki=0.0, kd=0.0, zone_id="climate.salotto", action="cool")
    with patch("time.monotonic", return_value=2000.0):
        cool_wrapper.update_sensor_timestamp()
        cool_wrapper.calc(26.0, 24.0)
    assert cool_wrapper.get_diagnostics()["pid_target"] == pytest.approx(24.0)
    assert cool_wrapper.get_diagnostics()["p_contribution"] == pytest.approx(40.0)

    # Full diagnostics integration
    hass = MagicMock()
    hass.states.get.return_value = None
    entry = MagicMock()
    entry.entry_id = "diag_pid_entry"
    entry.version = 1
    entry.domain = DOMAIN
    entry.title = "Diag Test"
    entry.data = {CONF_ZONES: [{CONF_ZONE_NAME: "Cucina", CONF_ZONE_TEMP_SENSOR: "sensor.t_cucina"}]}
    entry.options = {}
    coord = MultizoneCoordinator(hass, entry)
    coord.zone_controller = ZoneController(hass, coord)
    coord._pids = coord.zone_controller.pids
    hass.data = {DOMAIN: {entry.entry_id: {"coordinator": coord}}}

    result = await async_get_config_entry_diagnostics(hass, entry)
    cid = make_zone_entity_id("Cucina")
    zone_diag = result["zones"][cid]
    assert "pid_state" in zone_diag
    assert "pid_state_cool" in zone_diag
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
    tuner = PassiveAutotuneObserver("Cucina", required_cycles=3, mode="heat")

    # Cycle 1: anomalous fast start -> dead time collapses to L=60s, steep initial slope
    fast_hist = [
        (0.0, 19.0),
        (60.0, 19.01),
        (180.0, 19.5),
        (300.0, 20.0),
        (420.0, 20.5),
    ]
    res_fast = tuner._analyze_reaction_curve(fast_hist, start_time=0.0, start_temp=19.0)
    assert res_fast is not None
    # Even a single L=60s cycle must obey Ti >= 900s, Ki <= 0.15, Kd <= 500
    assert res_fast["Ki"] <= 0.15
    assert res_fast["Kd"] <= 500.0
    tuner.completed_cycles.append(res_fast)

    # Cycles 2 & 3: normal slow radiator cycles (~45-50 min dead time)
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
    # Coherent FOPDT from median (L, slope): Ti_eff = Kp / Ki >= 900s, Td_eff = Kd / Kp <= 60s
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
    coord.get_zone_mode.return_value = "primary"
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

    number_calls = [c for c in hass.services.async_call.call_args_list if c.args[0] == "number"]
    assert number_calls == []
    # Demand-driven bounded overdrive still sets boosted target (eff_room 19.5 + 1.5 = 21.0)
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
        # 1. Zero delta & calib == 0.0 must NEVER spam set_value(0.0)
        await mgr.async_sync_trvs(HVACMode.HEAT, 21.0, 20.0, False, True, zone_demand=60.0)
        assert [c for c in hass.services.async_call.call_args_list if c.args[0] == "number"] == []

        # 2. Small delta (< 0.25 C deadband) must NOT write offset
        await mgr.async_sync_trvs(HVACMode.HEAT, 21.0, 20.15, False, True, zone_demand=60.0)
        assert [c for c in hass.services.async_call.call_args_list if c.args[0] == "number"] == []

        # 3. Real skew (+0.8 C): first write sends 0.8
        await mgr.async_sync_trvs(HVACMode.HEAT, 21.0, 20.8, False, True, zone_demand=60.0)
        num_calls = [c for c in hass.services.async_call.call_args_list if c.args[0] == "number"]
        assert len(num_calls) == 1
        assert num_calls[0].args[2]["value"] == pytest.approx(0.8)
        calib_st.state = "0.8"

        # 4. 10s demand_driven ticks before 180s cooldown: blocked (even if TRV drifts slightly)
        hass.services.async_call.reset_mock()
        clock["now"] = 1010.0
        trv_st.attributes["current_temperature"] = 19.9  # natural drift
        await mgr.async_sync_trvs(HVACMode.HEAT, 21.0, 20.8, False, True, zone_demand=60.0)
        assert [c for c in hass.services.async_call.call_args_list if c.args[0] == "number"] == []

        # 5. At 200s (< 300s settle window): base remains 0.0, no double-stacking onto 0.8
        clock["now"] = 1200.0
        trv_st.attributes["current_temperature"] = 20.0
        await mgr.async_sync_trvs(HVACMode.HEAT, 21.0, 20.8, False, True, zone_demand=60.0)
        for c in hass.services.async_call.call_args_list:
            if c.args[0] == "number":
                assert c.args[2]["value"] == pytest.approx(0.8)

        # 6. First settle expires at +310s (t=1310) without TRV responding -> cnt=1, writes 1.6
        hass.services.async_call.reset_mock()
        clock["now"] = 1310.0
        await mgr.async_sync_trvs(HVACMode.HEAT, 21.0, 20.8, False, True, zone_demand=60.0)
        num_calls = [c for c in hass.services.async_call.call_args_list if c.args[0] == "number"]
        assert len(num_calls) == 1
        assert num_calls[0].args[2]["value"] == pytest.approx(1.6)
        calib_st.state = "1.6"

        # 7. Second settle expires at +310s (t=1620) still unresponsive -> cnt=2 -> STALLED!
        hass.services.async_call.reset_mock()
        clock["now"] = 1620.0
        await mgr.async_sync_trvs(HVACMode.HEAT, 21.0, 20.8, False, True, zone_demand=60.0)
        assert mgr._offset_stalled["climate.eve_thermo"] is True
        assert mgr.trv_health["climate.eve_thermo"]["offset_stalled"] is True
        assert [c for c in hass.services.async_call.call_args_list if c.args[0] == "number"] == []

        # 8. Manual user reset of offset back to 0.0 clears the stall
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
    coord.get_zone_mode.return_value = "primary"
    coord.get_zone_demand.return_value = 100.0
    coord.enable_heat_pump = False

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

    # Level-triggered resync: switch recovered from unavailable -> "off" while pwm already True
    hass.services.async_call.reset_mock()
    states["switch.mqtt_valve"].state = "off"
    changed = await sm.async_pwm_tick(HVACMode.HEAT)
    assert changed is False  # edge state did not change
    hass.services.async_call.assert_any_call(
        "switch", SERVICE_TURN_ON, {ATTR_ENTITY_ID: "switch.mqtt_valve"}, context=sm._internal_context
    )

    # Valve in STATE_UNKNOWN must be commanded
    hass.services.async_call.reset_mock()
    await sm.async_sync_proportional_valves(HVACMode.HEAT)
    hass.services.async_call.assert_any_call(
        "valve",
        "set_valve_position",
        {ATTR_ENTITY_ID: "valve.prop_1", "position": 100},
        context=sm._internal_context,
    )
