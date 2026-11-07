"""Unit tests validating fixes for BUG-01 through BUG-05 (Audit High Severity)."""
import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

from custom_components.multizone_thermostat.const import (
    CONF_ZONE_NAME,
    CONF_ZONE_CLIMATES,
    ZONE_MODE_PRIMARY,
    ZONE_MODE_SECONDARY,
    KEY_WEATHER_CURVE,
    make_zone_entity_id,
)
from custom_components.multizone_thermostat.schedule.slot_engine import ScheduleSlotEngine
from custom_components.multizone_thermostat.zone_controller import ZoneController
from custom_components.multizone_thermostat.plant_diagnostics.anomalies import evaluate_zone_anomalies
from custom_components.multizone_thermostat.plant_diagnostics.const import ANOMALY_SENSOR_FAULT, ANOMALY_NONE
from custom_components.multizone_thermostat.safety.anti_seize import AntiSeizeManager
from custom_components.multizone_thermostat.boiler.relay_backend import RelayBoilerBackend


def test_bug01_manual_override_persists_across_midnight_gap():
    """BUG-01: Slot id for gap outside defined blocks is day-agnostic, preserving overrides across midnight."""
    engine = ScheduleSlotEngine(resolve_preset_temp_fn=lambda p, c: 20.0)
    profile = {
        "baseline_preset": "eco",
        "days": {
            "mon": {"climate.living": [{"start": "08:00", "end": "22:00", "preset": "comfort"}]},
            "tue": {"climate.living": [{"start": "07:00", "end": "22:00", "preset": "comfort"}]},
        },
    }

    # At 23:00 on Monday, next block starts Tuesday at 07:00
    t_2300 = datetime(2026, 11, 9, 23, 0, 0)
    slot_2300 = engine.evaluate_zone_slot(profile, "climate.living", t_2300)

    # At 01:00 on Tuesday, next block still starts Tuesday at 07:00
    t_0100 = datetime(2026, 11, 10, 1, 0, 0)
    slot_0100 = engine.evaluate_zone_slot(profile, "climate.living", t_0100)

    # Slot id MUST be identical so manual override isn't dropped at midnight!
    assert slot_2300["slot_id"] == slot_0100["slot_id"]
    assert "gap_2026-11-10T07:00:00" in slot_2300["slot_id"]


@pytest.mark.asyncio
async def test_bug02_weather_state_entity_id_domain_detection():
    """BUG-02: Weather domain entities (with textual state e.g. 'partlycloudy') extract temperature attribute."""
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.hass = hass
    coordinator.zones = [{CONF_ZONE_NAME: "Living"}]
    cid = make_zone_entity_id("Living")
    coordinator.weather_sensor_id = "weather.home"
    coordinator.get_persistent_data = MagicMock(return_value=1.5)  # 1.5 weather curve
    coordinator.zone_manager = MagicMock()
    coordinator.zone_manager.get_zone_mode = MagicMock(return_value=ZONE_MODE_PRIMARY)
    coordinator.demand_aggregator = MagicMock()
    coordinator.is_zone_in_frost_emergency = MagicMock(return_value=False)
    coordinator.is_dhw_active = False
    coordinator.schedule_manager = None
    coordinator._climate_entities = {}
    coordinator.plant_diagnostics.has_critical_sensor_fault = MagicMock(return_value=False)

    # State object of weather.home in Home Assistant
    weather_state = MagicMock()
    weather_state.entity_id = "weather.home"
    weather_state.state = "partlycloudy"
    weather_state.attributes = {"temperature": 5.0}  # Outdoor: 5°C
    delattr(weather_state, "domain") if hasattr(weather_state, "domain") else None

    climate_state = MagicMock()
    climate_state.attributes = {"current_temperature": 18.0, "temperature": 22.0}
    climate_state.state = "heat"

    def get_state(eid):
        if eid == "weather.home":
            return weather_state
        if eid == cid:
            return climate_state
        return None

    hass.states.get = MagicMock(side_effect=get_state)

    zc = ZoneController(hass, coordinator)
    # Autolearn completed -> PID mode
    zc._autotuners[cid].state = zc._autotuners[cid].STATE_COMPLETED
    zc._autotuners[cid].best_kp = 100.0

    # Calc demand with outdoor temp = 5.0 -> DeltaT = 22 - 5 = 17°C -> weather bonus applied!
    demand = await zc.async_update_zone(cid, climate_state)
    assert isinstance(demand, float)
    assert demand > 0.0


