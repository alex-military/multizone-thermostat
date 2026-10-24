"""Unit tests for production readiness audit fixes (PROD-01 through PROD-06)."""
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.multizone_thermostat import async_setup_entry, async_unload_entry
from custom_components.multizone_thermostat.boiler.plant_orchestrator import PlantOrchestrator
from custom_components.multizone_thermostat.climate import MultizoneVirtualThermostat
from custom_components.multizone_thermostat.const import (
    CONF_ANTI_SEIZE_BOILER,
    CONF_BOILER_MODE,
    CONF_BOILER_SWITCH,
    CONF_ZONE_NAME,
    CONF_ZONE_SENSOR_TIMEOUT,
    CONF_ZONE_TARGET_TEMP,
    CONF_ZONE_TEMP_SENSOR,
    CONF_ZONES,
    DOMAIN,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    KEY_ANTI_SEIZE_DURATION,
    KEY_ANTI_SEIZE_ENABLED,
    MODE_RELAY,
    make_zone_entity_id,
)
from custom_components.multizone_thermostat.coordinator import MultizoneCoordinator
from custom_components.multizone_thermostat.plant_diagnostics.anomalies import get_opentherm_diagnostics
from custom_components.multizone_thermostat.plant_diagnostics.const import (
    ANOMALY_NONE,
    ANOMALY_SENSOR_TIMEOUT,
    ANOMALY_STALE_SENSOR,
)
from custom_components.multizone_thermostat.plant_diagnostics.engine import PlantDiagnosticsEngine
from custom_components.multizone_thermostat.safety.anti_seize import AntiSeizeManager


