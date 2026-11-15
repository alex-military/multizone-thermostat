"""Unit tests specifically verifying all Track 1 beta.6 bugfixes."""
import asyncio
import time
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

from homeassistant.core import State
from homeassistant.components.climate import HVACMode

from custom_components.multizone_thermostat.const import (
    CONF_GRID_EXPORT_INVERTED,
    DEFAULT_GRID_EXPORT_INVERTED,
    CONF_MIN_CYCLE_ON,
    CONF_MIN_CYCLE_OFF,
    CONF_VALVE_DELAY,
    KEY_MIN_CYCLE_ON,
    KEY_MIN_CYCLE_OFF,
    KEY_VALVE_DELAY,
    KEY_HP_MIN_CYCLE_ON,
    KEY_HP_MIN_CYCLE_OFF,
    CONF_ZONE_NAME,
    CONF_ZONE_SPLIT_ROLE,
    SPLIT_ROLE_COOLING_ONLY,
    EMITTER_TYPE_UNDERFLOOR,
    EMITTER_TYPE_RADIATOR,
    CONF_ENERGY_MANAGEMENT_ENABLED,
    CONF_GRID_EXPORT_SENSOR,
    CONF_SOLAR_EXPORT_THRESHOLD,
    CONF_SOLAR_MIN_RUN_TIME,
    CONF_BATTERY_POWER_SENSOR,
    CONF_BATTERY_MAX_DISCHARGE_TIME,
    ZONE_MODE_PRIMARY,
    ZONE_MODE_BYPASS,
    make_zone_entity_id,
)
from custom_components.multizone_thermostat.boiler.heat_pump_backend import CentralHeatPumpBackend
from custom_components.multizone_thermostat.boiler.opentherm_backend import OpenThermBoilerBackend
from custom_components.multizone_thermostat.boiler.relay_backend import RelayBoilerBackend
from custom_components.multizone_thermostat.demand_aggregator import (
    DemandAggregator,
    DEMAND_STRATEGY_WEIGHTED_AVERAGE,
)
from custom_components.multizone_thermostat.safety.anti_seize import AntiSeizeManager
from custom_components.multizone_thermostat.energy.energy_manager import EnergyManager
from custom_components.multizone_thermostat.number import MultizonePersistentNumber
from custom_components.multizone_thermostat.boiler.flow_curve import EMITTER_UNDERFLOOR, EMITTER_RADIATOR


# -----------------------------------------------------------------------------
# 1. const.py constants & aliases
# -----------------------------------------------------------------------------
def test_const_grid_export_inverted_definitions():
    assert CONF_GRID_EXPORT_INVERTED == "grid_export_inverted"
    assert DEFAULT_GRID_EXPORT_INVERTED is False
    assert KEY_MIN_CYCLE_ON == "min_cycle_on"
    assert KEY_MIN_CYCLE_OFF == "min_cycle_off"
    assert KEY_VALVE_DELAY == "valve_opening_delay"


# -----------------------------------------------------------------------------
# 2. heat_pump_backend.py: min_cycle units & dew point filter
# -----------------------------------------------------------------------------
def test_heat_pump_min_cycle_units_conversion():
    """Verify CentralHeatPumpBackend correctly converts minutes (<=60) to seconds."""
    hass = MagicMock()
    coord = MagicMock()
    data = {
        KEY_HP_MIN_CYCLE_ON: 5.0,     # 5 minutes -> 300s
        KEY_HP_MIN_CYCLE_OFF: 360.0,  # 360 seconds (>60) -> 360s
    }
    coord.get_persistent_data = lambda k, d=None: data.get(k, d)

    hp = CentralHeatPumpBackend(hass, coord, "climate", "climate.hp")
    assert hp.min_cycle_on == 300.0
    assert hp.min_cycle_off == 360.0

    hp.set_min_cycle_on(10.0)  # 10 minutes -> 600s
    assert hp.min_cycle_on == 600.0

    hp.set_min_cycle_off(30.0)  # 30 minutes -> 1800s
    assert hp.min_cycle_off == 1800.0

    # Non-numeric or 0 safety
    assert CentralHeatPumpBackend._to_seconds(0) == 0.0
    assert CentralHeatPumpBackend._to_seconds(None) == 0.0
    assert CentralHeatPumpBackend._to_seconds("invalid") == 0.0


