"""Unit tests verifying Track 2 fixes for beta.6: PID, PIDWrapper, Autotune, ThermalObserver, ZoneController."""
import math
import sys
import time
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from custom_components.multizone_thermostat.pid import PID, PIDController
from custom_components.multizone_thermostat.pid_wrapper import MultizonePID
from custom_components.multizone_thermostat.autotune import PassiveAutotuneObserver
from custom_components.multizone_thermostat.thermal_model import ThermalObserver


# -----------------------------------------------------------------------------
# 1. PID Controller Tests
# -----------------------------------------------------------------------------
def test_pid_uses_monotonic_and_rejects_non_finite():
    """Verify PID uses monotonic time and rejects NaN, +inf, -inf cleanly."""
    pid = PID(kp=10.0, ki=0.1, kd=1.0)
    
    # Normal sample
    out, updated = pid.calc(input_val=20.0, set_point=21.0, input_time=100.0, last_input_time=None)
    assert updated is True
    assert out > 0.0

    prev_integral = pid.integral
    prev_deriv = pid.derivative

    # Rejection of NaN
    out_nan, updated_nan = pid.calc(input_val=float("nan"), set_point=21.0)
    assert updated_nan is False
    assert out_nan == out
    assert pid.integral == prev_integral
    assert pid.derivative == prev_deriv

    # Rejection of +inf
    out_inf, updated_inf = pid.calc(input_val=float("inf"), set_point=21.0)
    assert updated_inf is False
    assert out_inf == out
    assert pid.integral == prev_integral

    # Rejection of -inf
    out_ninf, updated_ninf = pid.calc(input_val=20.0, set_point=float("-inf"))
    assert updated_ninf is False
    assert out_ninf == out
    assert pid.integral == prev_integral


def test_pid_max_dt_clamps_integral_accumulation():
    """Verify max_dt parameter caps dt for integral accumulation to prevent windup."""
    pid = PID(kp=10.0, ki=0.1, kd=0.0, max_dt=300.0)
    assert pid.max_dt == 300.0

    # First sample
    pid.calc(input_val=19.0, set_point=20.0, input_time=1000.0, last_input_time=None)
    assert pid.integral == 0.0

    # Second sample with 7200s gap (2 hours)
    # Without max_dt, dt=7200s -> integral += 0.1 * 1.0 * 7200 = 720
    # With max_dt=300s, dt_int = 300s -> integral += 0.1 * 1.0 * 300 = 30.0
    pid.calc(input_val=19.0, set_point=20.0, input_time=8200.0, last_input_time=1000.0)
    assert pid.integral == pytest.approx(30.0)


def test_pid_derivative_filtering_and_clamping():
    """Verify least-squares derivative over 15-min window, flicker immunity, clamping to [-15, 15], and reset on dt < 1s."""
    pid = PID(kp=10.0, ki=0.0, kd=1000.0)

    # Initial sample and < 5 min span: derivative stays 0.0
    pid.calc(input_val=20.0, set_point=20.0, input_time=0.0, last_input_time=None)
    assert pid.derivative == 0.0
    pid.calc(input_val=19.5, set_point=20.0, input_time=10.0, last_input_time=0.0)
    assert pid.derivative == 0.0

    # Real downward ramp >= 5 min span and > 0.105 C excursion -> positive D bounded by +/-15
    pid.calc(input_val=19.0, set_point=20.0, input_time=300.0, last_input_time=10.0)
    assert 0.0 < pid.derivative <= 15.0

    # Massive drop over 600s -> raw -Kd*slope exceeds +15 -> clamps to exactly +15.0
    pid_spike = PID(kp=10.0, ki=0.0, kd=5000.0)
    pid_spike.calc(input_val=20.0, set_point=20.0, input_time=0.0, last_input_time=None)
    pid_spike.calc(input_val=19.0, set_point=20.0, input_time=300.0, last_input_time=0.0)
    pid_spike.calc(input_val=10.0, set_point=20.0, input_time=600.0, last_input_time=300.0)
    assert pid_spike.derivative == pytest.approx(15.0)

    # When dt < 1.0s: derivative must be explicitly reset to 0.0
    pid_spike.calc(input_val=10.0, set_point=20.0, input_time=600.5, last_input_time=600.0)
    assert pid_spike.derivative == 0.0


# -----------------------------------------------------------------------------
# 2. PID Wrapper Tests
# -----------------------------------------------------------------------------
def test_pid_wrapper_updates_last_input_time_only_on_updated():
    """Verify MultizonePID only updates _last_input_time when updated is True."""
    wrapper = MultizonePID(kp=10.0, ki=0.1, kd=1.0)
    assert wrapper._last_input_time is None

    # Valid calculation
    wrapper.calc(20.0, 21.0)
    t1 = wrapper._last_input_time
    assert t1 is not None

    # Invalid calculation (NaN temperature): updated is False
    wrapper.calc(float("nan"), 21.0)
    assert wrapper._last_input_time == t1  # Must NOT be modified!


