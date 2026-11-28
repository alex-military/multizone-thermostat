"""Regression tests for SIMC autotuner, trapezoidal PID, dynamic Smart Stop, Newton k_loss, and adaptive phase-locked PWM (master)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.multizone_thermostat.autotune import PassiveAutotuneObserver
from custom_components.multizone_thermostat.boiler.relay_backend import RelayBoilerBackend
from custom_components.multizone_thermostat.const import (
    CONF_ZONES,
    CONF_ZONE_NAME,
    CONF_ZONE_TEMP_SENSOR,
    DOMAIN,
    make_zone_entity_id,
)
from custom_components.multizone_thermostat.coordinator import MultizoneCoordinator
from custom_components.multizone_thermostat.pid import PID
from custom_components.multizone_thermostat.plant_diagnostics.efficiency import get_zone_energy_class
from custom_components.multizone_thermostat.pwm_engine import PWMEngine
from custom_components.multizone_thermostat.thermal_model import ThermalObserver
from custom_components.multizone_thermostat.zone_controller import ZoneController


# ---------------------------------------------------------------------------
# 1. SIMC Autotuner & OLS Reaction Curve Slope
# ---------------------------------------------------------------------------


def test_autotuner_simc_calm_gains_and_ols_noise_resistance():
    # Typical radiator room: L=240s, R=1.8 C/h (0.0005 C/s)
    kp, ki, kd = PassiveAutotuneObserver._derive_pid_from_fopdt(240.0, 0.0005)
    # Old ZN gave 120/(0.0005*240)=1000->500; SIMC gives calm Kp ~ 238.1, Ti=3360s
    assert kp == pytest.approx(100.0 / (0.0005 * (600.0 + 240.0)), rel=1e-4)
    assert kp < 250.0
    assert ki == pytest.approx(round(kp / 3360.0, 5), rel=1e-4)
    assert kd <= 500.0

    # Quantization step / sensor jitter on reaction curve: OLS smooths across samples
    tuner = PassiveAutotuneObserver("Living", required_cycles=1)
    noisy_hist = [
        (0.0, 19.0),
        (60.0, 19.05),
        (120.0, 19.0),
        (180.0, 19.15),
        (240.0, 19.10),
        (300.0, 19.15),
        (360.0, 19.20),
        (420.0, 19.22),
        (480.0, 19.25),
    ]
    res = tuner._analyze_reaction_curve(noisy_hist, start_time=0.0, start_temp=19.0)
    assert res is not None
    # True underlying slope is ~0.0005 C/s, not inflated by single noisy pair (19.0->19.15 over 180s)
    assert res["slope"] < 0.00075


# ---------------------------------------------------------------------------
# 2. PID Trapezoidal Integration, Integral Deadband & Dynamic Smart Stop
# ---------------------------------------------------------------------------


def test_pid_trapezoidal_integration_and_deadband():
    pid = PID(kp=10.0, ki=0.1, kd=0.0, out_min=0.0, out_max=100.0)
    # Step 1: t=0, error = 1.0 -> dt=0, I=0
    pid.calc(19.0, 20.0, input_time=0.0, last_input_time=None)
    assert pid.integral == pytest.approx(0.0)

    # Step 2: t=100, error = 0.0 -> trapezoidal avg_error = 0.5 -> I = 0.1 * 0.5 * 100 = 5.0
    # (Rectangular Euler at error=0.0 would have produced 0.0)
    pid.calc(20.0, 20.0, input_time=100.0, last_input_time=0.0)
    assert pid.integral == pytest.approx(5.0)

    # Micro-noise inside +-0.03 C deadband must NOT drift the integral
    pid.calc(19.98, 20.0, input_time=200.0, last_input_time=100.0)
    assert pid.integral == pytest.approx(5.0)


@pytest.mark.asyncio
async def test_dynamic_smart_stop_zero_offset_at_steady_state_and_active_on_ramp():
    hass = MagicMock()
    hass.states = MagicMock()
    hass.states.get.return_value = None
    entry = MagicMock()
    entry.entry_id = "dyn_ss_entry"
    entry.version = 1
    entry.domain = DOMAIN
    entry.title = "Dynamic Smart Stop Test"
    entry.data = {CONF_ZONES: [{CONF_ZONE_NAME: "Living", CONF_ZONE_TEMP_SENSOR: "sensor.living_t"}]}
    entry.options = {}
    coord = MultizoneCoordinator(hass, entry)
    coord.storage = MagicMock()
    coord.storage.async_save_autotuner_states = AsyncMock()
    coord.storage.async_save_thermal_states = AsyncMock()
    coord.debounced_save_thermal_states = MagicMock()
    cid = make_zone_entity_id("Living")
    zc = ZoneController(hass, coord)
    coord.zone_controller = zc

    zc.get_autotuner(cid).seed_learned_pid(kp=50.0, ki=0.05, kd=0.0)
    zc._apply_tuner_pid_to_controller(cid)
    tm = zc.get_thermal_model(cid)
    tm.thermal_inertia = 0.4
    tm.heating_rate = 1.0  # °C/h

    t = [1000.0]
    with patch("time.monotonic", side_effect=lambda: t[0]):
        # Flat steady-state samples around 19.8 C (target 20.0 C): slope <= 0 -> NO permanent Smart Stop undershoot
        for step in range(5):
            t[0] = 1000.0 + step * 180.0
            st = SimpleNamespace(state="heat", attributes={"current_temperature": 19.8, "temperature": 20.0})
            await zc.async_update_zone(cid, st)
        attrs_ss = zc.get_zone_demand_attributes(cid)
        assert attrs_ss["smart_stop_offset"] == 0.0
        assert attrs_ss["set_point"] == pytest.approx(20.0)

        # Active warm-up ramp (+0.25 C per 15 min = 1.0 C/h) -> Smart Stop engages proportionally
        for step in range(1, 8):
            t[0] += 180.0
            cur_t = 19.2 + step * 0.05
            st = SimpleNamespace(state="heat", attributes={"current_temperature": cur_t, "temperature": 20.0})
            await zc.async_update_zone(cid, st)
        attrs_ramp = zc.get_zone_demand_attributes(cid)
        assert attrs_ramp["smart_stop_offset"] > 0.1


# ---------------------------------------------------------------------------
# 3. Cooling OLS R2 Filter, Newton k_loss & Weather-Invariant Energy Class
# ---------------------------------------------------------------------------


def test_thermal_observer_ols_r2_rejects_non_linear_and_learns_invariant_k_loss():
    t = [1000.0]
    with patch("time.monotonic", side_effect=lambda: t[0]):
        obs = ThermalObserver("climate.living")
        # Feed 4 samples with non-linear disturbance (flat then sudden step -> low R2 < 0.65)
        obs.update(21.0, is_heating=False, outdoor_temp=0.0)
        t[0] = 1600.0
        obs.update(21.0, is_heating=False, outdoor_temp=0.0)
        t[0] = 2200.0
        obs.update(21.0, is_heating=False, outdoor_temp=0.0)
        t[0] = 2800.0
        obs.update(20.7, is_heating=False, outdoor_temp=0.0)
        # Advance 10 min confirmation -> must remain 0.0 because R2 was rejected
        t[0] = 3400.0
        obs.update(20.7, is_heating=False, outdoor_temp=0.0)
        assert obs.cooling_rate == 0.0
        assert obs.k_loss == 0.0

        # Now feed linear Newton cooling: 0.40 C/hr over 45 min (delta = -0.30 C >= 0.25 C) at T_in~20 C, T_out=0 C
        obs2 = ThermalObserver("climate.living")
        obs2.update(20.15, is_heating=False, outdoor_temp=0.0)
        for step in range(1, 10):
            t[0] += 300.0  # every 5 min -> 45 min total
            obs2.update(20.15 - step * (0.30 / 9.0), is_heating=False, outdoor_temp=0.0)
        t[0] += 600.0
        obs2.update(19.79, is_heating=False, outdoor_temp=0.0)
        assert obs2.cooling_rate == pytest.approx(0.40, rel=1e-2)
        assert obs2.k_loss == pytest.approx(0.02, rel=5e-2)

        # Persist & reload k_loss
        dumped = obs2.dump_state()
        obs3 = ThermalObserver("climate.living")
        obs3.load_state(dumped)
        assert obs3.k_loss == pytest.approx(obs2.k_loss)
        assert len(obs3._k_loss_samples) == 1

    # Energy Class remains constant across cold night (0 C) and mild afternoon (14 C)
    hass = MagicMock()
    coord = MagicMock()
    coord.zone_controller.get_thermal_model.return_value = obs2
    coord.weather_sensor_id = "sensor.outdoor"

    hass.states.get.side_effect = lambda eid: (
        SimpleNamespace(state="heat", attributes={"current_temperature": 20.0})
        if eid == "climate.living"
        else SimpleNamespace(state="0.0", attributes={})
    )
    night_class = get_zone_energy_class(coord, hass, "climate.living")

    hass.states.get.side_effect = lambda eid: (
        SimpleNamespace(state="heat", attributes={"current_temperature": 20.0})
        if eid == "climate.living"
        else SimpleNamespace(state="14.0", attributes={})
    )
    afternoon_class = get_zone_energy_class(coord, hass, "climate.living")
    assert night_class == afternoon_class
    assert night_class in ("A", "B")


# ---------------------------------------------------------------------------
# 4. Adaptive Boiler PWM Interval & Phase-Locked Synchronization
# ---------------------------------------------------------------------------


def test_relay_backend_adaptive_pwm_and_phase_locked_sync():
    hass = MagicMock()
    coord = MagicMock()
    coord.zones = []

    b0 = RelayBoilerBackend(hass, coord, "switch.boiler", 0.0, 0.0, 0.0)
    assert b0._boiler_pwm.pwm_interval == 900.0
    assert b0._boiler_pwm.phase_locked is True

    b5 = RelayBoilerBackend(hass, coord, "switch.boiler", 5.0, 5.0, 0.0)
    assert b5._boiler_pwm.pwm_interval == 1200.0

    b5.set_min_cycle_on(10)
    b5.set_min_cycle_off(10)
    assert b5._boiler_pwm.pwm_interval == 2400.0

    # Phase-locked engines started at different offsets in the same window stay aligned
    t = [100.0]
    with patch("time.monotonic", side_effect=lambda: t[0]):
        pwm_boiler = PWMEngine(pwm_interval=900.0, phase_locked=True)
        t[0] = 250.0
        pwm_valve = PWMEngine(pwm_interval=900.0, phase_locked=True)
        assert pwm_boiler.cycle_start_time == pwm_valve.cycle_start_time == 0.0
        assert pwm_boiler.calculate(50.0) is True
        assert pwm_valve.calculate(50.0) is True
        t[0] = 460.0
        assert pwm_boiler.calculate(50.0) is False
        assert pwm_valve.calculate(50.0) is False