def test_heat_pump_dew_point_candidate_filtering():
    """Verify _is_zone_cooling_candidate filters inactive, bypass, and cooling-only split zones."""
    hass = MagicMock()
    coord = MagicMock()
    coord.get_zone_mode = MagicMock(return_value="primary")
    coord._climate_entities = {}
    coord.split_manager = MagicMock()
    coord.split_manager.has_split.return_value = False
    coord.split_manager.is_split_active.return_value = False

    hp = CentralHeatPumpBackend(hass, coord, "climate", "climate.hp")

    # 1. Normal cooling candidate
    z1 = {"name": "Salotto", "emitter_type": EMITTER_TYPE_UNDERFLOOR}
    assert hp._is_zone_cooling_candidate(z1) is True

    # 2. Split role cooling_only -> excluded
    z2 = {"name": "Mansarda", "split_role": "cooling_only"}
    assert hp._is_zone_cooling_candidate(z2) is False

    # 3. Zone in bypass mode -> excluded
    cid3 = make_zone_entity_id("BypassZone")
    coord.get_zone_mode.side_effect = lambda cid: "bypass" if cid == cid3 else "primary"
    z3 = {"name": "BypassZone"}
    assert hp._is_zone_cooling_candidate(z3) is False

    # 4. Zone climate is in HVACMode.OFF -> excluded
    cid4 = make_zone_entity_id("OffZone")
    mock_c = MagicMock()
    mock_c.hvac_mode = HVACMode.OFF
    coord._climate_entities = {cid4: mock_c}
    z4 = {"name": "OffZone"}
    assert hp._is_zone_cooling_candidate(z4) is False

    # 5. Zone climate in HVACMode.HEAT -> excluded
    mock_c.hvac_mode = HVACMode.HEAT
    assert hp._is_zone_cooling_candidate(z4) is False

    # 6. Zone climate in HVACMode.COOL -> accepted
    mock_c.hvac_mode = HVACMode.COOL
    assert hp._is_zone_cooling_candidate(z4) is True

    # 7. Split active on radiator zone -> excluded
    cid7 = make_zone_entity_id("SplitRad")
    coord.split_manager.has_split.side_effect = lambda cid: cid == cid7
    coord.split_manager.is_split_active.side_effect = lambda cid: cid == cid7
    z7 = {"name": "SplitRad", "emitter_type": EMITTER_TYPE_RADIATOR}
    assert hp._is_zone_cooling_candidate(z7) is False

    # 8. Split active on underfloor zone -> STILL candidate (floor condensation protection needed)
    z8 = {"name": "SplitRad", "emitter_type": EMITTER_TYPE_UNDERFLOOR}
    assert hp._is_zone_cooling_candidate(z8) is True


# -----------------------------------------------------------------------------
# 3. opentherm_backend.py: Flow curve & unconditional underfloor cap
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_opentherm_unconditional_underfloor_safety_cap():
    """Verify OpenTherm target_temp is capped to 40.0°C whenever underfloor is present without mixing valve."""
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    st = State("climate.ot_boiler", "heat", {"temperature": 35.0})
    hass.states.get = MagicMock(return_value=st)

    coord = MagicMock()
    coord.has_mixing_valve = False
    coord.zones = [{"name": "Living", "emitter_type": EMITTER_UNDERFLOOR}]
    coord.plant_diagnostics = None

    backend = OpenThermBoilerBackend(hass, coord, "climate.ot_boiler", 30.0, 70.0)

    # 1. 100% demand without outdoor temp -> base mapping would be 70.0°C, capped to 40.0°C
    await backend.async_update(100.0, "Living", False)
    hass.services.async_call.assert_called_with(
        "climate", "set_temperature", {"entity_id": "climate.ot_boiler", "temperature": 40.0}, blocking=False
    )

    # 2. Frost emergency -> capped to 40.0°C
    coord.frost_flow_temp = 55.0
    hass.services.async_call.reset_mock()
    await backend.async_update(0.0, None, True)
    hass.services.async_call.assert_called_with(
        "climate", "set_temperature", {"entity_id": "climate.ot_boiler", "temperature": 40.0}, blocking=False
    )


