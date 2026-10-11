"""Dedicated unit tests for Phase 4 items: presence (4.1), cold room (4.2), OpenTherm confirmation (4.4)."""
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.multizone_thermostat.const import (
    GLOBAL_PRESET_AWAY,
    KEY_GEOFENCING_TOGGLE,
)
from custom_components.multizone_thermostat.routine_manager import RoutineManager
from custom_components.multizone_thermostat.plant_diagnostics.anomalies import (
    ANOMALY_NONE,
    ANOMALY_SENSOR_FAULT,
    evaluate_zone_anomalies,
)
from custom_components.multizone_thermostat.boiler.opentherm_backend import (
    COMMAND_CONFIRM_TIMEOUT,
    OpenThermBoilerBackend,
)


# ---------------------------------------------------------------------------
# 4.1 Presence tests (unknown / unavailable handling)
# ---------------------------------------------------------------------------

def _create_routine_manager():
    hass = MagicMock()
    coros = []
    def create_task(coro):
        coros.append(coro)
        return MagicMock()
    hass.async_create_task = MagicMock(side_effect=create_task)

    get_persistent_data = MagicMock(return_value=True)
    async_set_persistent_data = AsyncMock()
    get_current_global_preset = MagicMock(return_value="auto")
    async_set_global_preset = AsyncMock()

    rm = RoutineManager(
        hass,
        "sensor.presence",
        get_persistent_data,
        async_set_persistent_data,
        get_current_global_preset,
        async_set_global_preset,
    )
    return rm, hass, coros


@pytest.mark.asyncio
async def test_presence_unknown_or_unavailable_does_not_trigger_away():
    """Verify that sensor dropouts (unavailable/unknown) never trigger Away mode."""
    rm, hass, coros = _create_routine_manager()
    rm._last_known_presence = "home"

    # Event with state becoming unavailable
    event_unavail = MagicMock()
    event_unavail.data = {
        "old_state": MagicMock(state="home"),
        "new_state": MagicMock(state="unavailable"),
    }
    rm._async_on_presence_changed(event_unavail)
    assert hass.async_create_task.call_count == 0
    assert rm._last_known_presence == "home"

    # Event transitioning from unavailable to unknown
    event_unknown = MagicMock()
    event_unknown.data = {
        "old_state": MagicMock(state="unavailable"),
        "new_state": MagicMock(state="unknown"),
    }
    rm._async_on_presence_changed(event_unknown)
    assert hass.async_create_task.call_count == 0
    assert rm._last_known_presence == "home"


@pytest.mark.asyncio
async def test_presence_home_to_unavailable_to_not_home_triggers_away():
    """Verify that a drop into unavailable followed by not_home correctly compares with last known good value."""
    rm, hass, coros = _create_routine_manager()
    rm._last_known_presence = "home"

    # Drop into unavailable
    ev1 = MagicMock()
    ev1.data = {"old_state": MagicMock(state="home"), "new_state": MagicMock(state="unavailable")}
    rm._async_on_presence_changed(ev1)
    assert hass.async_create_task.call_count == 0

    # Recovery into not_home: must compare with "home" and trigger Away
    ev2 = MagicMock()
    ev2.data = {"old_state": MagicMock(state="unavailable"), "new_state": MagicMock(state="not_home")}
    rm._async_on_presence_changed(ev2)
    assert hass.async_create_task.call_count == 2
    assert rm._last_known_presence == "not_home"
    for c in coros:
        await c


# ---------------------------------------------------------------------------
# 4.2 Cold room test (< 4 °C does NOT trigger sensor fault)
# ---------------------------------------------------------------------------

