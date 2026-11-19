"""Regression tests for GitHub Issues #15 (Fahrenheit units) and #16 (post-DHW heating)."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from custom_components.multizone_thermostat.climate import MultizoneVirtualThermostat
from custom_components.multizone_thermostat.const import (
    CONF_ZONE_CLIMATES,
    CONF_ZONE_NAME,
    CONF_ZONE_TEMP_SENSOR,
    to_celsius,
)
from custom_components.multizone_thermostat.plant_diagnostics.const import ANOMALY_NONE
from custom_components.multizone_thermostat.plant_diagnostics.engine import PlantDiagnosticsEngine
from custom_components.multizone_thermostat.safety.watchdog import SensorWatchdog
from custom_components.multizone_thermostat.zone_controller import (
    ZoneController,
    make_zone_entity_id,
)


def test_to_celsius_conversions():
    """Verify Fahrenheit, Kelvin, Celsius and HA unit-system fallback conversions."""
    assert to_celsius(68.0, "°F") == pytest.approx(20.0)
    assert to_celsius(32.0, "F") == pytest.approx(0.0)
    assert to_celsius(293.15, "K") == pytest.approx(20.0)
    assert to_celsius(21.5, "°C") == pytest.approx(21.5)

    hass_f = SimpleNamespace(config=SimpleNamespace(units=SimpleNamespace(temperature_unit="°F")))
    assert to_celsius(77.0, None, hass_f) == pytest.approx(25.0)
    assert to_celsius(20.0, "°C", hass_f) == pytest.approx(20.0)


def test_issue_15_fahrenheit_sensor_converted_and_no_fault():
    """Issue #15: Fahrenheit room sensor must convert to Celsius and not trip sensor_fault."""
    states = {
        "sensor.living_room_temp": SimpleNamespace(
            state="68.0",
            attributes={"unit_of_measurement": "°F"},
            last_reported=None,
            last_updated=None,
        )
    }
    hass = MagicMock()
    hass.states.get = MagicMock(side_effect=lambda eid: states.get(eid))
    hass.config = SimpleNamespace(units=SimpleNamespace(temperature_unit="°F"))
    hass.async_create_task = MagicMock(side_effect=lambda coro: coro.close())

    coordinator = MagicMock()
    coordinator.hass = hass
    coordinator.zones = [{CONF_ZONE_NAME: "Living Room", CONF_ZONE_TEMP_SENSOR: "sensor.living_room_temp"}]
    coordinator.get_zone_mode = MagicMock(return_value="primary")
    coordinator.get_master_state = MagicMock(return_value=True)
    coordinator.get_zone_demand = MagicMock(return_value=0.0)
    coordinator.register_climate = MagicMock()

    zone_data = {
        CONF_ZONE_NAME: "Living Room",
        CONF_ZONE_TEMP_SENSOR: "sensor.living_room_temp",
        CONF_ZONE_CLIMATES: [],
    }
    hass.data = {"multizone_thermostat": {"entry_1": {"coordinator": coordinator}}}
    climate = MultizoneVirtualThermostat(hass, "entry_1", zone_data)
    climate.entity_id = make_zone_entity_id("Living Room")
    climate.async_write_ha_state = MagicMock()

    # Initial update via _update_current_temp
    climate._update_current_temp()
    assert climate.current_temperature == pytest.approx(20.0)

    # Event-driven update via _on_temp_changed (71.6 °F == 22.0 °C)
    event = SimpleNamespace(
        data={
            "new_state": SimpleNamespace(
                state="71.6",
                attributes={"unit_of_measurement": "°F"},
            )
        }
    )
    climate._on_temp_changed(event)
    assert climate.current_temperature == pytest.approx(22.0)

    # Sanity check in PlantDiagnostics must see 22.0 °C, not 71.6 °C
    # Simulate HA's ClimateEntity state serialization in Fahrenheit (71.6 °F, target 69.0 °F)
    states[climate.entity_id] = SimpleNamespace(
        state="heat",
        attributes={"current_temperature": 71.6, "temperature": 69.0},
    )
    coordinator.zone_manager = MagicMock()
    coordinator.zone_manager.get_zone = MagicMock(
        return_value={"name": "Living Room", "temp_sensor": "sensor.living_room_temp", "climates": []}
    )
    diag = PlantDiagnosticsEngine(coordinator)
    anomaly, _ = diag.evaluate_zone_anomalies(climate.entity_id)
    assert anomaly == ANOMALY_NONE
    assert diag.has_critical_sensor_fault(climate.entity_id) is False