@pytest.mark.asyncio
async def test_prod01_climate_sensor_dropout_without_trv_sets_none():
    """Verify timed-out or unavailable external sensor with no TRVs sets current_temperature to None."""
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.master_device_id = "master_1"
    coordinator.calendar_manager.temp_overrides = {}
    hass.data = {DOMAIN: {"entry1": {"coordinator": coordinator}}}

    now = time.time()
    fresh_reported = MagicMock()
    fresh_reported.timestamp.return_value = now - 60  # 1 min ago

    stale_reported = MagicMock()
    stale_reported.timestamp.return_value = now - 7200  # 120 min ago (> 30 min timeout)

    sensor_state = MagicMock(state="21.5", last_reported=fresh_reported)
    hass.states.get = MagicMock(return_value=sensor_state)

    zone_data = {
        CONF_ZONE_NAME: "Studio",
        CONF_ZONE_TEMP_SENSOR: "sensor.studio_temp",
        CONF_ZONE_SENSOR_TIMEOUT: 30,
        CONF_ZONE_TARGET_TEMP: 20.0,
    }
    climate = MultizoneVirtualThermostat(hass=hass, entry_id="entry1", zone_data=zone_data)
    climate.async_write_ha_state = MagicMock()

    climate._update_current_temp()
    assert climate.current_temperature == 21.5

    # Sensor exceeds timeout and no TRVs are configured -> must become None (not stay 21.5)
    sensor_state.last_reported = stale_reported
    changed = climate.check_sensor_staleness()
    assert changed is True
    assert climate.current_temperature is None
    climate.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_prod01_orchestrator_enforces_zero_demand_and_catches_tick_errors():
    """Verify PlantOrchestrator zeroes demand on critical sensor fault or None temp and guards async_tick."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "entry_orch"
    entry.data = {
        CONF_BOILER_MODE: MODE_RELAY,
        CONF_BOILER_SWITCH: "switch.boiler",
        CONF_ZONES: [
            {
                CONF_ZONE_NAME: "Studio",
                CONF_ZONE_TEMP_SENSOR: "sensor.studio_temp",
                CONF_ZONE_SENSOR_TIMEOUT: 30,
            }
        ],
    }
    entry.options = {}

    states = {
        "switch.boiler": MagicMock(state="off"),
        "sensor.studio_temp": MagicMock(state="unavailable", attributes={}),
        make_zone_entity_id("Studio"): MagicMock(
            state="heat",
            attributes={"current_temperature": 19.0, "temperature": 21.0},
        ),
    }
    hass.states.get = MagicMock(side_effect=lambda eid: states.get(eid))
    hass.services.async_call = AsyncMock()

    coord = MultizoneCoordinator(hass, entry)
    coord.set_master_state(True)
    cid = make_zone_entity_id("Studio")

    # Pre-load high demand for the zone
    coord.set_zone_demand(cid, 85.0)

    # Orchestrator must evaluate zone anomalies and zero out the zone demand because sensor is unavailable with no TRVs
    await coord.plant_orchestrator._async_update_boiler()
    assert coord.plant_diagnostics.has_critical_sensor_fault(cid) is True
    assert coord.get_zone_demand(cid) == 0.0

    # Also verify async_tick catches unexpected exceptions without raising
    coord.plant_orchestrator._async_update_boiler = AsyncMock(side_effect=RuntimeError("boom"))
    await coord.plant_orchestrator.async_tick(None)


@pytest.mark.asyncio
async def test_prod02_unload_emergency_off_and_full_storage_flush():
    """Verify unload forces boiler emergency off and flushes window, preset, and settings stores."""
    hass = MagicMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    entry = MagicMock()
    entry.entry_id = "entry_unload"
    entry.data = {CONF_BOILER_MODE: MODE_RELAY, CONF_BOILER_SWITCH: "switch.boiler", CONF_ZONES: []}
    entry.options = {}

    coord = MultizoneCoordinator(hass, entry)
    coord._store.async_save = AsyncMock()
    coord._preset_store.async_save = AsyncMock()
    coord._settings_store.async_save = AsyncMock()
    coord.boiler_backend.async_emergency_off = AsyncMock()
    coord.async_teardown_listeners = MagicMock()

    hass.data = {DOMAIN: {entry.entry_id: {"coordinator": coord}}}

    ok = await async_unload_entry(hass, entry)
    assert ok is True
    coord._store.async_save.assert_awaited_once()
    coord._preset_store.async_save.assert_awaited_once()
    coord._settings_store.async_save.assert_awaited_once()
    coord.boiler_backend.async_emergency_off.assert_awaited_once()
    coord.async_teardown_listeners.assert_called_once()


@pytest.mark.asyncio
async def test_prod03_anti_seize_emergency_off_on_hold_and_exception_cleanup():
    """Verify AntiSeizeManager forces emergency off on HOLD_ON and cleans up on runtime exception."""
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.zones = [{CONF_ZONE_NAME: "Zone 1"}]
    coordinator._valve_delay = 0
    coordinator.get_zone_demand.return_value = 0.0

    def get_data(key, default):
        if key == KEY_ANTI_SEIZE_ENABLED:
            return True
        if key == KEY_ANTI_SEIZE_DURATION:
            return 0.001
        if key == CONF_ANTI_SEIZE_BOILER:
            return True
        return default

    coordinator.get_persistent_data.side_effect = get_data
    coordinator._async_set_hvac_mode = AsyncMock()
    coordinator.boiler_backend = MagicMock()
    coordinator.boiler_backend.async_update = AsyncMock()
    coordinator.boiler_backend.async_emergency_off = AsyncMock()
    coordinator.boiler_backend._status_reason = "HOLD_ON (Min Cycle On: 180s left)"

    zone_st = MagicMock(state=HVAC_MODE_OFF)
    hass.states.get.return_value = zone_st

    anti_seize = AntiSeizeManager(hass, coordinator)
    await anti_seize.async_execute()

    # Because _status_reason starts with HOLD_ON, async_emergency_off must be called
    coordinator.boiler_backend.async_update.assert_any_call(0.0, None, False)
    coordinator.boiler_backend.async_emergency_off.assert_awaited_once()

    # Now simulate an exception during boiler turn-on and verify zones and boiler are restored
    coordinator.boiler_backend.async_emergency_off.reset_mock()
    coordinator._async_set_hvac_mode.reset_mock()
    coordinator.set_zone_demand.reset_mock()

    call_count = 0

    async def fail_on_boiler_on(demand, peak, frost):
        nonlocal call_count
        call_count += 1
        if demand > 0:
            raise RuntimeError("Boiler communication error")

    coordinator.boiler_backend.async_update = AsyncMock(side_effect=fail_on_boiler_on)
    await anti_seize.async_execute()

    # Emergency cleanup must have restored zone to HVAC_MODE_OFF and demand 0.0
    coordinator.set_zone_demand.assert_called_with("climate.multizone_thermostat_zone_1", 0.0)
    coordinator._async_set_hvac_mode.assert_called_with("climate.multizone_thermostat_zone_1", HVAC_MODE_OFF)
    assert anti_seize.is_running is False


@pytest.mark.asyncio
async def test_prod03_last_active_wall_time_restored_across_restarts():
    """Verify coordinator persists last_active_wall_time and restores monotonic offset on load."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "entry_active_time"
    entry.data = {CONF_BOILER_MODE: MODE_RELAY, CONF_BOILER_SWITCH: "switch.boiler", CONF_ZONES: []}
    entry.options = {}

    coord = MultizoneCoordinator(hass, entry)
    coord.reset_last_active_time()
    assert "last_active_wall_time" in coord._settings

    # Simulate 5 days (432000s) elapsed in wall clock before restart
    five_days_ago_wall = time.time() - 432000.0
    coord._store.async_load = AsyncMock(return_value={})
    coord._preset_store.async_load = AsyncMock(return_value={})
    coord._settings_store.async_load = AsyncMock(return_value={"last_active_wall_time": five_days_ago_wall})

    await coord.async_load_storage()
    idle_sec = time.monotonic() - coord.last_active_time
    assert 431990.0 <= idle_sec <= 432010.0