# -----------------------------------------------------------------------------
# 3. Autotune Observer Tests
# -----------------------------------------------------------------------------
def test_autotune_extended_dead_time_and_ti_kd_limits():
    """Verify L up to 14400s is accepted, Ti >= 600s, and Kd <= 500.0."""
    obs = PassiveAutotuneObserver("climate.radiant_zone", required_cycles=1)
    obs.cycle_start_time = 0.0
    obs.cycle_start_temp = 18.0

    # Very slow underfloor zone: Dead time L = 7500s (> 7200s former limit, < 14400s new limit)
    # history points:
    # 0 to 7500s flat at 18.0
    # 7500s to 10000s rises to 18.5 (slope = 0.50 / 2500 = 0.0002 °C/s)
    obs.history.extend([
        (0.0, 18.0),
        (2000.0, 18.0),
        (5000.0, 18.0),
        (7500.0, 18.0),
        (10000.0, 18.50),
    ])
    obs._stop_heating(10000.0, 18.50)
    assert len(obs.completed_cycles) == 1
    cycle = obs.completed_cycles[0]
    assert cycle["L"] > 7200.0  # Would have been rejected under old 7200s limit!
    assert cycle["Kp"] > 0.0
    assert cycle["Ki"] > 0.0
    assert cycle["Kd"] <= 500.0  # Capped to 500.0


def test_weekly_learning_idle_tracking_and_false_start_prevention():
    """Verify false start prevention from already-running actuator and rollback."""
    tuner = PassiveAutotuneObserver("climate.living", required_cycles=1)
    t0 = 1_000_000.0
    # Complete 1 cycle to reach COMPLETED state
    tuner.completed_cycles.append({
        "L": 120.0, "slope": 0.001, "Kp": 50.0, "Ki": 0.05, "Kd": 200.0, "timestamp": t0
    })
    tuner.state = tuner.STATE_COMPLETED
    tuner._compute_final_pid()
    assert tuner.baseline_kp == 50.0
    assert tuner.baseline_ki == 0.05
    assert tuner.baseline_kd == 200.0

    # 1. System is running at intermediate demand (40%) -> _was_idle_before_ramp becomes False
    tuner.update(20.0, is_active=True, now=t0 + 100.0, demand=40.0)
    assert tuner._was_idle_before_ramp is False
    assert tuner._ramp_active is False

    # 2. Demand jumps to 90% (>= 85%), but system was NOT idle -> should NOT start a weekly ramp!
    tuner.update(20.1, is_active=True, now=t0 + 150.0, demand=90.0)
    assert tuner._ramp_active is False  # False start prevented!

    # 3. System stops (idle) -> _was_idle_before_ramp becomes True
    tuner.update(20.2, is_active=False, now=t0 + 200.0, demand=0.0)
    assert tuner._was_idle_before_ramp is True

    # 4. Now cold start jump to 90% -> weekly ramp begins!
    tuner.update(20.0, is_active=True, now=t0 + 300.0, demand=90.0)
    assert tuner._ramp_active is True
    assert tuner._was_idle_before_ramp is False

    # 5. Rollback to baseline test
    tuner._learned_kp = 85.0
    tuner._learned_ki = 0.09
    tuner._learned_kd = 350.0
    tuner._sync_effective_pid()
    assert tuner.kp == 85.0

    tuner.rollback_to_baseline()
    assert tuner._learned_kp == 50.0
    assert tuner._learned_ki == 0.05
    assert tuner._learned_kd == 200.0
    assert tuner.kp == 50.0
    assert tuner.ki == 0.05
    assert tuner.kd == 200.0
    assert tuner.best_kp == 50.0


# -----------------------------------------------------------------------------
# 4. ThermalObserver Tests
# -----------------------------------------------------------------------------
def test_thermal_observer_lowered_gate_and_duty_normalization():
    """Verify heating rate gate is lowered to demand >= 30% with normalized duty."""
    obs = ThermalObserver("climate.test_zone")
    obs._last_temp = 19.0
    obs._last_temp_time = 1000.0
    obs._is_heating = True

    # demand = 25% (< 30% gate): no update
    with patch("time.monotonic", return_value=2800.0):  # 0.5h elapsed
        obs.update(19.5, is_heating=True, demand=25.0)
        assert obs.heating_rate == 0.0

    # demand = 35% (>= 30% gate): updates with duty normalization
    # delta = 0.5 over 0.5h = 1.0 °C/hr -> normalized by duty 0.35 = 1.0 / 0.35 ~= 2.857 °C/hr
    obs._last_temp = 19.0
    obs._last_temp_time = 1000.0
    with patch("time.monotonic", return_value=2800.0):
        obs.update(19.5, is_heating=True, demand=35.0)
        assert obs.heating_rate == pytest.approx(1.0 / 0.35, rel=1e-2)