def test_bug03_spike_anomaly_recovers_after_sustained_readings():
    """BUG-03: Sudden jump > 4°C flags anomaly, but 3 sustained readings accept the value and clear fault."""
    cid = make_zone_entity_id("Living")
    coordinator = MagicMock()
    coordinator.zones = [{CONF_ZONE_NAME: "Living", "sensor_timeout_min": 240}]
    coordinator.get_zone_mode = MagicMock(return_value="primary")
    coordinator.get_zone_demand = MagicMock(return_value=50.0)
    coordinator.zone_manager = MagicMock()
    coordinator.zone_manager.get_zone = MagicMock(return_value={"name": "Living", "sensor_timeout_min": 240})
    coordinator.zone_manager.is_passive_heat_allowed = MagicMock(return_value=False)

    # Target is 21.0°C so jump to 20.0°C is within target (not an overshoot)
    climate_state = MagicMock()
    climate_state.attributes = {"current_temperature": 15.0, "temperature": 21.0}
    hass = MagicMock()
    hass.states.get = MagicMock(return_value=climate_state)

    state = {}
    t_mono = 1000.0

    with patch("time.monotonic", return_value=t_mono), patch("time.time", return_value=1700000000.0):
        # 1. Initial stable reading at 15°C
        code0, _ = evaluate_zone_anomalies(coordinator, hass, cid, state, boiler_on=True)
        assert code0 == ANOMALY_NONE
        assert state["last_temp_seen"] == 15.0

    # 2. Reading jumps to 20°C (+5°C) -> 1st reading is flagged as spike
    climate_state.attributes["current_temperature"] = 20.0
    with patch("time.monotonic", return_value=t_mono + 10), patch("time.time", return_value=1700000010.0):
        code1, _ = evaluate_zone_anomalies(coordinator, hass, cid, state, boiler_on=True)
        assert code1 == ANOMALY_SENSOR_FAULT

    # 3. 2nd reading at 20.1°C -> still flagged
    climate_state.attributes["current_temperature"] = 20.1
    with patch("time.monotonic", return_value=t_mono + 20), patch("time.time", return_value=1700000020.0):
        code2, _ = evaluate_zone_anomalies(coordinator, hass, cid, state, boiler_on=True)
        assert code2 == ANOMALY_SENSOR_FAULT

    # 4. 3rd reading at 20.0°C -> sustained reading accepted! Anomaly clears
    climate_state.attributes["current_temperature"] = 20.0
    with patch("time.monotonic", return_value=t_mono + 30), patch("time.time", return_value=1700000030.0):
        code3, _ = evaluate_zone_anomalies(coordinator, hass, cid, state, boiler_on=True)
        assert code3 == ANOMALY_NONE
        assert state["last_temp_seen"] == 20.0


@pytest.mark.asyncio
async def test_bug04_anti_seize_trigger_manually_reuses_running_task():
    """BUG-04: Repeated manual triggers reuse active task without cancellation race condition."""
    hass = MagicMock()
    coord = MagicMock()

    dummy_task = MagicMock()
    dummy_task.done.return_value = False
    hass.async_create_task = MagicMock(return_value=dummy_task)

    mgr = AntiSeizeManager(hass, coord)
    t1 = mgr.trigger_manually()
    assert t1 is dummy_task
    assert hass.async_create_task.call_count == 1

    # Second trigger while running must return same task without spawning second competitor
    t2 = mgr.trigger_manually()
    assert t2 is t1
    assert hass.async_create_task.call_count == 1


@pytest.mark.asyncio
async def test_bug05_secondary_zones_can_validate_trvs_ready():
    """BUG-05: Secondary zone with demand > 0 and open TRV validates hydraulic circuit readiness."""
    hass = MagicMock()
    coord = MagicMock()
    coord.zones = [
        {CONF_ZONE_NAME: "MasterBedroom", CONF_ZONE_CLIMATES: ["climate.bedroom_trv"]},
    ]
    cid = make_zone_entity_id("MasterBedroom")

    # Zone is SECONDARY with 60% demand
    coord.get_zone_mode = MagicMock(return_value=ZONE_MODE_SECONDARY)
    coord.get_zone_demand = MagicMock(return_value=60.0)

    # TRV is open at 100%
    trv_state = MagicMock(state="heat", attributes={"position": 100.0})
    hass.states.get = MagicMock(return_value=trv_state)
    hass.services.async_call = AsyncMock()

    backend = RelayBoilerBackend(hass, coord, "switch.boiler", min_cycle_on=0, min_cycle_off=0, valve_delay=0)

    # Calling async_update with 60% demand must NOT trigger 120s HOLD_TRV_CLOSED!
    await backend.async_update(60.0, cid, False)

    assert "HOLD_TRV_CLOSED" not in backend._status_reason
    assert hass.services.async_call.called
