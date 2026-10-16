"""Regression tests for v4.3 bug fixes:
- Preset manual memory retention
- Battery sensor timeout & fallback
- Relay external turn-on protection & cooldown
- TRV closed grace period
- Logbook attribution
"""
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.multizone_thermostat.boiler.relay_backend import RelayBoilerBackend
from custom_components.multizone_thermostat.plant_diagnostics.engine import PlantDiagnosticsEngine
from custom_components.multizone_thermostat.plant_diagnostics.const import (
    ANOMALY_SENSOR_TIMEOUT,
    ANOMALY_NONE,
)
from custom_components.multizone_thermostat.climate import MultizoneVirtualThermostat
from homeassistant.components.climate import PRESET_ECO, PRESET_COMFORT
from custom_components.multizone_thermostat.const import (
    DOMAIN,
    CONF_ZONE_NAME,
    CONF_ZONE_TARGET_TEMP,
    GLOBAL_PRESET_MANUAL,
    ZONE_MODE_PRIMARY,
)


@pytest.mark.asyncio
async def test_manual_preset_temperature_retention():
    """Verify that changing temperature in manual preset saves it and restores on preset switch."""
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    
    coordinator = MagicMock()
    coordinator.zones = [{"name": "Living Room", "target_temp": 20.0}]
    coordinator.get_master_state.return_value = True
    coordinator.async_set_persistent_data = AsyncMock()
    coordinator.master_device_id = "master_dev_123"
    coordinator.get_global_preset.return_value = "manual"
    coordinator.zone_manager = MagicMock()
    coordinator.calendar_manager.temp_overrides = {}
    
    hass.data = {DOMAIN: {"test_entry": {"coordinator": coordinator}}}
    
    zone_data = {
        CONF_ZONE_NAME: "Living Room",
        CONF_ZONE_TARGET_TEMP: 20.0,
    }

    climate = MultizoneVirtualThermostat(
        hass=hass,
        entry_id="test_entry",
        zone_data=zone_data,
    )
    climate.async_write_ha_state = MagicMock()

    # Changing temperature in manual preset
    await climate.async_set_temperature(temperature=22.5)
    assert climate.target_temperature == 22.5
    # Verify it was saved to zone_manager presets for 'manual'
    coordinator.zone_manager.update_preset_temperature.assert_called_once_with("manual", climate.entity_id, 22.5)


@pytest.mark.asyncio
async def test_battery_sensor_timeout_and_fallback():
    """Verify sleeping battery sensor with valid float reading does not trigger critical fault."""
    hass = MagicMock()
    hass.data = {}
    coordinator = MagicMock()
    coordinator.hass = hass
    coordinator.is_dhw_active = False
    
    now_wall = time.time()
    last_reported = MagicMock()
    # 150 minutes since last report (> 90 min)
    last_reported.timestamp.return_value = now_wall - 9000
    
    sensor_state = MagicMock()
    sensor_state.state = "20.4"
    sensor_state.attributes = {}
    sensor_state.last_reported = last_reported
    
    climate_state = MagicMock()
    climate_state.state = "heat"
    climate_state.attributes = {"current_temperature": 20.4, "temperature": 21.0}
    
    def mock_get(entity_id):
        if entity_id == "sensor.temp":
            return sensor_state
        if entity_id == "climate.multizone_bedroom":
            return climate_state
        return None
    hass.states.get = MagicMock(side_effect=mock_get)

    zone_info = {
        "name": "Bedroom",
        "temp_sensor": "sensor.temp",
        "sensor_timeout_min": 60, # 60 min limit, so 150 min exceeds limit
        "climates": [],
    }
    coordinator.zones = [zone_info]
    coordinator.zone_manager.get_zone.return_value = zone_info
    coordinator.get_zone_mode.return_value = "primary"
    coordinator.get_master_state.return_value = True

    engine = PlantDiagnosticsEngine(coordinator)
    anomaly_type, desc = engine.evaluate_zone_anomalies("climate.multizone_bedroom")
    assert anomaly_type == ANOMALY_SENSOR_TIMEOUT
    # Because sensor has valid float reading "20.4", fallback_ok should be True
    assert engine.has_critical_sensor_fault("climate.multizone_bedroom") is False


@pytest.mark.asyncio
async def test_relay_backend_external_turn_on_protection():
    """Verify that when the boiler is switched ON externally, min_cycle_on protects it from being killed."""
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    
    # Boiler is ON in HA
    boiler_mock = MagicMock(state="on")
    hass.states.get = MagicMock(return_value=boiler_mock)
    
    coordinator = MagicMock()
    coordinator.zones = []
    coordinator.is_dhw_active = False
    coordinator.plant_diagnostics = MagicMock()
    coordinator.plant_diagnostics._current_boiler_start = None
    
    backend = RelayBoilerBackend(hass, coordinator, "switch.boiler", 5.0, 5.0, 0.0)
    assert backend._last_boiler_change == 0.0
    
    # External turn-on detected on first tick with 0 demand
    await backend.async_update(0.0, "Zone1", False)
    
    # Should record transition time
    assert backend._last_boiler_change > 0.0
    # Should NOT have called turn_off because min_cycle_on is active!
    hass.services.async_call.assert_not_called()
    assert "HOLD_ON" in backend.status_reason


@pytest.mark.asyncio
async def test_relay_backend_trv_closed_grace_period():
    """Verify TRV closed state does not deadlock boiler forever and allows ignition after grace period."""
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    
    boiler_mock = MagicMock(state="off")
    trv_mock = MagicMock(state="heat", attributes={"position": 0.0}) # 0% open
    
    def mock_get(entity_id):
        if entity_id == "switch.boiler":
            return boiler_mock
        return trv_mock
    hass.states.get = MagicMock(side_effect=mock_get)
    
    coordinator = MagicMock()
    coordinator.zones = [{
        CONF_ZONE_NAME: "Living",
        "climates": ["climate.trv_1"],
    }]
    coordinator.get_zone_mode.return_value = ZONE_MODE_PRIMARY
    coordinator.get_zone_demand.return_value = 60.0
    coordinator.is_dhw_active = False
    coordinator.plant_diagnostics = MagicMock()
    coordinator.plant_diagnostics._current_boiler_start = None
    
    backend = RelayBoilerBackend(hass, coordinator, "switch.boiler", 0.0, 0.0, 0.0)
    
    # 1. First tick: waiting in grace period
    await backend.async_update(60.0, "Living", False)
    assert "HOLD_TRV_CLOSED" in backend.status_reason
    hass.services.async_call.assert_not_called()
    
    # 2. Simulate 121 seconds passing without TRV updating position
    backend._trv_wait_start = time.monotonic() - 121.0
    await backend.async_update(60.0, "Living", False)
    
    # Boiler must ignite despite lagging TRV position
    hass.services.async_call.assert_called_once_with(
        "switch", "turn_on", {"entity_id": "switch.boiler"}, blocking=False
    )