# -----------------------------------------------------------------------------
# 4. demand_aggregator.py: peak floor in weighted average
# -----------------------------------------------------------------------------
def test_demand_aggregator_weighted_average_peak_floor():
    """Verify peak floor prevents starving active zone in weighted average strategy."""
    agg = DemandAggregator(strategy=DEMAND_STRATEGY_WEIGHTED_AVERAGE)
    za = agg.register_zone("Small", weight=10.0, mode=ZONE_MODE_PRIMARY)
    zb = agg.register_zone("Large", weight=90.0, mode=ZONE_MODE_PRIMARY)

    # Only Small is active at 100% -> raw_avg = (100*10)/100 = 10%, peak floor = 70%
    agg.set_zone_demand(za, 100.0)
    agg.set_zone_demand(zb, 0.0)
    res = agg.calculate()
    assert res.demand == 70.0
    assert res.peak_zone == "Small"

    # Both active: Small at 50%, Large at 80% -> raw_avg = (50*10 + 80*90)/100 = 77% > 0.70*80 (56%)
    agg.set_zone_demand(za, 50.0)
    agg.set_zone_demand(zb, 80.0)
    res = agg.calculate()
    assert res.demand == 77.0


# -----------------------------------------------------------------------------
# 5. safety/anti_seize.py: task guard and cleanup
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_anti_seize_task_guard_and_finally_cleanup():
    """Verify AntiSeizeManager guards against concurrent execution and cleans up task reference."""
    hass = MagicMock()
    coord = MagicMock()
    coord.zones = []
    coord.get_persistent_data.return_value = True

    mgr = AntiSeizeManager(hass, coord)

    # Mock an active task
    mock_task = MagicMock()
    mock_task.done.return_value = False
    mgr._task = mock_task

    # check_anti_seize returns without scheduling new task
    hass.async_create_task.reset_mock()
    mgr.check_anti_seize()
    hass.async_create_task.assert_not_called()

    # trigger_manually returns existing task
    assert mgr.trigger_manually() is mock_task
    hass.async_create_task.assert_not_called()

    # async_execute returns immediately if already running
    mgr._running = True
    await mgr.async_execute()
    # Still True because it returned early before finally
    assert mgr.is_running is True

    # Real execution cleans up in finally
    mgr._running = False
    mock_task.done.return_value = True
    mgr._task = None
    await mgr.async_execute()
    assert mgr.is_running is False
    assert mgr._task is None


# -----------------------------------------------------------------------------
# 6. relay_backend.py: status reason log throttling
# -----------------------------------------------------------------------------
def test_relay_backend_status_reason_log_deduplication():
    """Verify RelayBoilerBackend only logs INFO on structural status changes."""
    hass = MagicMock()
    coord = MagicMock()
    backend = RelayBoilerBackend(hass, coord, "switch.boiler", 5.0, 5.0, 0)

    with patch("custom_components.multizone_thermostat.boiler.relay_backend._LOGGER") as mock_logger:
        # First transition -> logs info
        backend._status_reason = "HOLD_ON - min_cycle_on active (180s remaining)"
        mock_logger.info.assert_called_once()
        mock_logger.debug.assert_not_called()

        # Second transition (same key "HOLD_ON - min_cycle_on active", different seconds) -> logs debug only
        mock_logger.reset_mock()
        backend._status_reason = "HOLD_ON - min_cycle_on active (179s remaining)"
        mock_logger.info.assert_not_called()
        mock_logger.debug.assert_called_once()

        # Structural change -> logs info
        mock_logger.reset_mock()
        backend._status_reason = "OFF - No Demand"
        mock_logger.info.assert_called_once()


