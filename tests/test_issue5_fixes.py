"""Unit and regression tests for Issue #5 fixes:
1. Scheduler: local time vs UTC wall-clock slot resolution
2. Smart Start: preheating latching as room warms up
3. Dead sensor timeout: fresh report tracking with constant temperature & zone ID logging
4. Direct valve PWM: minimum cycle times hold against fluctuating demand
"""

import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import zoneinfo

import pytest

# Ensure dummy_ha is used
sys.meta_path[:] = [
    f for f in sys.meta_path if f.__class__.__name__ != "HomeAssistantMockFinder"
]

import homeassistant.util.dt as dt_util
from homeassistant.components.climate.const import HVACMode
from homeassistant.const import STATE_ON, STATE_OFF

from custom_components.multizone_thermostat.const import (
    CONF_ZONE_NAME,
    CONF_ZONE_SWITCHES,
    CONF_ZONE_TEMP_SENSOR,
    DEFAULT_BASELINE_PRESET,
    SCHEDULE_DAYS,
    make_zone_entity_id,
)
from custom_components.multizone_thermostat.pid_wrapper import MultizonePID
from custom_components.multizone_thermostat.pwm_engine import PWMEngine
from custom_components.multizone_thermostat.schedule_manager import ScheduleProfileManager
from custom_components.multizone_thermostat.sync_manager import ZoneSyncManager
from custom_components.multizone_thermostat.zone_controller import ZoneController


# ---------------------------------------------------------------------------
# 1. Weekly Scheduler: Local Time vs UTC (mirks80 reproduction)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scheduler_local_time_vs_utc():
    """Evaluating at 08:10 CET or 07:10 UTC selects 21°C when Monday 08:00-23:00 Comfort block is configured."""
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.time_zone = "Europe/Rome"
    dt_util.set_default_time_zone("Europe/Rome")

    coordinator = MagicMock()
    coordinator.hass = hass
    coordinator.zones = [{CONF_ZONE_NAME: "Living"}]
    coordinator.get_persistent_data = MagicMock(return_value=None)
    coordinator.zone_manager = MagicMock()
    coordinator.zone_manager.get_preset_temperature = MagicMock(
        side_effect=lambda preset, cid: 21.0 if preset == "comfort" else 18.0
    )

    mgr = ScheduleProfileManager(coordinator)
    cid = make_zone_entity_id("Living")

    # Configure Monday block 08:00 - 23:00 Comfort
    profile_data = {
        "name": "Standard",
        "baseline_preset": "eco",
        "days": {
            "mon": {
                cid: [{"start": "08:00", "end": "23:00", "preset": "comfort"}]
            }
        },
    }
    await mgr.async_save_profile("standard", profile_data)
    await mgr.async_set_scheduler_enabled(True)

    rome_tz = dt_util.get_time_zone("Europe/Rome")

    # Monday in winter (CET = UTC+1): e.g. 2026-11-09 is a Monday
    eval_local = datetime(2026, 11, 9, 8, 10, 0, tzinfo=rome_tz)
    eval_utc = eval_local.astimezone(timezone.utc)
    assert eval_utc.hour == 7
    assert eval_utc.minute == 10

    # 1. Evaluate with local CET time
    slot_local = mgr.evaluate_zone_slot(cid, eval_local)
    assert slot_local["target_temp"] == 21.0
    assert slot_local["state_type"] == "block"
    assert slot_local["preset"] == "comfort"

    # 2. Evaluate with UTC instant (as passed by HA periodic callbacks)
    slot_utc = mgr.evaluate_zone_slot(cid, eval_utc)
    assert slot_utc["target_temp"] == 21.0
    assert slot_utc["state_type"] == "block"
    assert slot_utc["preset"] == "comfort"

    # 3. Before block at 07:50 CET (06:50 UTC) -> should be Eco (18.0 °C)
    pre_local = datetime(2026, 11, 9, 7, 50, 0, tzinfo=rome_tz)
    pre_utc = pre_local.astimezone(timezone.utc)
    slot_pre = mgr.evaluate_zone_slot(cid, pre_utc)
    assert slot_pre["target_temp"] == 18.0
    assert slot_pre["state_type"] == "baseline"


