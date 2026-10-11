"""Tests for PID recovery and integral/timestamp reset after DHW production (roadmap 4.5)."""
import time
from unittest.mock import MagicMock, patch

import pytest

from custom_components.multizone_thermostat.zone_controller import ZoneController, make_zone_entity_id
from custom_components.multizone_thermostat.pid_wrapper import MultizonePID


class DummyState:
    def __init__(self, state="heat", current_temp=19.0, target_temp=20.0):
        self.state = state
        self.attributes = {
            "current_temperature": current_temp,
            "temperature": target_temp,
        }


def _create_mock_coordinator():
    coord = MagicMock()
    coord.zones = [{"name": "Salone"}]
    demands = {}
    coord.demand_aggregator = MagicMock()
    coord.demand_aggregator.get_zone_demand = MagicMock(side_effect=lambda cid: demands.get(cid, 0.0))
    coord.demand_aggregator.set_zone_demand = MagicMock(side_effect=lambda cid, d: demands.update({cid: d}))
    coord.get_zone_demand = coord.demand_aggregator.get_zone_demand
    coord.get_zone_mode = MagicMock(return_value="auto")
    coord.plant_diagnostics = MagicMock()
    coord.plant_diagnostics.has_critical_sensor_fault = MagicMock(return_value=False)
    coord.weather_sensor_id = None
    coord.is_dhw_active = False
    return coord, demands


@pytest.mark.asyncio
async def test_pid_recovery_after_20_minute_dhw():
    """Verify that after a 20-minute DHW event, the PID resumes without integral surge or dt jump."""
    hass = MagicMock()
    coord, demands = _create_mock_coordinator()
    zc = ZoneController(hass, coord)
    cid = make_zone_entity_id("Salone")

    # Set up PID with Kp=10.0, Ki=0.05 (integrating), Kd=1.0
    tuner = zc.get_autotuner(cid)
    tuner.state = tuner.STATE_COMPLETED
    pid = zc.get_pid(cid)
    pid.set_pid_param(kp=10.0, ki=0.05, kd=1.0)

    # 1. Normal heating before DHW: Error = 1.0°C (19.0 -> 20.0)
    t0 = 1000.0
    with patch("time.monotonic", return_value=t0):
        st = DummyState("heat", current_temp=19.0, target_temp=20.0)
        res1 = await zc.async_update_zone(cid, st)
        # First sample: dt = 0, proportional = 10.0%, integral = 0.0
        assert res1 == pytest.approx(10.0)

    # Second sample 60s later: dt = 60s, error = 1.0 -> integral adds Ki * 1.0 * 60 = 3.0%
    with patch("time.monotonic", return_value=t0 + 60.0):
        res2 = await zc.async_update_zone(cid, st)
        assert res2 > res1
        assert pid._pid.integral == pytest.approx(3.0)

    # 2. DHW starts and lasts 20 minutes (1200 seconds)
    coord.is_dhw_active = True
    with patch("time.monotonic", return_value=t0 + 120.0):
        await zc.async_update_zone(cid, st)
        # PID frozen during DHW, clear_samples called
        assert pid._pid.integral == 0.0

    # 3. DHW ends 20 minutes later
    coord.is_dhw_active = False
    with patch("time.monotonic", return_value=t0 + 1260.0):
        # Resume heating
        res_post_dhw = await zc.async_update_zone(cid, st)

        # CRITICAL VERIFICATION:
        # If dt had not been reset, dt would be 1200s, and Ki * error * 1200 = 60% jump!
        # Instead, dt must be 0 on resumption and integral reset to 0.0.
        assert pid._pid._dt == 0.0
        assert pid._pid.integral == 0.0
        # Demand resumes cleanly from proportional baseline (10.0%) without sudden spike
        assert res_post_dhw == pytest.approx(10.0)

    # Subsequent sample 30s after resumption integrates normally with small dt=30s
    with patch("time.monotonic", return_value=t0 + 1290.0):
        res_subsequent = await zc.async_update_zone(cid, st)
        assert pid._pid._dt == pytest.approx(30.0)
        assert pid._pid.integral == pytest.approx(0.05 * 1.0 * 30.0)  # 1.5%
        assert res_subsequent == pytest.approx(11.5)


def test_multizone_pid_clear_samples_resets_all_timing_and_integral():
    """Direct verification of MultizonePID clear_samples contract."""
    pid = MultizonePID(kp=10.0, ki=0.1, kd=1.0)
    
    t0 = 500.0
    with patch("time.monotonic", return_value=t0):
        pid.calc(18.0, 20.0)

    with patch("time.monotonic", return_value=t0 + 50.0):
        pid.calc(18.0, 20.0)
        assert pid._pid.integral > 0.0
        assert pid._last_input_time == t0 + 50.0

    # Clear samples (as happens at DHW start/finish)
    pid.clear_samples()
    assert pid._last_input_time is None
    assert pid._pid.integral == 0.0

    # First call after clear has dt=0
    with patch("time.monotonic", return_value=t0 + 1500.0):
        demand = pid.calc(18.0, 20.0)
        assert pid._pid._dt == 0.0
        assert pid._pid.integral == 0.0
        assert demand == pytest.approx(20.0)  # Pure proportional: 10.0 * 2.0