@pytest.mark.asyncio
async def test_issue_15_climate_state_attributes_in_fahrenheit():
    """Issue #15 follow-up: HA serializes climate attributes in °F; ZoneController & Restorer must convert to °C."""
    from unittest.mock import AsyncMock
    from custom_components.multizone_thermostat.state_restorer import ZoneStateRestorer

    hass = MagicMock()
    hass.config = SimpleNamespace(units=SimpleNamespace(temperature_unit="°F"))
    coord = MagicMock()
    coord.zones = [{"name": "Living Room"}]
    demands = {}
    coord.demand_aggregator = MagicMock()
    coord.demand_aggregator.get_zone_demand = MagicMock(side_effect=lambda cid: demands.get(cid, 0.0))
    coord.demand_aggregator.set_zone_demand = MagicMock(side_effect=lambda cid, d: demands.update({cid: d}))
    coord.get_zone_demand = coord.demand_aggregator.get_zone_demand
    coord.get_zone_mode = MagicMock(return_value="primary")
    coord.plant_diagnostics = MagicMock()
    coord.plant_diagnostics.has_critical_sensor_fault = MagicMock(return_value=False)
    coord.weather_sensor_id = None
    coord.is_dhw_active = False

    zc = ZoneController(hass, coord)
    cid = make_zone_entity_id("Living Room")
    # 68.0 °F (20.0 °C) vs target 69.8 °F (21.0 °C) -> delta 1.0 °C -> hysteresis demands 100%
    st = SimpleNamespace(state="heat", attributes={"current_temperature": 68.0, "temperature": 69.8})
    dem = await zc.async_update_zone(cid, st)
    assert dem == 100.0

    # StateRestorer: 69.8 °F -> 21.0 °C
    ent = MagicMock()
    ent.hass = hass
    ent.async_get_last_state = AsyncMock(
        return_value=SimpleNamespace(state="heat", attributes={"temperature": 69.8})
    )
    mode, restored_t = await ZoneStateRestorer.async_restore_state(ent)
    assert mode == "heat"
    assert restored_t == pytest.approx(21.0)


def test_issue_15_trv_fallback_fahrenheit():
    """Issue #15: TRV fallback temperatures in Fahrenheit must convert to Celsius."""
    hass = MagicMock()
    hass.config = SimpleNamespace(units=SimpleNamespace(temperature_unit="°F"))
    hass.states.get = MagicMock(
        return_value=SimpleNamespace(state="heat", attributes={"current_temperature": 68.0})
    )
    avg = SensorWatchdog(hass).get_zone_trv_fallback_temp({CONF_ZONE_CLIMATES: ["climate.trv_1"]}, hass)
    assert avg == pytest.approx(20.0)


@pytest.mark.asyncio
async def test_issue_16_smart_pid_resumes_after_dhw_with_thermal_inertia():
    """Issue #16: Smart PID must resume heating after DHW when current_temp < target despite thermal_inertia."""
    hass = MagicMock()
    coord = MagicMock()
    coord.zones = [{"name": "Cucina"}]
    demands = {}
    coord.demand_aggregator = MagicMock()
    coord.demand_aggregator.get_zone_demand = MagicMock(side_effect=lambda cid: demands.get(cid, 0.0))
    coord.demand_aggregator.set_zone_demand = MagicMock(side_effect=lambda cid, d: demands.update({cid: d}))
    coord.get_zone_demand = coord.demand_aggregator.get_zone_demand
    coord.get_zone_mode = MagicMock(return_value="primary")
    coord.plant_diagnostics = MagicMock()
    coord.plant_diagnostics.has_critical_sensor_fault = MagicMock(return_value=False)
    coord.weather_sensor_id = None
    coord.is_dhw_active = False

    zc = ZoneController(hass, coord)
    cid = make_zone_entity_id("Cucina")
    tuner = zc.get_autotuner(cid)
    tuner.state = tuner.STATE_COMPLETED
    pid = zc.get_pid(cid)
    pid.set_pid_param(kp=20.0, ki=0.05, kd=0.0)
    zc.get_thermal_model(cid).thermal_inertia = 0.4  # effective_target = 19.5 - 0.4 = 19.1

    st_19_1 = SimpleNamespace(state="heat", attributes={"current_temperature": 19.1, "temperature": 19.5})
    st_19_2 = SimpleNamespace(state="heat", attributes={"current_temperature": 19.2, "temperature": 19.5})

    with patch("time.monotonic", return_value=1000.0):
        await zc.async_update_zone(cid, st_19_1)

    # DHW activates and wipes integral
    coord.is_dhw_active = True
    with patch("time.monotonic", return_value=1300.0):
        await zc.async_update_zone(cid, st_19_2)
        assert pid._pid.integral == 0.0

    # DHW ends while current_temp (19.2) < target (19.5), even though effective_target (19.1) <= 19.2
    coord.is_dhw_active = False
    with patch("time.monotonic", return_value=1600.0):
        demand = await zc.async_update_zone(cid, st_19_2)
        assert demand > 0.0