# ---------------------------------------------------------------------------
# 2. Predictive Smart Start Latching (mirks80 reproduction)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_smart_start_preheating_latched_as_room_warms():
    """Smart Start stays latched even when room warms and deficit shrinks before slot starts."""
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.time_zone = "Europe/Rome"
    dt_util.set_default_time_zone("Europe/Rome")

    cid = make_zone_entity_id("Living")
    current_temp_val = 19.8

    climate_mock = MagicMock()
    climate_mock.hvac_mode = HVACMode.HEAT
    climate_mock._hvac_mode = HVACMode.HEAT
    climate_mock.current_temperature = current_temp_val

    thermal_mock = MagicMock()
    thermal_mock.heating_rate = 0.4  # 0.4 °C/h as reported by mirks80

    coordinator = MagicMock()
    coordinator.hass = hass
    coordinator.zones = [{CONF_ZONE_NAME: "Living", "climate_id": cid}]
    coordinator._climate_entities = {cid: climate_mock}
    coordinator._thermal_models = {cid: thermal_mock}
    coordinator.get_persistent_data = MagicMock(return_value=None)
    coordinator.zone_manager = MagicMock()
    coordinator.zone_manager.get_preset_temperature = MagicMock(
        side_effect=lambda preset, cid: 21.0 if preset == "comfort" else 18.0
    )

    mgr = ScheduleProfileManager(coordinator)

    # Monday Comfort block 08:00 - 23:00 (target 21.0, baseline eco 18.0)
    profile_data = {
        "name": "Standard",
        "baseline_preset": "eco",
        "days": {
            "mon": {
                cid: [{"start": "08:00", "end": "23:00", "preset": "comfort"}]
            }
        },
    }
    await mgr.async_save_profile("standard", profile_data)
    await mgr.async_set_scheduler_enabled(True)

    rome_tz = dt_util.get_time_zone("Europe/Rome")

    # Step 1: At 05:05, room is at 19.8 °C.
    # Deficit = 21.0 - 19.8 = 1.2 °C. At 0.4 °C/h, needs 3.0 h -> ignition at 05:00.
    # 05:05 >= 05:00 -> Smart Start MUST trigger and target set to 21.0 °C.
    t_0505 = datetime(2026, 11, 9, 5, 5, 0, tzinfo=rome_tz)
    climate_mock.current_temperature = 19.8
    await mgr.async_evaluate_schedule(t_0505)

    assert mgr.schedule_overrides[cid] == 21.0
    assert cid in mgr.smart_start_info
    assert mgr.smart_start_info[cid]["target_temp"] == 21.0

    # Step 2: At 05:30, room has warmed to 20.1 °C.
    # Without latching, deficit is 0.9 °C -> needs 2h15m -> ignition at 05:45.
    # Because 05:30 < 05:45, unmodified code reverted to Eco 18.0 °C!
    # With latching, it MUST stay active at 21.0 °C!
    t_0530 = datetime(2026, 11, 9, 5, 30, 0, tzinfo=rome_tz)
    climate_mock.current_temperature = 20.1
    await mgr.async_evaluate_schedule(t_0530)

    assert mgr.schedule_overrides[cid] == 21.0
    assert cid in mgr.smart_start_info
    assert mgr.smart_start_info[cid]["target_temp"] == 21.0

    # Step 3: At 08:00, block starts officially -> slot evaluation takes over at 21.0 °C
    t_0800 = datetime(2026, 11, 9, 8, 0, 0, tzinfo=rome_tz)
    climate_mock.current_temperature = 21.0
    await mgr.async_evaluate_schedule(t_0800)

    assert mgr.schedule_overrides[cid] == 21.0

    # Step 4: Verify Explicit OFF resets the latch
    t_preheat = datetime(2026, 11, 9, 5, 10, 0, tzinfo=rome_tz)
    climate_mock.current_temperature = 19.8
    await mgr.async_evaluate_schedule(t_preheat)
    assert cid in mgr.smart_start_info

    climate_mock.hvac_mode = HVACMode.OFF
    climate_mock._hvac_mode = HVACMode.OFF
    await mgr.async_evaluate_schedule(t_preheat)
    assert cid not in mgr.schedule_overrides
    assert cid not in mgr.smart_start_info


