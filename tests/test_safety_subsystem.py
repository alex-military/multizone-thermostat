import asyncio
import importlib.abc
import importlib.machinery
import sys
import time
from unittest.mock import AsyncMock, MagicMock

# A custom finder to mock ANY homeassistant.* module


import pytest

from custom_components.multizone_thermostat.const import (
    CONF_ANTI_SEIZE_BOILER,
    CONF_ZONE_CLIMATES,
    CONF_ZONE_NAME,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    KEY_ANTI_FROST_ENABLED,
    KEY_ANTI_SEIZE_DURATION,
    KEY_ANTI_SEIZE_ENABLED,
    KEY_ANTI_SEIZE_IDLE_DAYS,
    KEY_FROST_PROTECTION_TEMP,
)
from custom_components.multizone_thermostat.safety.anti_seize import AntiSeizeManager
from custom_components.multizone_thermostat.safety.frost import FrostManager
from custom_components.multizone_thermostat.safety.interlocks import SafetyInterlocks
from custom_components.multizone_thermostat.safety.watchdog import SensorWatchdog


# -------------------------------------------------------------
# 1. Tests for FrostManager
# -------------------------------------------------------------
def test_frost_manager_detection():
    hass = MagicMock()
    coordinator = MagicMock()

    def get_data(key, default):
        if key == KEY_ANTI_FROST_ENABLED:
            return True
        if key == KEY_FROST_PROTECTION_TEMP:
            return 10.0
        return default

    coordinator.get_persistent_data.side_effect = get_data
    coordinator.plant_diagnostics.has_critical_sensor_fault.return_value = False
    frost_mgr = FrostManager(hass, coordinator)

    # Zone entity state: temp is 15.0 -> No frost emergency
    st_warm = MagicMock()
    st_warm.attributes = {"current_temperature": 15.0}
    hass.states.get.return_value = st_warm
    assert frost_mgr.is_zone_in_frost_emergency("climate.zone_1") is False

    # Zone entity state: temp drops to 4.5 -> Frost emergency!
    st_cold = MagicMock()
    st_cold.attributes = {"current_temperature": 4.5}
    hass.states.get.return_value = st_cold
    assert frost_mgr.is_zone_in_frost_emergency("climate.zone_1") is True

    # Fallback to TRV readings if virtual thermostat temp is None
    st_none = MagicMock()
    st_none.attributes = {"current_temperature": None}
    
    trv1 = MagicMock()
    trv1.attributes = {"current_temperature": 3.0}
    trv2 = MagicMock()
    trv2.attributes = {"current_temperature": 5.0}

    def states_get_trv(entity_id):
        if entity_id == "climate.zone_1":
            return st_none
        if entity_id == "climate.trv_1":
            return trv1
        if entity_id == "climate.trv_2":
            return trv2
        return None
    hass.states.get.side_effect = states_get_trv

    zone_mock = {
        CONF_ZONE_NAME: "Zone 1",
        CONF_ZONE_CLIMATES: ["climate.trv_1", "climate.trv_2"],
    }
    coordinator.zone_manager = MagicMock()
    coordinator.zone_manager.get_zone.return_value = zone_mock
    coordinator._get_zone.return_value = zone_mock
    # Average is 4.0 (< 10.0) -> Frost emergency
    assert frost_mgr.is_zone_in_frost_emergency("climate.zone_1") is True


@pytest.mark.asyncio
async def test_frost_manager_actions():
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.zones = [{CONF_ZONE_NAME: "Living Room"}]
    coordinator.get_persistent_data.side_effect = lambda k, d: True if k == KEY_ANTI_FROST_ENABLED else (10.0 if k == KEY_FROST_PROTECTION_TEMP else d)
    coordinator._async_set_hvac_mode = AsyncMock()
    hass.services.async_call = AsyncMock()

    # Zone state is OFF and cold (5.0 deg)
    st = MagicMock()
    st.state = HVAC_MODE_OFF
    st.attributes = {"current_temperature": 5.0}
    hass.states.get.return_value = st
    coordinator.plant_diagnostics.has_critical_sensor_fault.return_value = False
    frost_mgr = FrostManager(hass, coordinator)
    res = await frost_mgr.async_handle_frost_emergencies()
    assert res is True
    # Should force zone to HVAC_MODE_HEAT
    coordinator._async_set_hvac_mode.assert_called_with("climate.multizone_thermostat_living_room", HVAC_MODE_HEAT)
    # Should call set_temperature to frost_temp + 3.0 = 13.0
    hass.services.async_call.assert_called()


