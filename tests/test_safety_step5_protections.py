"""Unit tests for Step 5 protections: PDC anti-short-cycling, dew-point, and frost restore."""
import pytest
import time
from unittest.mock import MagicMock, AsyncMock
from homeassistant.core import State
from custom_components.multizone_thermostat.boiler.heat_pump_backend import CentralHeatPumpBackend
from custom_components.multizone_thermostat.safety.frost import FrostManager
from custom_components.multizone_thermostat.const import (
    CONF_ZONE_NAME,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    make_zone_entity_id,
    KEY_ANTI_FROST_ENABLED,
    KEY_FROST_PROTECTION_TEMP,
)


@pytest.mark.asyncio
async def test_heat_pump_anti_short_cycling():
    """Verify heat pump compressor respects min_cycle_on and min_cycle_off (ORACLE-3 / L3)."""
    hass = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    st = State("climate.hp", "off", {"temperature": 40.0})
    hass.states.get = MagicMock(return_value=st)

    coord = MagicMock()
    coord.zones = []
    coord.weather_sensor_id = None

    backend = CentralHeatPumpBackend(
        hass=hass,
        coordinator=coord,
        hp_entity="climate.hp",
        hp_type="climate",
        min_temp=25.0,
        max_temp=55.0,
    )
    backend.min_cycle_on = 10.0   # 10s for fast test
    backend.min_cycle_off = 10.0

    # 1. First start: should turn ON immediately
    await backend.async_update(demand=50.0, peak_zone="Living", frost_emergency=False)
    assert backend._current_running_state is True

    # 2. Immediate request to turn OFF: should be held ON due to min_cycle_on!
    await backend.async_update(demand=0.0, peak_zone="Living", frost_emergency=False)
    assert backend._current_running_state is True
    assert "HOLD_ON" in backend.status_reason

    # 3. Simulate elapsed time beyond min_cycle_on: now turn OFF succeeds
    backend._last_switch_time = time.monotonic() - 15.0
    await backend.async_update(demand=0.0, peak_zone="Living", frost_emergency=False)
    assert backend._current_running_state is False

    # 4. Immediate request to turn ON: should be held OFF due to min_cycle_off!
    await backend.async_update(demand=60.0, peak_zone="Living", frost_emergency=False)
    assert backend._current_running_state is False
    assert "HOLD_OFF" in backend.status_reason


@pytest.mark.asyncio
async def test_cooling_condensation_dew_point_protection():
    """Verify cooling water temp never drops below dew-point + 2.0°C (L4)."""
    hass = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()

    # Weather: 28°C and 65% humidity -> Dew point is approx 20.8°C -> Safe floor > 22.8°C
    weather_st = State("weather.home", "sunny", {"temperature": 28.0, "humidity": 65.0})
    hp_st = State("climate.hp", "cool", {"temperature": 20.0})
    hass.states.get = lambda eid: weather_st if eid == "weather.home" else hp_st

    coord = MagicMock()
    coord.zones = []
    coord.weather_sensor_id = "weather.home"

    backend = CentralHeatPumpBackend(
        hass=hass,
        coordinator=coord,
        hp_entity="climate.hp",
        hp_type="climate",
        cool_min_temp=7.0,  # normally would drop to 7°C
        cool_max_temp=18.0,
        reversible_cooling=True,
    )

    # At 100% cooling demand: water would want to be cool_min_temp (7.0°C)
    # But dew point protection must prevent it from dropping below safe floor
    await backend.async_update(demand=100.0, peak_zone="Living", frost_emergency=False, hvac_mode=HVAC_MODE_COOL)
    safe_floor = backend._calculate_safe_cooling_min_temp()
    assert safe_floor > 18.0


@pytest.mark.asyncio
async def test_frost_setpoint_restoration_with_hysteresis():
    """Verify frost emergency saves user target and restores it upon exit (L6)."""
    hass = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()

    cid = make_zone_entity_id("Salone")
    zone_st = State(cid, "heat", {"current_temperature": 5.0, "temperature": 21.0})
    hass.states.get = MagicMock(return_value=zone_st)

    coord = MagicMock()
    coord.zones = [{CONF_ZONE_NAME: "Salone"}]
    coord.plant_diagnostics.has_critical_sensor_fault.return_value = False

    def get_data(key, default=None):
        if key == KEY_ANTI_FROST_ENABLED:
            return True
        if key == KEY_FROST_PROTECTION_TEMP:
            return 7.0
        return default

    coord.get_persistent_data.side_effect = get_data
    coord._async_set_hvac_mode = AsyncMock()

    mgr = FrostManager(hass, coord)

    # 1. Temp is 5.0°C < 7.0°C -> enters frost emergency, saves user target (21.0°C)
    res = await mgr.async_handle_frost_emergencies()
    assert res is True
    assert mgr._pre_frost_targets[cid] == 21.0

    # 2. Temp rises to 7.5°C (inside hysteresis window < 8.5°C) -> still in frost emergency
    zone_st.attributes["current_temperature"] = 7.5
    res = await mgr.async_handle_frost_emergencies()
    assert res is True

    # 3. Temp rises to 9.0°C (exits hysteresis window >= 8.5°C) -> exits emergency and restores target to 21.0°C
    zone_st.attributes["current_temperature"] = 9.0
    res = await mgr.async_handle_frost_emergencies()
    assert res is False
    assert cid not in mgr._pre_frost_targets

    # Check that set_temperature was called with restored 21.0°C
    hass.services.async_call.assert_any_call(
        "climate",
        "set_temperature",
        {"entity_id": cid, "temperature": 21.0},
        blocking=False,
    )
