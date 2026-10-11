"""Tests for time management: in-process monotonic timing vs wall-clock persistence (Phase 2)."""
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

from custom_components.multizone_thermostat.pwm_engine import PWMEngine
from custom_components.multizone_thermostat.pid_wrapper import MultizonePID
from custom_components.multizone_thermostat.autotune import PassiveAutotuneObserver
from custom_components.multizone_thermostat.safety.watchdog import SensorWatchdog
from custom_components.multizone_thermostat.plant_diagnostics.engine import PlantDiagnosticsEngine


def test_pwm_engine_immune_to_wall_clock_shift():
    """PWMEngine uses monotonic time and must be immune to wall-clock time shifts."""
    pwm = PWMEngine(pwm_interval=600.0)
    
    # 50% demand -> calculate checks time.monotonic()
    # Simulate wall-clock jumping 10 hours back and forward
    with patch("time.time", return_value=time.time() - 36000):
        state = pwm.calculate(demand=50.0)
        assert state is True

    with patch("time.time", return_value=time.time() + 36000):
        state = pwm.calculate(demand=50.0)
        assert state is True


def test_pid_wrapper_timeout_immune_to_wall_clock_shift():
    """MultizonePID sensor timeout uses monotonic time and is immune to wall-clock shifts."""
    pid = MultizonePID(kp=10.0, ki=0.01, kd=0.0, sensor_timeout=600.0)
    pid.update_sensor_timestamp()

    # Wall-clock leaps forward 2 days: sensor should NOT be reported as timed out
    with patch("time.time", return_value=time.time() + 172800):
        demand = pid.calc(current_temp=19.0, target_temp=20.0)
        assert demand > 0.0

    # Wall-clock leaps backward 2 days: sensor should NOT fail or misreport
    with patch("time.time", return_value=time.time() - 172800):
        demand = pid.calc(current_temp=19.0, target_temp=20.0)
        assert demand > 0.0


def test_plant_diagnostics_cycle_count_immune_to_wall_clock_shift():
    """Boiler cycle frequency in PlantDiagnosticsEngine uses monotonic time."""
    coord = MagicMock()
    coord.zones = [{"name": "Living"}]
    engine = PlantDiagnosticsEngine(coord)

    # Record ON and OFF cycles
    with patch("time.time", return_value=time.time() - 7200):
        engine.record_boiler_state(True)
        engine.record_boiler_state(False)

    with patch("time.time", return_value=time.time() + 7200):
        engine.record_boiler_state(True)
        engine.record_boiler_state(False)

    # Cycles per hour should be calculated via monotonic time, unaffected by wall-clock patches
    cycles = engine.get_boiler_cycles_per_hour()
    assert cycles == 2


def test_autotune_dump_state_uses_wall_clock_and_no_monotonic():
    """Autotune persistence must save absolute wall-clock timestamps (> 1e8)."""
    tuner = PassiveAutotuneObserver("test_zone", required_cycles=1)
    
    # Simulate a full heating cycle with at least 5 data points across 200s
    t0_mono = 100.0
    t0_wall = 1700000000.0

    with patch("time.monotonic", return_value=t0_mono), patch("time.time", return_value=t0_wall):
        tuner.update(current_temp=19.0, is_heating=True)

    # Add points during heating
    for step in range(1, 5):
        t_m = t0_mono + step * 50.0
        t_w = t0_wall + step * 50.0
        temp = 19.0 + step * 0.25
        with patch("time.monotonic", return_value=t_m), patch("time.time", return_value=t_w):
            tuner.update(current_temp=temp, is_heating=True)

    # Stop heating
    with patch("time.monotonic", return_value=t0_mono + 250.0), patch("time.time", return_value=t0_wall + 250.0):
        tuner.update(current_temp=20.2, is_heating=False)

    assert tuner.state == tuner.STATE_COMPLETED
    dumped = tuner.dump_state()
    assert "completed_cycles" in dumped
    assert len(dumped["completed_cycles"]) == 1

    cycle = dumped["completed_cycles"][0]
    # Timestamp must be absolute wall-clock (> 1e8), not monotonic (~100-300)
    assert cycle["timestamp"] >= 1e8
    assert cycle["timestamp"] == pytest.approx(t0_wall + 200.0)

    # Reloading state
    tuner2 = PassiveAutotuneObserver("test_zone", required_cycles=1)
    tuner2.load_state(dumped)
    assert tuner2.state == tuner2.STATE_COMPLETED
    assert tuner2.kp == pytest.approx(cycle["Kp"])


def test_sensor_watchdog_datetime_and_float_types():
    """SensorWatchdog handles datetime, epoch float, and monotonic float without mixing clocks."""
    wd = SensorWatchdog()

    # 1. datetime object (HA state last_reported)
    now_dt = datetime.now(timezone.utc)
    recent_dt = now_dt - timedelta(seconds=30)
    old_dt = now_dt - timedelta(seconds=120)

    assert wd.is_sensor_stale(recent_dt, timeout_seconds=60) is False
    assert wd.is_sensor_stale(old_dt, timeout_seconds=60) is True

    # 2. Epoch float (> 1e8)
    now_epoch = time.time()
    assert wd.is_sensor_stale(now_epoch - 30, timeout_seconds=60) is False
    assert wd.is_sensor_stale(now_epoch - 120, timeout_seconds=60) is True

    # 3. Monotonic float (< 1e8)
    now_mono = time.monotonic()
    assert wd.is_sensor_stale(now_mono - 30, timeout_seconds=60) is False
    assert wd.is_sensor_stale(now_mono - 120, timeout_seconds=60) is True

    # Zero or negative timeout never stale
    assert wd.is_sensor_stale(old_dt, timeout_seconds=0) is False