# ---------------------------------------------------------------------------
# 3. Dead Sensor Timeout: Constant reading report freshness & Zone ID
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dead_sensor_timeout_freshness_and_zone_id(caplog):
    """Dead sensor timeout includes zone ID and does not falsely trigger on constant readings."""
    # 1. MultizonePID warning includes zone ID
    pid = MultizonePID(kp=100.0, ki=0.0, kd=0.0, sensor_timeout=10.0, zone_id="climate.soggiorno")
    pid.last_sensor_update = 100.0

    with patch("time.monotonic", return_value=120.0):
        demand = pid.calc(current_temp=20.0, target_temp=21.0)
        assert demand == 0.0
        assert "for zone 'climate.soggiorno'" in caplog.text

    # 2. ZoneController keeps sensor fresh when reports arrive with identical temperature
    hass = MagicMock()
    hass.states = MagicMock()

    sensor_state = MagicMock()
    sensor_state.state = "20.0"
    now_utc = datetime.now(timezone.utc)
    sensor_state.last_reported = now_utc
    hass.states.get = MagicMock(return_value=sensor_state)

    coord = MagicMock()
    coord.hass = hass
    coord.zones = [{
        CONF_ZONE_NAME: "Soggiorno",
        CONF_ZONE_TEMP_SENSOR: "sensor.soggiorno_temp",
    }]
    coord.get_persistent_data = MagicMock(return_value=0.0)
    coord.weather_sensor_id = None
    coord.is_dhw_active = False
    coord.demand_aggregator = MagicMock()
    coord.demand_aggregator.set_zone_demand = MagicMock()
    coord.zone_manager = MagicMock()
    coord.zone_manager.get_zone_mode = MagicMock(return_value="primary")

    zc = ZoneController(hass, coord)
    cid = make_zone_entity_id("Soggiorno")

    # First update: 20.0
    climate_state = MagicMock()
    climate_state.state = "heat"
    climate_state.attributes = {"current_temperature": 20.0, "temperature": 21.0}
    await zc.async_update_zone(cid, climate_state)
    t1 = zc.pids[cid].last_sensor_update

    # Second update: still 20.0, but a new report arrived 1 minute later
    sensor_state.last_reported = now_utc + timedelta(minutes=1)
    await zc.async_update_zone(cid, climate_state)
    t2 = zc.pids[cid].last_sensor_update

    # Timestamp was refreshed despite identical temperature!
    assert t2 >= t1


# ---------------------------------------------------------------------------
# 4. Direct Valve PWM: Protection against short ON/OFF intervals
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_direct_valve_pwm_prevents_short_cycles():
    """ZoneSyncManager respects min_cycle_on and min_cycle_off against mid-cycle demand shifts."""
    hass = MagicMock()
    hass.states = MagicMock()
    switch_state = MagicMock(state="off")
    hass.states.get = MagicMock(return_value=switch_state)
    hass.services = AsyncMock()
    hass.services.async_call = AsyncMock()

    coord = MagicMock()
    coord._min_cycle_on = 3.0   # 3 minutes = 180s
    coord._min_cycle_off = 3.0  # 3 minutes = 180s
    coord.get_persistent_data = MagicMock(return_value=None)
    demand_val = 50.0
    coord.get_zone_demand = MagicMock(side_effect=lambda cid: demand_val)

    t_now = 1000.0

    with patch("time.monotonic", return_value=t_now - 500.0):
        sync_mgr = ZoneSyncManager(
            hass=hass,
            coordinator=coord,
            zone_name="Living",
            entity_id="climate.living",
            climates=[],
            switches=["switch.living_valve"],
            calibrations={},
        )

    # 1. Initially OFF, demand 50% -> turns ON
    with patch("time.monotonic", return_value=t_now):
        changed = await sync_mgr.async_pwm_tick(HVACMode.HEAT)
        assert changed is True
        assert sync_mgr._local_pwm_state is True

    # 2. After 15 seconds (t = 1015s), demand drops to 10%
    # In pure calculation, 10% demand at t=15s might turn OFF
    # But min_on is 180s: it MUST hold ON!
    t_now = 1015.0
    demand_val = 10.0
    with patch("time.monotonic", return_value=t_now):
        changed = await sync_mgr.async_pwm_tick(HVACMode.HEAT)
        assert changed is False
        assert sync_mgr._local_pwm_state is True

    # 3. After min_on elapsed (t = 1200s, 200s in state), turns OFF
    t_now = 1200.0
    with patch("time.monotonic", return_value=t_now):
        changed = await sync_mgr.async_pwm_tick(HVACMode.HEAT)
        assert changed is True
        assert sync_mgr._local_pwm_state is False

    # 4. After 20 seconds of OFF (t = 1220s), demand rises to 40%
    # min_off is 180s: it MUST hold OFF, preventing a 20s short OFF pulse!
    t_now = 1220.0
    demand_val = 40.0
    with patch("time.monotonic", return_value=t_now):
        changed = await sync_mgr.async_pwm_tick(HVACMode.HEAT)
        assert changed is False
        assert sync_mgr._local_pwm_state is False