def test_prod04_and_prod06_diagnostics_no_false_alarms():
    """Verify sleeping battery sensors, idle rooms, and OpenTherm 'unknown' fault state do not trigger false alarms."""
    hass = MagicMock()
    hass.data = {}
    coordinator = MagicMock()
    coordinator.hass = hass
    coordinator.is_dhw_active = False
    coordinator.opentherm_entity = "climate.ot_boiler"

    now_wall = time.time()
    last_reported = MagicMock()
    # 6 hours since last report (> default 240 min, but < 24h) on a healthy battery sensor
    last_reported.timestamp.return_value = now_wall - 21600

    sensor_state = MagicMock(state="20.0", attributes={}, last_reported=last_reported)
    climate_state = MagicMock(state="heat", attributes={"current_temperature": 20.0, "temperature": 20.0})

    def mock_get(eid):
        if eid == "sensor.bedroom_temp":
            return sensor_state
        if eid == "climate.multizone_thermostat_bedroom":
            return climate_state
        return None

    hass.states.get = MagicMock(side_effect=mock_get)

    zone_info = {
        "name": "Bedroom",
        "temp_sensor": "sensor.bedroom_temp",
        "sensor_timeout_min": 240,  # default 240 min
        "climates": [],
    }
    coordinator.zones = [zone_info]
    coordinator.zone_manager.get_zone.return_value = zone_info
    coordinator.get_zone_mode.return_value = "primary"
    coordinator.get_master_state.return_value = True
    coordinator.get_zone_demand.return_value = 0.0  # Idle room

    engine = PlantDiagnosticsEngine(coordinator)
    cid = make_zone_entity_id("Bedroom")

    # Simulate 7 hours of constant temperature in an idle room
    engine._zone_anomaly_state[cid]["last_temp_seen"] = 20.0
    engine._zone_anomaly_state[cid]["last_temp_time"] = time.monotonic() - 25200

    anomaly_type, _ = engine.evaluate_zone_anomalies(cid)
    assert anomaly_type == ANOMALY_NONE

    # When boiler is actively heating (boiler_on=True and demand > 0) for > 6 hours with frozen reading -> STALE_SENSOR
    coordinator.get_zone_demand.return_value = 80.0
    engine._current_boiler_start = time.monotonic() - 25200
    anomaly_type, _ = engine.evaluate_zone_anomalies(cid)
    assert anomaly_type == ANOMALY_STALE_SENSOR

    # PROD-06: OpenTherm fault entity with state "unknown" must not trigger fault_active
    ent_reg = MagicMock()
    ot_entry = MagicMock(device_id="dev_ot")
    fault_entry = MagicMock(entity_id="sensor.ot_fault_code", original_device_class=None, device_class=None)
    ent_reg.async_get.return_value = ot_entry
    hass.data["entity_registry"] = ent_reg

    from homeassistant.helpers import entity_registry as er
    orig_entries = getattr(er, "async_entries_for_device", None)
    er.async_entries_for_device = MagicMock(return_value=[fault_entry])
    try:
        hass.states.get = MagicMock(
            side_effect=lambda eid: MagicMock(state="unknown", attributes={})
            if eid == "sensor.ot_fault_code"
            else MagicMock(state="heat", attributes={})
        )
        diag = get_opentherm_diagnostics(coordinator, hass)
        assert diag["fault_active"] is False
    finally:
        if orig_entries is not None:
            er.async_entries_for_device = orig_entries