# -----------------------------------------------------------------------------
# 7. energy_manager.py: inverted export, hysteresis & min run time hold
# -----------------------------------------------------------------------------
def test_energy_manager_inverted_export_and_hysteresis_hold():
    """Verify inverted export support and surplus hysteresis + solar_min_run_time hold."""
    hass = MagicMock()
    coord = MagicMock()
    config = {
        CONF_ENERGY_MANAGEMENT_ENABLED: True,
        CONF_GRID_EXPORT_SENSOR: "sensor.grid_export",
        CONF_GRID_EXPORT_INVERTED: True,
        CONF_SOLAR_EXPORT_THRESHOLD: 500.0,
        CONF_SOLAR_MIN_RUN_TIME: 10,
    }
    mgr = EnergyManager(hass, coord, config)

    # Export sensor reports -600W (negative = exporting when inverted)
    hass.states.get.return_value = MagicMock(state="-600.0", attributes={})
    assert mgr.get_grid_export() == 600.0
    assert mgr.is_solar_surplus() is True
    assert mgr._surplus_hold_active is True

    # Telemetry drops to 400W: below 500W threshold, BUT above 0.7 * 500 = 350W hysteresis off-threshold!
    hass.states.get.return_value = MagicMock(state="-400.0", attributes={})
    assert mgr.is_solar_surplus() is True

    # Telemetry drops to 200W: below hysteresis off-threshold, but held active by solar_min_run_time!
    hass.states.get.return_value = MagicMock(state="-200.0", attributes={})
    assert mgr.is_solar_surplus() is True

    # Simulate 11 minutes elapsed (> 10 min solar_min_run_time) -> hold expires
    mgr._surplus_active_since -= 660.0
    assert mgr.is_solar_surplus() is False
    assert mgr._surplus_hold_active is False


# -----------------------------------------------------------------------------
# 8. number.py: runtime update propagation
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_number_persistent_updates_propagate_to_coordinator():
    """Verify MultizonePersistentNumber propagates value updates to coordinator runtime setters."""
    coord = MagicMock()
    coord.async_set_persistent_data = AsyncMock()
    coord.set_hp_min_cycle_on = MagicMock()
    coord.set_hp_min_cycle_off = MagicMock()
    coord.set_min_cycle_on = MagicMock()
    coord.set_min_cycle_off = MagicMock()
    coord.set_valve_delay = MagicMock()

    device_info = MagicMock()

    # 1. HP Min cycle on
    num_hp_on = MultizonePersistentNumber(coord, "entry", KEY_HP_MIN_CYCLE_ON, "HP On", 0, 30, 1, "min", "mdi:timer", 5, device_info)
    num_hp_on.async_write_ha_state = MagicMock()
    await num_hp_on.async_set_native_value(15.0)
    coord.async_set_persistent_data.assert_called_with(KEY_HP_MIN_CYCLE_ON, 15.0)
    coord.set_hp_min_cycle_on.assert_called_with(15.0)

    # 2. HP Min cycle off
    num_hp_off = MultizonePersistentNumber(coord, "entry", KEY_HP_MIN_CYCLE_OFF, "HP Off", 0, 30, 1, "min", "mdi:timer", 5, device_info)
    num_hp_off.async_write_ha_state = MagicMock()
    await num_hp_off.async_set_native_value(12.0)
    coord.set_hp_min_cycle_off.assert_called_with(12.0)

    # 3. Boiler Min cycle on
    num_b_on = MultizonePersistentNumber(coord, "entry", KEY_MIN_CYCLE_ON, "Boiler On", 0, 60, 1, "min", "mdi:timer", 5, device_info)
    num_b_on.async_write_ha_state = MagicMock()
    await num_b_on.async_set_native_value(8.0)
    coord.set_min_cycle_on.assert_called_with(8.0)

    # 4. Valve delay
    num_vd = MultizonePersistentNumber(coord, "entry", KEY_VALVE_DELAY, "Valve Delay", 0, 300, 1, "s", "mdi:valve", 0, device_info)
    num_vd.async_write_ha_state = MagicMock()
    await num_vd.async_set_native_value(25.0)
    coord.set_valve_delay.assert_called_with(25.0)
