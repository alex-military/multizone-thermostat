"""Unit tests for EnergyManager (Phase 11).

Tests solar surplus detection, grid export threshold, battery SoC reserve protection,
external optimizer signal override (EMHASS/Predbat), and heat source priority arbitration.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock

from custom_components.multizone_thermostat.const import (
    CONF_ENERGY_MANAGEMENT_ENABLED,
    CONF_SOLAR_POWER_SENSOR,
    CONF_GRID_EXPORT_SENSOR,
    CONF_BATTERY_SOC_SENSOR,
    CONF_EXTERNAL_SOLAR_OVERRIDE_ENTITY,
    CONF_SOLAR_EXPORT_THRESHOLD,
    CONF_BATTERY_MIN_RESERVE_SOC,
    KEY_ALLOW_SPLIT_HEATING,
    KEY_ALLOW_SPLIT_COOLING,
    KEY_HEAT_SOURCE_PRIORITY,
    DEFAULT_HEAT_SOURCE_PRIORITY,
    SOURCE_PRIORITY_GAS,
    SOURCE_PRIORITY_ELECTRIC,
    SOURCE_PRIORITY_GAS_ONLY,
    SOURCE_PRIORITY_ELECTRIC_ONLY,
)
from custom_components.multizone_thermostat.energy.energy_manager import EnergyManager


class MockState:
    def __init__(self, state, attributes=None):
        self.state = state
        self.attributes = attributes or {}


@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.states = MagicMock()
    hass.bus = MagicMock()
    return hass


@pytest.fixture
def mock_coordinator():
    coord = MagicMock()
    coord._storage_data = {}
    
    def get_persistent(key, default=None):
        return coord._storage_data.get(key, default)
        
    async def set_persistent(key, val):
        coord._storage_data[key] = val

    coord.get_persistent_data = MagicMock(side_effect=get_persistent)
    coord.async_set_persistent_data = AsyncMock(side_effect=set_persistent)
    coord.async_update_all_climates = MagicMock()
    return coord


def test_energy_manager_disabled_by_default(mock_hass, mock_coordinator):
    """Verify that if energy management is disabled, is_solar_surplus is always False."""
    config = {CONF_ENERGY_MANAGEMENT_ENABLED: False}
    mgr = EnergyManager(mock_hass, mock_coordinator, config)

    assert mgr.is_energy_management_enabled() is False
    assert mgr.is_solar_surplus() is False


def test_solar_surplus_via_grid_export(mock_hass, mock_coordinator):
    """Verify surplus detection when grid export exceeds threshold."""
    config = {
        CONF_ENERGY_MANAGEMENT_ENABLED: True,
        CONF_GRID_EXPORT_SENSOR: "sensor.grid_export",
        CONF_SOLAR_EXPORT_THRESHOLD: 500.0,
    }
    mgr = EnergyManager(mock_hass, mock_coordinator, config)

    # Below threshold -> False
    mock_hass.states.get.return_value = MockState("400.0")
    assert mgr.is_solar_surplus() is False

    # At or above threshold -> True
    mock_hass.states.get.return_value = MockState("550.0")
    assert mgr.is_solar_surplus() is True

    # Unit conversion: 0.8 kW -> 800 W >= 500 W -> True
    mock_hass.states.get.return_value = MockState("0.8", {"unit_of_measurement": "kW"})
    assert mgr.is_solar_surplus() is True


def test_battery_reserve_protection_suppresses_surplus(mock_hass, mock_coordinator):
    """Verify that low battery SoC blocks solar surplus even when exporting."""
    config = {
        CONF_ENERGY_MANAGEMENT_ENABLED: True,
        CONF_GRID_EXPORT_SENSOR: "sensor.grid_export",
        CONF_BATTERY_SOC_SENSOR: "sensor.battery_soc",
        CONF_SOLAR_EXPORT_THRESHOLD: 500.0,
        CONF_BATTERY_MIN_RESERVE_SOC: 80.0,
    }
    mgr = EnergyManager(mock_hass, mock_coordinator, config)

    def get_state(eid):
        if eid == "sensor.grid_export":
            return MockState("1200.0")  # High export
        if eid == "sensor.battery_soc":
            return MockState("65.0")  # SoC below 80% reserve
        return None

    mock_hass.states.get.side_effect = get_state

    # Battery not charged enough -> suppress split heating surplus
    assert mgr.is_solar_surplus() is False

    # Now battery reaches 85% -> surplus becomes True
    def get_state_charged(eid):
        if eid == "sensor.grid_export":
            return MockState("1200.0")
        if eid == "sensor.battery_soc":
            return MockState("85.0")
        return None

    mock_hass.states.get.side_effect = get_state_charged
    assert mgr.is_solar_surplus() is True


def test_external_optimizer_override(mock_hass, mock_coordinator):
    """Verify that external signal (EMHASS/Predbat) unconditionally forces surplus."""
    config = {
        CONF_ENERGY_MANAGEMENT_ENABLED: True,
        CONF_EXTERNAL_SOLAR_OVERRIDE_ENTITY: "binary_sensor.emhass_boost",
        CONF_GRID_EXPORT_SENSOR: "sensor.grid_export",
        CONF_BATTERY_SOC_SENSOR: "sensor.battery_soc",
        CONF_BATTERY_MIN_RESERVE_SOC: 90.0,
    }
    mgr = EnergyManager(mock_hass, mock_coordinator, config)

    # Battery is low (40%) and export is 0W, BUT external override is ON!
    def get_state(eid):
        if eid == "binary_sensor.emhass_boost":
            return MockState("on")
        if eid == "sensor.grid_export":
            return MockState("0.0")
        if eid == "sensor.battery_soc":
            return MockState("40.0")
        return None

    mock_hass.states.get.side_effect = get_state
    assert mgr.is_external_override_active() is True
    assert mgr.is_solar_surplus() is True

    # When override turns off, regular sensor telemetry takes back control
    def get_state_off(eid):
        if eid == "binary_sensor.emhass_boost":
            return MockState("off")
        if eid == "sensor.grid_export":
            return MockState("0.0")
        if eid == "sensor.battery_soc":
            return MockState("40.0")
        return None

    mock_hass.states.get.side_effect = get_state_off
    assert mgr.is_external_override_active() is False
    assert mgr.is_solar_surplus() is False


@pytest.mark.asyncio
async def test_runtime_master_permissions_and_source_priority(mock_hass, mock_coordinator):
    """Verify split heating/cooling master toggles and heat source priority arbitration."""
    config = {CONF_ENERGY_MANAGEMENT_ENABLED: True}
    mgr = EnergyManager(mock_hass, mock_coordinator, config)

    # Default permissions
    assert mgr.is_split_heating_allowed() is True
    assert mgr.is_split_cooling_allowed() is True
    assert mgr.get_heat_source_priority() == DEFAULT_HEAT_SOURCE_PRIORITY

    # Change split heating permission
    await mgr.async_set_split_heating_allowed(False)
    assert mgr.is_split_heating_allowed() is False
    mock_coordinator.async_update_all_climates.assert_called()

    # Change heat source priority to gas_priority
    await mgr.async_set_heat_source_priority(SOURCE_PRIORITY_GAS)
    assert mgr.get_heat_source_priority() == SOURCE_PRIORITY_GAS

    # Change heat source priority to electric_only
    await mgr.async_set_heat_source_priority(SOURCE_PRIORITY_ELECTRIC_ONLY)
    assert mgr.get_heat_source_priority() == SOURCE_PRIORITY_ELECTRIC_ONLY

    # Invalid priority raises ValueError
    with pytest.raises(ValueError):
        await mgr.async_set_heat_source_priority("invalid_priority")


def test_energy_diagnostics(mock_hass, mock_coordinator):
    """Verify diagnostics dictionary format."""
    config = {
        CONF_ENERGY_MANAGEMENT_ENABLED: True,
        CONF_SOLAR_POWER_SENSOR: "sensor.solar",
        CONF_GRID_EXPORT_SENSOR: "sensor.export",
        CONF_BATTERY_SOC_SENSOR: "sensor.battery",
    }
    mgr = EnergyManager(mock_hass, mock_coordinator, config)

    mock_hass.states.get.side_effect = lambda eid: MockState("1500.0")
    diag = mgr.get_diagnostics()

    assert diag["enabled"] is True
    assert diag["solar_power_w"] == 1500.0
    assert diag["grid_export_w"] == 1500.0
    assert diag["battery_soc_pct"] == 1500.0
    assert "is_solar_surplus" in diag
    assert "heat_source_priority" in diag


def test_external_optimizer_triggers_split_heating_in_auto_mode(mock_hass, mock_coordinator):
    """Verify end-to-end: external AI signal (EMHASS/Predbat) triggers split heating and decouples gas."""
    from custom_components.multizone_thermostat.split.split_controller import SplitZoneManager
    from custom_components.multizone_thermostat.const import (
        CONF_ZONE_NAME,
        CONF_ZONE_SPLIT_CLIMATE,
        CONF_ZONE_SPLIT_ROLE,
        CONF_ZONE_SPLIT_SOLAR_PRIORITY,
        CONF_ZONE_SPLIT_QUICK_BOOST,
        HVAC_MODE_HEAT,
        HVAC_MODE_OFF,
        make_zone_entity_id,
        KEY_HEAT_SOURCE_PRIORITY,
        SOURCE_PRIORITY_AUTO,
    )

    # 1. Setup EnergyManager with EMHASS signal
    config = {
        CONF_ENERGY_MANAGEMENT_ENABLED: True,
        CONF_EXTERNAL_SOLAR_OVERRIDE_ENTITY: "binary_sensor.emhass_solar_boost",
    }
    energy_mgr = EnergyManager(mock_hass, mock_coordinator, config)
    mock_coordinator.energy_manager = energy_mgr

    # 2. Setup SplitZoneManager with a zone having solar priority
    zone_conf = [{
        CONF_ZONE_NAME: "Salotto",
        CONF_ZONE_SPLIT_CLIMATE: "climate.split_salotto",
        CONF_ZONE_SPLIT_ROLE: "heat_cool",
        CONF_ZONE_SPLIT_SOLAR_PRIORITY: True,
        CONF_ZONE_SPLIT_QUICK_BOOST: False,  # Boost disabled so we isolate pure solar surplus
    }]
    mock_coordinator.zones = zone_conf
    split_mgr = SplitZoneManager(mock_hass, mock_coordinator)
    mock_coordinator.split_manager = split_mgr
    climate_id = make_zone_entity_id("Salotto")

    # Zone is in AUTO mode
    mock_coordinator.get_persistent_data.side_effect = lambda k, d=None: (
        SOURCE_PRIORITY_AUTO if k == KEY_HEAT_SOURCE_PRIORITY else d
    )

    # Room is at 19.5°C, target 20.0°C (delta = 0.5°C)
    # A) EMHASS signal is OFF -> No surplus -> Split is OFF
    mock_hass.states.get.return_value = MockState("off")
    assert energy_mgr.is_solar_surplus() is False
    mode, target, is_heating = split_mgr.evaluate_split_state(
        climate_id=climate_id,
        current_temp=19.5,
        target_temp=20.0,
        zone_hvac_mode=HVAC_MODE_HEAT,
        solar_surplus=energy_mgr.is_solar_surplus(),
    )
    assert mode == HVAC_MODE_OFF
    assert is_heating is False
    assert split_mgr.should_suppress_hydronic_demand(climate_id) is False

    # B) EMHASS signal turns ON! (Solar boost active)
    mock_hass.states.get.return_value = MockState("on")
    assert energy_mgr.is_solar_surplus() is True
    mode, target, is_heating = split_mgr.evaluate_split_state(
        climate_id=climate_id,
        current_temp=19.5,
        target_temp=20.0,
        zone_hvac_mode=HVAC_MODE_HEAT,
        solar_surplus=energy_mgr.is_solar_surplus(),
    )
    assert mode == HVAC_MODE_HEAT
    assert is_heating is True
    # Gas boiler demand is suppressed because split is covering load with free solar electricity!
    assert split_mgr.should_suppress_hydronic_demand(climate_id) is True


def test_emhass_numeric_deferrable_load_and_inverter_clipping(mock_hass, mock_coordinator):
    """Verify EMHASS numeric power sensor (sensor.p_deferrable0) and Inverter Clipping saturation."""
    from custom_components.multizone_thermostat.const import (
        CONF_SOLAR_OVERHEAT_OFFSET,
        CONF_SOLAR_MIN_RUN_TIME,
    )

    config = {
        CONF_ENERGY_MANAGEMENT_ENABLED: True,
        CONF_EXTERNAL_SOLAR_OVERRIDE_ENTITY: "sensor.p_deferrable0",
        CONF_SOLAR_POWER_SENSOR: "sensor.pv_power",
        CONF_GRID_EXPORT_SENSOR: "sensor.grid_export",
        CONF_BATTERY_SOC_SENSOR: "sensor.battery_soc",
        CONF_SOLAR_EXPORT_THRESHOLD: 600.0,
        CONF_BATTERY_MIN_RESERVE_SOC: 50.0,
        CONF_SOLAR_MIN_RUN_TIME: 12,
        CONF_SOLAR_OVERHEAT_OFFSET: 1.5,
    }
    mgr = EnergyManager(mock_hass, mock_coordinator, config)

    # 1. EMHASS allocates 1450 W to deferrable load -> override active!
    def state_emhass_active(eid):
        if eid == "sensor.p_deferrable0":
            return MockState("1450.0", {"unit_of_measurement": "W"})
        return MockState("0.0")

    mock_hass.states.get.side_effect = state_emhass_active
    assert mgr.is_external_override_active() is True
    assert mgr.get_external_override_power() == 1450.0
    assert mgr.is_solar_surplus() is True

    # 2. EMHASS allocates 0 W, but Battery is full (99%) and PV is generating 420W (Zero-Export Clipping)
    def state_clipping(eid):
        if eid == "sensor.p_deferrable0":
            return MockState("0.0", {"unit_of_measurement": "W"})
        if eid == "sensor.battery_soc":
            return MockState("99.0")
        if eid == "sensor.pv_power":
            return MockState("420.0", {"unit_of_measurement": "W"})
        if eid == "sensor.grid_export":
            return MockState("20.0", {"unit_of_measurement": "W"})  # Below 600W export threshold due to zero-export limiter
        return None

    mock_hass.states.get.side_effect = state_clipping
    assert mgr.is_external_override_active() is False
    assert mgr.is_solar_surplus() is True


def test_solar_overheat_offset_and_anti_chatter_hold(mock_hass, mock_coordinator):
    """Verify thermal storage overheat offset (+1.0°C) and compressor anti-chatter hold."""
    from custom_components.multizone_thermostat.split.split_controller import SplitZoneManager
    from custom_components.multizone_thermostat.const import (
        CONF_ZONE_NAME,
        CONF_ZONE_SPLIT_CLIMATE,
        CONF_ZONE_SPLIT_ROLE,
        CONF_ZONE_SPLIT_SOLAR_PRIORITY,
        CONF_SOLAR_MIN_RUN_TIME,
        CONF_SOLAR_OVERHEAT_OFFSET,
        HVAC_MODE_HEAT,
        HVAC_MODE_OFF,
        make_zone_entity_id,
    )

    config = {
        CONF_ENERGY_MANAGEMENT_ENABLED: True,
        CONF_SOLAR_MIN_RUN_TIME: 10,
        CONF_SOLAR_OVERHEAT_OFFSET: 1.0,
    }
    energy_mgr = EnergyManager(mock_hass, mock_coordinator, config)
    mock_coordinator.energy_manager = energy_mgr

    mock_coordinator.zones = [{
        CONF_ZONE_NAME: "Salotto",
        CONF_ZONE_SPLIT_CLIMATE: "climate.split_salotto",
        CONF_ZONE_SPLIT_ROLE: "heat_cool",
        CONF_ZONE_SPLIT_SOLAR_PRIORITY: True,
    }]
    split_mgr = SplitZoneManager(mock_hass, mock_coordinator)
    cid = make_zone_entity_id("Salotto")

    # Room is ALREADY at target (20.0°C == 20.0°C), but solar_surplus is True and overheat_offset is +1.0°C!
    # Effective target becomes 21.0°C -> split turns ON to store free solar thermal energy!
    mode, target, is_heating = split_mgr.evaluate_split_state(
        climate_id=cid,
        current_temp=20.0,
        target_temp=20.0,
        zone_hvac_mode=HVAC_MODE_HEAT,
        solar_surplus=True,
    )
    assert mode == HVAC_MODE_HEAT
    assert is_heating is True

    # Now a brief cloud passes (solar_surplus=False), only a few milliseconds later (< 10 min)
    # Anti-chatter hold keeps split ON!
    mode2, target2, is_heating2 = split_mgr.evaluate_split_state(
        climate_id=cid,
        current_temp=20.0,
        target_temp=20.0,
        zone_hvac_mode=HVAC_MODE_HEAT,
        solar_surplus=False,
    )
    assert mode2 == HVAC_MODE_HEAT
    assert is_heating2 is True

    # Simulate 11 minutes elapsed -> anti-chatter expires and split turns OFF
    split_mgr._solar_run_start_timestamps[cid] -= 660.0
    mode3, target3, is_heating3 = split_mgr.evaluate_split_state(
        climate_id=cid,
        current_temp=20.0,
        target_temp=20.0,
        zone_hvac_mode=HVAC_MODE_HEAT,
        solar_surplus=False,
    )
    assert mode3 == HVAC_MODE_OFF
    assert is_heating3 is False


@pytest.mark.asyncio
async def test_central_heat_pump_backend_and_bivalent_orchestrator(mock_hass, mock_coordinator):
    """Verify PlantOrchestrator drives CentralHeatPumpBackend in solar/electric/cooling modes."""
    from custom_components.multizone_thermostat.boiler.heat_pump_backend import CentralHeatPumpBackend
    from custom_components.multizone_thermostat.boiler.plant_orchestrator import PlantOrchestrator
    from custom_components.multizone_thermostat.const import HP_TYPE_CLIMATE, HVAC_MODE_HEAT, HVAC_MODE_COOL

    mock_hass.services.async_call = AsyncMock()
    mock_hass.states.get.return_value = MockState("off", {"temperature": 25.0})

    boiler_backend = MagicMock()
    boiler_backend.async_update = AsyncMock()
    boiler_backend.async_emergency_off = AsyncMock()

    hp_backend = CentralHeatPumpBackend(
        hass=mock_hass,
        coordinator=mock_coordinator,
        hp_type=HP_TYPE_CLIMATE,
        hp_entity="climate.pdc_centrale",
        min_temp=25.0,
        max_temp=50.0,
        reversible_cooling=True,
    )

    agg_res = MagicMock()
    agg_res.demand = 60.0
    agg_res.peak_zone = "climate.multizone_thermostat_salotto"
    demand_aggregator = MagicMock()
    demand_aggregator.calculate.return_value = agg_res

    mock_coordinator.get_master_state.return_value = True
    mock_coordinator.enable_gas_heater = True
    mock_coordinator.enable_heat_pump = True
    mock_coordinator.heat_pump_cooling = True
    mock_coordinator.master_hvac_mode = HVAC_MODE_HEAT
    mock_coordinator.energy_manager = MagicMock()
    mock_coordinator.energy_manager.get_heat_source_priority.return_value = "auto"

    orch = PlantOrchestrator(mock_hass, demand_aggregator, boiler_backend, mock_coordinator, hp_backend)

    # 1. AUTO mode with Solar Surplus -> Central Heat Pump gets 60% demand (40.0°C flow), Gas gets 0%
    mock_coordinator.energy_manager.is_solar_surplus.return_value = True
    await orch._async_update_boiler()
    boiler_backend.async_update.assert_called_with(0.0, "climate.multizone_thermostat_salotto", False)
    assert any(
        c[0][0] == "climate" and c[0][1] == "set_hvac_mode" and c[0][2]["hvac_mode"] == "heat"
        for c in mock_hass.services.async_call.call_args_list
    )

    # 2. Summer COOL mode -> Gas gets 0%, Central Heat Pump switches to COOL when zone needs cooling
    mock_hass.services.async_call.reset_mock()
    mock_coordinator.master_hvac_mode = HVAC_MODE_COOL
    zone_ent = MagicMock()
    zone_ent.hvac_mode = HVAC_MODE_COOL
    zone_ent.current_temperature = 27.0
    zone_ent.target_temperature = 24.0
    mock_coordinator._climate_entities = {"climate.multizone_thermostat_camera": zone_ent}
    mock_coordinator.get_zone_mode.return_value = "primary"
    mock_coordinator.split_manager = None

    await orch._async_update_boiler()
    boiler_backend.async_update.assert_called_with(0.0, None, False)
    assert any(
        c[0][0] == "climate" and c[0][1] == "set_hvac_mode" and c[0][2]["hvac_mode"] == "cool"
        for c in mock_hass.services.async_call.call_args_list
    )


def test_battery_discharge_guard_and_offgrid_saturation(mock_hass, mock_coordinator):
    """Verify continuous battery discharge guard suppresses surplus and Off-Grid saturation triggers it."""
    from custom_components.multizone_thermostat.const import (
        CONF_BATTERY_POWER_SENSOR,
        CONF_BATTERY_MAX_DISCHARGE_TIME,
        CONF_BATTERY_SOC_SENSOR,
        CONF_SOLAR_POWER_SENSOR,
    )

    config = {
        CONF_ENERGY_MANAGEMENT_ENABLED: True,
        CONF_BATTERY_SOC_SENSOR: "sensor.battery_soc",
        CONF_BATTERY_POWER_SENSOR: "sensor.battery_power",
        CONF_BATTERY_MAX_DISCHARGE_TIME: 5,  # 5 minutes limit
        CONF_BATTERY_MIN_RESERVE_SOC: 80.0,  # 80% reserve for the night
        CONF_SOLAR_POWER_SENSOR: "sensor.pv_power",
    }
    mgr = EnergyManager(mock_hass, mock_coordinator, config)

    # 1. Battery is high (96%), PV is 800W -> Off-Grid saturation triggers surplus!
    def state_offgrid(eid):
        if eid == "sensor.battery_soc":
            return MockState("96.0")
        if eid == "sensor.pv_power":
            return MockState("800.0")
        if eid == "sensor.battery_power":
            return MockState("200.0")  # Charging (+200W)
        return None

    mock_hass.states.get.side_effect = state_offgrid
    assert mgr.is_solar_surplus() is True

    # 2. A cloud passes, PV drops to 0, house starts discharging battery (-1200W)
    def state_discharging(eid):
        if eid == "sensor.battery_soc":
            return MockState("94.0")
        if eid == "sensor.pv_power":
            return MockState("0.0")
        if eid == "sensor.battery_power":
            return MockState("-1200.0")  # Discharging (-1200W)
        return None

    mock_hass.states.get.side_effect = state_discharging
    # First tick: records discharge start, but hasn't exceeded 5 minutes yet
    assert mgr.is_battery_discharging_too_long() is False

    # Simulate 6 minutes of continuous discharge
    mgr._discharge_start_timestamp -= 360.0
    assert mgr.is_battery_discharging_too_long() is True
    # When discharge guard trips, surplus is strictly FALSE to protect night battery reserve!
    assert mgr.is_solar_surplus() is False