# -------------------------------------------------------------
# 2. Tests for AntiSeizeManager
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_anti_seize_execution():
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.zones = [{CONF_ZONE_NAME: "Zone 1"}]
    coordinator._valve_delay = 0.001
    coordinator.last_active_time = time.monotonic() - 2000000  # long idle (> 15 days)

    def get_data(key, default):
        if key == KEY_ANTI_SEIZE_ENABLED:
            return True
        if key == KEY_ANTI_SEIZE_IDLE_DAYS:
            return 15
        if key == KEY_ANTI_SEIZE_DURATION:
            return 0.001  # fraction of min for fast test
        if key == CONF_ANTI_SEIZE_BOILER:
            return True
        return default
    coordinator.get_persistent_data.side_effect = get_data
    coordinator._async_set_hvac_mode = AsyncMock()
    coordinator.boiler_backend = MagicMock()
    coordinator.boiler_backend.async_update = AsyncMock()

    zone_st = MagicMock()
    zone_st.state = HVAC_MODE_OFF
    hass.states.get.return_value = zone_st

    anti_seize = AntiSeizeManager(hass, coordinator)

    await anti_seize.async_execute()

    # 1. Zone set to HEAT
    coordinator._async_set_hvac_mode.assert_any_call("climate.multizone_thermostat_zone_1", HVAC_MODE_HEAT)
    # 2. Boiler turned ON (100%) and then OFF (0%)
    coordinator.boiler_backend.async_update.assert_any_call(100.0, "Anti-Seize", False)
    coordinator.boiler_backend.async_update.assert_any_call(0.0, None, False)
    # 3. Zone restored to pre-state (OFF)
    coordinator._async_set_hvac_mode.assert_called_with("climate.multizone_thermostat_zone_1", HVAC_MODE_OFF)


# -------------------------------------------------------------
# 3. Tests for SensorWatchdog
# -------------------------------------------------------------
def test_sensor_watchdog():
    watchdog = SensorWatchdog()
    now = time.time()
    # 100 seconds ago with timeout of 600s -> Not stale
    assert watchdog.is_sensor_stale(now - 100, 600) is False
    # 1000 seconds ago with timeout of 600s -> Stale!
    assert watchdog.is_sensor_stale(now - 1000, 600) is True

    # TRV fallback computation
    hass = MagicMock()
    trv1 = MagicMock()
    trv1.state = "heat"
    trv1.attributes = {"current_temperature": 20.0}
    trv2 = MagicMock()
    trv2.state = "heat"
    trv2.attributes = {"current_temperature": 22.0}
    trv_unavail = MagicMock()
    trv_unavail.state = "unavailable"

    def states_get(ent):
        if ent == "trv_1":
            return trv1
        if ent == "trv_2":
            return trv2
        if ent == "trv_dead":
            return trv_unavail
        return None
    hass.states.get.side_effect = states_get

    zone = {CONF_ZONE_CLIMATES: ["trv_1", "trv_2", "trv_dead"]}
    avg = watchdog.get_zone_trv_fallback_temp(zone, hass)
    assert avg == 21.0


# -------------------------------------------------------------
# 4. Tests for SafetyInterlocks
# -------------------------------------------------------------
def test_safety_interlocks():
    # Window bypass
    assert SafetyInterlocks.can_bypass_windows(is_frost_emergency=False) is True
    assert SafetyInterlocks.can_bypass_windows(is_frost_emergency=True) is False

    # Boiler fire permissions
    # Master OFF -> False
    ok, reason = SafetyInterlocks.can_boiler_fire(master_state=False, demand=50.0)
    assert ok is False
    assert reason == "MASTER_OFF"

    # DHW active -> False
    ok, reason = SafetyInterlocks.can_boiler_fire(master_state=True, demand=50.0, is_dhw_active=True)
    assert ok is False
    assert reason == "DHW_ACTIVE"

    # Frost emergency -> True even if master OFF
    ok, reason = SafetyInterlocks.can_boiler_fire(master_state=False, demand=0.0, frost_emergency=True)
    assert ok is True
    assert reason == "FROST_EMERGENCY"

    # Normal running -> True
    ok, reason = SafetyInterlocks.can_boiler_fire(master_state=True, demand=35.0)
    assert ok is True
    assert reason == "DEMAND_ACTIVE"