def test_cold_room_at_2c_is_not_sensor_fault():
    """Verify cold rooms (e.g., 2.0°C or 0.0°C) are considered physically valid and not faulted."""
    coordinator = MagicMock()
    coordinator.get_zone_demand.return_value = 0.0
    coordinator.get_zone_mode.return_value = "auto"
    coordinator.zone_manager.get_zone.return_value = {"temp_sensor": None}
    coordinator.zone_manager.is_passive_heat_allowed.return_value = False

    hass = MagicMock()
    cid = "climate.cantina"

    state = {
        "active_anomaly": ANOMALY_NONE,
        "anomaly_details": "",
        "last_temp_seen": 2.0,
        "last_temp_time": time.monotonic() - 100,
        "last_heating_time": None,
        "high_demand_start_time": None,
        "high_demand_start_temp": None,
        "ghost_heat_start_temp": None,
        "fallback_ok": False,
    }

    # 1. Temperature of 2.0°C (cold room)
    st_2c = MagicMock(attributes={"current_temperature": 2.0, "temperature": 18.0})
    hass.states.get.return_value = st_2c
    anomaly, desc = evaluate_zone_anomalies(coordinator, hass, cid, state, boiler_on=False)
    assert anomaly == ANOMALY_NONE

    # 2. Temperature of -5.0°C (sub-zero room)
    st_subzero = MagicMock(attributes={"current_temperature": -5.0, "temperature": 18.0})
    hass.states.get.return_value = st_subzero
    state["last_temp_seen"] = -5.0
    anomaly, desc = evaluate_zone_anomalies(coordinator, hass, cid, state, boiler_on=False)
    assert anomaly == ANOMALY_NONE

    # 3. Physically impossible temperature (-35.0°C or 70°C) -> ANOMALY_SENSOR_FAULT
    st_impossible = MagicMock(attributes={"current_temperature": -35.0, "temperature": 18.0})
    hass.states.get.return_value = st_impossible
    anomaly, desc = evaluate_zone_anomalies(coordinator, hass, cid, state, boiler_on=False)
    assert anomaly == ANOMALY_SENSOR_FAULT

    # 4. Sudden jump > 4°C within 10 min (from 2.0°C to 8.0°C) -> ANOMALY_SENSOR_FAULT
    state["last_temp_seen"] = 2.0
    state["last_temp_time"] = time.monotonic()
    st_spike = MagicMock(attributes={"current_temperature": 8.0, "temperature": 18.0})
    hass.states.get.return_value = st_spike
    anomaly, desc = evaluate_zone_anomalies(coordinator, hass, cid, state, boiler_on=False)
    assert anomaly == ANOMALY_SENSOR_FAULT


# ---------------------------------------------------------------------------
# 4.4 OpenTherm command confirmation tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_opentherm_command_timeout_recorded():
    """Verify BOILER_COMMAND_TIMEOUT event is recorded when OpenTherm entity fails to confirm."""
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    # Entity is off/unavailable
    st = MagicMock(state="off", attributes={"temperature": 35.0})
    hass.states.get.return_value = st

    coordinator = MagicMock()
    coordinator.plant_diagnostics = MagicMock()
    coordinator.plant_diagnostics.get_opentherm_diagnostics.return_value = {}
    coordinator.plant_diagnostics._current_boiler_start = None
    coordinator.record_diagnostic_event = MagicMock()

    backend = OpenThermBoilerBackend(hass, coordinator, "climate.ot", 35.0, 75.0)

    # 1. Update with demand 50% -> wanted ON, command queued
    t0 = 1000.0
    with patch("time.monotonic", return_value=t0):
        await backend.async_update(50.0, "Living", False)
        assert backend._pending_command == ("on", t0)
        coordinator.record_diagnostic_event.assert_not_called()

    # 2. Advance time past COMMAND_CONFIRM_TIMEOUT (65s), entity still 'off'
    t1 = t0 + COMMAND_CONFIRM_TIMEOUT + 5.0
    with patch("time.monotonic", return_value=t1):
        await backend.async_update(50.0, "Living", False)
        # Timeout triggered and event recorded
        coordinator.record_diagnostic_event.assert_called_once_with(
            "BOILER_COMMAND_TIMEOUT",
            {"entity": "climate.ot", "command": "on"}
        )
        # Call re-dispatched with updated timestamp
        assert backend._pending_command == ("on", t1)

    # 3. Entity confirms 'heat' -> pending command cleared
    st.state = "heat"
    with patch("time.monotonic", return_value=t1 + 2.0):
        await backend.async_update(50.0, "Living", False)
        assert backend._pending_command is None


@pytest.mark.asyncio
async def test_opentherm_diagnostics_follow_confirmed_flame_state():
    """Verify that boiler diagnostics record confirmed flame telemetry instead of unconfirmed demand."""
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.states.get.return_value = MagicMock(state="heat", attributes={"temperature": 55.0})

    coordinator = MagicMock()
    coordinator.plant_diagnostics = MagicMock()
    coordinator.plant_diagnostics._current_boiler_start = None

    # Telemetry reports flame is FALSE even though demand is 50%
    coordinator.plant_diagnostics.get_opentherm_diagnostics.return_value = {"flame_active": False}

    backend = OpenThermBoilerBackend(hass, coordinator, "climate.ot", 35.0, 75.0)
    await backend.async_update(50.0, "Living", False)

    # Since confirmed_on is False, record_boiler_state(True) is NOT called
    coordinator.plant_diagnostics.record_boiler_state.assert_not_called()

    # When flame_active turns TRUE, record_boiler_state(True) is called
    coordinator.plant_diagnostics.get_opentherm_diagnostics.return_value = {"flame_active": True}
    await backend.async_update(50.0, "Living", False)
    coordinator.plant_diagnostics.record_boiler_state.assert_called_once_with(True)