@pytest.mark.asyncio
async def test_issue_16_hysteresis_resumes_at_target_minus_tolerance_despite_inertia():
    """Issue #16: Hysteresis fallback turns ON at target - 0.3 even when thermal_inertia > 0."""
    hass = MagicMock()
    coord = MagicMock()
    coord.zones = [{"name": "Cucina"}]
    demands = {}
    coord.demand_aggregator = MagicMock()
    coord.demand_aggregator.get_zone_demand = MagicMock(side_effect=lambda cid: demands.get(cid, 0.0))
    coord.demand_aggregator.set_zone_demand = MagicMock(side_effect=lambda cid, d: demands.update({cid: d}))
    coord.get_zone_demand = coord.demand_aggregator.get_zone_demand
    coord.get_zone_mode = MagicMock(return_value="primary")
    coord.plant_diagnostics = MagicMock()
    coord.plant_diagnostics.has_critical_sensor_fault = MagicMock(return_value=False)
    coord.weather_sensor_id = None
    coord.is_dhw_active = False

    zc = ZoneController(hass, coord)
    cid = make_zone_entity_id("Cucina")
    zc.get_thermal_model(cid).thermal_inertia = 0.4

    st = SimpleNamespace(state="heat", attributes={"current_temperature": 19.2, "temperature": 19.5})
    demand = await zc.async_update_zone(cid, st)
    assert demand == 100.0


@pytest.mark.asyncio
async def test_issue_14_smart_stop_bypass_no_chattering():
    """Issue #14: Smart Stop bypass latches until target is reached, preventing 10s chattering."""
    hass = MagicMock()
    coord = MagicMock()
    coord.zones = [{"name": "Cucina"}]
    coord.demand_aggregator = MagicMock()
    coord.demand_aggregator.set_zone_demand = MagicMock()
    coord.get_zone_mode = MagicMock(return_value="primary")
    coord.plant_diagnostics = MagicMock()
    coord.plant_diagnostics.has_critical_sensor_fault = MagicMock(return_value=False)
    coord.weather_sensor_id = None
    coord.is_dhw_active = False

    zc = ZoneController(hass, coord)
    cid = make_zone_entity_id("Cucina")
    tuner = zc.get_autotuner(cid)
    tuner.state = tuner.STATE_COMPLETED
    pid = zc.get_pid(cid)
    pid.set_pid_param(kp=100.0, ki=0.05, kd=0.0)
    zc.get_thermal_model(cid).thermal_inertia = 0.3  # effective_target = 21.0 - 0.3 = 20.7

    # Room at 20.8 (< 21.0 target, > 20.7 effective_target) with integral = 0.0
    st_20_8 = SimpleNamespace(state="heat", attributes={"current_temperature": 20.8, "temperature": 21.0})
    st_21_2 = SimpleNamespace(state="heat", attributes={"current_temperature": 21.2, "temperature": 21.0})

    demands = []
    for i in range(6):
        with patch("time.monotonic", return_value=2000.0 + i * 10.0):
            demands.append(await zc.async_update_zone(cid, st_20_8))

    # Demand must stay positive and monotonic (no 0% <-> ~20-38% chattering)
    assert all(d > 0.0 for d in demands)
    assert cid in zc._smart_stop_bypass

    # Reaching/exceeding target clears the latch
    with patch("time.monotonic", return_value=2060.0):
        d_over = await zc.async_update_zone(cid, st_21_2)
    assert d_over == 0.0
    assert cid not in zc._smart_stop_bypass
