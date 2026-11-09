"""Unit tests validating Track 1 Pass 3 Backend Core & Control fixes."""
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from homeassistant.components.climate import HVACMode, HVACAction
from homeassistant.core import State, ServiceCall
from homeassistant.const import ATTR_TEMPERATURE

from custom_components.multizone_thermostat.coordinator import MultizoneCoordinator
from custom_components.multizone_thermostat.storage.storage_manager import StorageManager
from custom_components.multizone_thermostat.zone_manager import PreWindowState
from custom_components.multizone_thermostat.climate import MultizoneVirtualThermostat
from custom_components.multizone_thermostat.split.split_controller import SplitZoneManager
from custom_components.multizone_thermostat.zone_controller import ZoneController
from custom_components.multizone_thermostat.boiler.plant_orchestrator import PlantOrchestrator
from custom_components.multizone_thermostat.boiler.heat_pump_backend import CentralHeatPumpBackend
from custom_components.multizone_thermostat.__init__ import _async_register_services
from custom_components.multizone_thermostat.const import (
    CONF_ZONE_NAME,
    CONF_ZONE_SPLIT_CLIMATE,
    CONF_ZONE_SPLIT_ROLE,
    SPLIT_ROLE_COOLING_ONLY,
    SPLIT_ROLE_HEAT_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    HVAC_MODE_OFF,
    DOMAIN,
    make_zone_entity_id,
)


@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.data = {DOMAIN: {}}
    hass.states.get.return_value = None
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=False)
    registered_services = {}

    def _register(domain, service, handler):
        registered_services[(domain, service)] = handler

    hass.services.async_register = MagicMock(side_effect=_register)
    hass._registered_services = registered_services
    return hass


# -----------------------------------------------------------------------------
# 1. can_zone_cool tests
# -----------------------------------------------------------------------------
def test_can_zone_cool_standard_and_radiator_matrix():
    coord = MagicMock()
    coord.can_central_cool.return_value = True
    coord.split_manager = MagicMock()
    coord.split_manager.has_split.return_value = False

    cid_std = make_zone_entity_id("StandardZone")
    cid_rad = make_zone_entity_id("RadiatorZone")
    cid_wall = make_zone_entity_id("WallThermostatZone")
    cid_underfloor = make_zone_entity_id("UnderfloorZone")
    cid_emitter_rad = make_zone_entity_id("EmitterRadiator")
    cid_allow_true = make_zone_entity_id("AllowCoolingTrue")

    coord.zones = [
        # Standard zone: no climates, no switches, no valves, trv_preset_sync default True
        {
            CONF_ZONE_NAME: "StandardZone",
            "climate_entities": [],
            "switch_entities": [],
            "valve_entities": [],
            "trv_preset_sync": True,
        },
        # Radiator zone: TRV climate present, no switches/valves, trv_preset_sync True
        {
            CONF_ZONE_NAME: "RadiatorZone",
            "climate_entities": ["climate.trv1"],
            "switch_entities": [],
            "valve_entities": [],
            "trv_preset_sync": True,
        },
        # Wall thermostat zone: climate entity present, but trv_preset_sync False
        {
            CONF_ZONE_NAME: "WallThermostatZone",
            "climate_entities": ["climate.wall_thermostat"],
            "switch_entities": [],
            "valve_entities": [],
            "trv_preset_sync": False,
        },
        # Underfloor zone: switches present, trv_preset_sync True
        {
            CONF_ZONE_NAME: "UnderfloorZone",
            "climate_entities": [],
            "switch_entities": ["switch.valve1"],
            "valve_entities": [],
            "trv_preset_sync": True,
        },
        # Zone with emitter_type radiator explicitly
        {
            CONF_ZONE_NAME: "EmitterRadiator",
            "emitter_type": "radiator",
            "switch_entities": ["switch.valve1"],
        },
        # Zone with allow_cooling True explicitly
        {
            CONF_ZONE_NAME: "AllowCoolingTrue",
            "allow_cooling": True,
            "emitter_type": "radiator",
        },
    ]

    # Standard zone with default trv_preset_sync must be allowed to cool
    assert MultizoneCoordinator.can_zone_cool(coord, cid_std) is True
    # Radiator zone (TRV sync + climates only) must be blocked
    assert MultizoneCoordinator.can_zone_cool(coord, cid_rad) is False
    # Wall thermostat zone without trv sync can cool
    assert MultizoneCoordinator.can_zone_cool(coord, cid_wall) is True
    # Underfloor zone with switch can cool even with trv_preset_sync True
    assert MultizoneCoordinator.can_zone_cool(coord, cid_underfloor) is True
    # Explicit radiator emitter cannot cool
    assert MultizoneCoordinator.can_zone_cool(coord, cid_emitter_rad) is False
    # Explicit allow_cooling True overrides radiator
    assert MultizoneCoordinator.can_zone_cool(coord, cid_allow_true) is True


# -----------------------------------------------------------------------------
# 2. PreWindowState loading tests
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_coordinator_loads_pre_window_state_as_pre_window_state(mock_hass):
    coord = MagicMock()
    coord._store = MagicMock()
    coord._store.async_load = AsyncMock(
        return_value={"climate.living": {"mode": "heat", "was_off": False}}
    )
    coord._settings_store = MagicMock()
    coord._settings_store.async_load = AsyncMock(return_value={})
    coord._preset_store = MagicMock()
    coord._preset_store.async_load = AsyncMock(return_value={})
    coord._settings = {}
    coord._climate_callbacks = {}
    coord.zone_manager = MagicMock()
    coord.zone_manager._pre_window_state = {}
    coord.storage = MagicMock()
    coord.storage._pre_window_state = {}
    coord.storage.presets_heat = {}
    coord.storage.presets_cool = {}
    coord.demand_aggregator = MagicMock()
    del coord.schedule_manager

    await MultizoneCoordinator.async_load_storage(coord)

    loaded = coord.zone_manager._pre_window_state["climate.living"]
    assert isinstance(loaded, PreWindowState)
    assert loaded == "heat"
    assert loaded.get("was_off") is False


@pytest.mark.asyncio
async def test_storage_manager_converts_pre_window_state(mock_hass):
    sm = StorageManager(mock_hass, "test_entry")
    sm._window_store = MagicMock()
    sm._window_store.async_load = AsyncMock(
        return_value={"climate.zone1": {"mode": "cool", "was_off": True}}
    )
    sm._preset_store = MagicMock()
    sm._preset_store.async_load = AsyncMock(return_value={})
    sm._settings_store = MagicMock()
    sm._settings_store.async_load = AsyncMock(return_value={})

    await sm.async_initialize()
    st = sm._pre_window_state["climate.zone1"]
    assert isinstance(st, PreWindowState)
    assert st == "cool"
    assert st.get("was_off") is True

    # Test saving converts input dicts
    sm._window_store.async_delay_save = MagicMock()
    await sm.async_save_windows({"climate.zone2": {"mode": "heat", "was_off": False}})
    saved = sm._pre_window_state["climate.zone2"]
    assert isinstance(saved, PreWindowState)
    assert saved == "heat"


# -----------------------------------------------------------------------------
# 3. climate.py hvac_modes with SPLIT_ROLE_COOLING_ONLY
# -----------------------------------------------------------------------------
def test_climate_cooling_only_split_retains_heat_when_hydronics_exist(mock_hass):
    coord = MagicMock()
    coord.can_zone_cool.return_value = True
    coord.enable_gas_heater = True
    coord.enable_heat_pump = False
    mock_hass.data[DOMAIN]["entry1"] = {"coordinator": coord}

    # Zone has a cooling-only split AND hydronic switch
    zone_data = {
        CONF_ZONE_NAME: "Living",
        CONF_ZONE_SPLIT_CLIMATE: "climate.split_ac",
        CONF_ZONE_SPLIT_ROLE: SPLIT_ROLE_COOLING_ONLY,
        "switch_entities": ["switch.hydronic_valve"],
    }
    thermostat = MultizoneVirtualThermostat(mock_hass, "entry1", zone_data)

    # Must retain HEAT mode because hydronic valve exists and boiler is enabled!
    assert HVACMode.HEAT in thermostat.hvac_modes
    assert HVACMode.COOL in thermostat.hvac_modes
    assert HVACMode.OFF in thermostat.hvac_modes


def test_climate_cooling_only_split_omits_heat_when_no_hydronics_and_no_boiler(mock_hass):
    coord = MagicMock()
    coord.can_zone_cool.return_value = True
    coord.enable_gas_heater = False
    coord.enable_heat_pump = False
    mock_hass.data[DOMAIN]["entry1"] = {"coordinator": coord}

    # Zone has cooling-only split and NO hydronics
    zone_data = {
        CONF_ZONE_NAME: "Attic",
        CONF_ZONE_SPLIT_CLIMATE: "climate.split_ac",
        CONF_ZONE_SPLIT_ROLE: SPLIT_ROLE_COOLING_ONLY,
        "climate_entities": [],
        "switch_entities": [],
        "valve_entities": [],
    }
    thermostat = MultizoneVirtualThermostat(mock_hass, "entry1", zone_data)

    # Omit HEAT mode
    assert thermostat.hvac_modes == [HVACMode.COOL, HVACMode.OFF]


# -----------------------------------------------------------------------------
# 4. split_controller cool mode hysteresis & solar freeze guard
# -----------------------------------------------------------------------------
def test_split_controller_cool_hysteresis_and_solar_freeze_guard(mock_hass):
    coord = MagicMock()
    cid = make_zone_entity_id("Living")
    coord.zones = [{
        CONF_ZONE_NAME: "Living",
        CONF_ZONE_SPLIT_CLIMATE: "climate.split_living",
        CONF_ZONE_SPLIT_ROLE: SPLIT_ROLE_HEAT_COOL,
    }]
    energy_mgr = MagicMock()
    energy_mgr.solar_overheat_offset = 2.0
    energy_mgr.solar_min_run_time = 0.0
    coord.energy_manager = energy_mgr

    mgr = SplitZoneManager(mock_hass, coord)

    # 1. Initially OFF (was_active=False): delta = 0.2°C <= 0.3°C -> remains OFF
    mode, target, _ = mgr.evaluate_split_state(cid, 22.2, 22.0, HVAC_MODE_COOL, solar_surplus=False)
    assert mode == HVAC_MODE_OFF

    # 2. delta = 0.4°C > 0.3°C -> turns ON
    mode, target, _ = mgr.evaluate_split_state(cid, 22.4, 22.0, HVAC_MODE_COOL, solar_surplus=False)
    assert mode == HVAC_MODE_COOL
    assert target == 22.0
    assert mgr._split_active_states[cid] is True

    # 3. Now active (was_active=True): delta = 0.1°C > 0.0 -> stays ON thanks to hysteresis
    mode, target, _ = mgr.evaluate_split_state(cid, 22.1, 22.0, HVAC_MODE_COOL, solar_surplus=False)
    assert mode == HVAC_MODE_COOL

    # 4. Reached target: delta = 0.0°C -> turns OFF
    mode, target, _ = mgr.evaluate_split_state(cid, 22.0, 22.0, HVAC_MODE_COOL, solar_surplus=False)
    assert mode == HVAC_MODE_OFF
    assert mgr._split_active_states[cid] is False

    # 5. Solar freeze guard: Room is already cold (e.g. 17.5°C, effective target is clamped to 18.0°C)
    # delta_t_cool = 17.5 - 18.0 = -0.5°C <= 0
    # Solar call must NOT turn split ON and freeze the room!
    mode, target, _ = mgr.evaluate_split_state(cid, 17.5, 20.0, HVAC_MODE_COOL, solar_surplus=True)
    assert mode == HVAC_MODE_OFF


# -----------------------------------------------------------------------------
# 5. zone_controller hydronic solar offset
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_zone_controller_hydronic_solar_offset_heat_and_cool():
    hass = MagicMock()
    coord = MagicMock()
    coord.zones = [{"name": "Salone"}]
    demands = {}
    coord.demand_aggregator = MagicMock()
    coord.demand_aggregator.get_zone_demand = MagicMock(side_effect=lambda c: demands.get(c, 0.0))
    coord.demand_aggregator.set_zone_demand = MagicMock(side_effect=lambda c, d: demands.update({c: d}))
    coord.get_zone_demand = coord.demand_aggregator.get_zone_demand
    coord.get_zone_mode = MagicMock(return_value="auto")
    coord.plant_diagnostics = MagicMock()
    coord.plant_diagnostics.has_critical_sensor_fault = MagicMock(return_value=False)
    coord.weather_sensor_id = None
    coord.is_dhw_active = False

    coord.solar_surplus = True
    coord.enable_energy_management = True
    coord.solar_overheat_offset = 1.5
    coord.enable_heat_pump = True
    coord.heat_pump_cooling = True

    zc = ZoneController(hass, coord)
    cid = make_zone_entity_id("Salone")

    # Heat mode: target 20.0 -> boosted to 21.5. Current 21.0 is below 21.5 - 0.3 (21.2) -> 100% demand
    st_heat = State(cid, "heat", {"current_temperature": 21.0, "temperature": 20.0})
    res_heat = await zc.async_update_zone(cid, st_heat)
    assert res_heat == 100.0

    # Cool mode: target 25.0 -> lowered to 23.5. Current 24.0 is above 23.5 + 0.3 (23.8) -> 100% cooling demand
    st_cool = State(cid, "cool", {"current_temperature": 24.0, "temperature": 25.0})
    res_cool = await zc.async_update_zone(cid, st_cool)
    assert res_cool == 100.0


# -----------------------------------------------------------------------------
# 6. plant_orchestrator cooling shutoff & heat_pump_backend valve_delay
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_plant_orchestrator_turns_off_hp_when_hp_cooling_disabled(mock_hass):
    coord = MagicMock()
    coord.get_master_state.return_value = True
    coord.master_hvac_mode = HVAC_MODE_COOL
    coord.enable_heat_pump = True
    coord.heat_pump_cooling = False  # Disabled cooling

    boiler = MagicMock()
    boiler.async_update = AsyncMock()
    hp = MagicMock()
    hp.async_update = AsyncMock()

    orch = PlantOrchestrator(mock_hass, MagicMock(), boiler, coord, heat_pump_backend=hp)
    await orch._async_update_boiler()

    boiler.async_update.assert_called_with(0.0, None, False)
    hp.async_update.assert_called_with(0.0, None, False, hvac_mode=HVAC_MODE_COOL)


@pytest.mark.asyncio
async def test_heat_pump_backend_valve_delay(mock_hass):
    coord = MagicMock()
    hp = CentralHeatPumpBackend(
        mock_hass, coord, "switch", "switch.hp_power",
        valve_delay=10,
    )
    # Initial state is OFF
    mock_hass.states.get.return_value = State("switch.hp_power", "off")

    t0 = 1000.0
    with patch("time.monotonic", return_value=t0):
        # 1st tick at t0: demand 50% -> starts valve delay, does not turn ON switch
        await hp.async_update(50.0, "Living", False, hvac_mode=HVAC_MODE_HEAT)
        assert "WAITING_VALVES" in hp.status_reason
        mock_hass.services.async_call.assert_not_called()

    with patch("time.monotonic", return_value=t0 + 5.0):
        # 2nd tick at t0 + 5s: still waiting
        await hp.async_update(50.0, "Living", False, hvac_mode=HVAC_MODE_HEAT)
        assert "WAITING_VALVES" in hp.status_reason
        mock_hass.services.async_call.assert_not_called()

    with patch("time.monotonic", return_value=t0 + 10.1):
        # 3rd tick at t0 + 10.1s: delay elapsed -> turns ON switch
        await hp.async_update(50.0, "Living", False, hvac_mode=HVAC_MODE_HEAT)
        mock_hass.services.async_call.assert_called_with(
            "switch", "turn_on", {"entity_id": "switch.hp_power"}, blocking=False
        )


# -----------------------------------------------------------------------------
# 7. __init__.py handle_save_schedule_profile supports both flat and nested profile
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_save_schedule_profile_nested_and_flat(mock_hass):
    coord = MagicMock()
    coord.schedule_manager = MagicMock()
    coord.schedule_manager.async_save_profile = AsyncMock()

    mock_hass.data[DOMAIN]["entry1"] = {"coordinator": coord}
    await _async_register_services(mock_hass)

    handler = mock_hass._registered_services[(DOMAIN, "save_schedule_profile")]

    # Flat call format
    call_flat = ServiceCall(
        DOMAIN,
        "save_schedule_profile",
        {
            "profile_id": "flat_prof",
            "name": "Flat Profile",
            "baseline_preset": "eco",
            "days": {"mon": []},
        },
    )
    await handler(call_flat)
    coord.schedule_manager.async_save_profile.assert_called_with(
        "flat_prof",
        {"name": "Flat Profile", "baseline_preset": "eco", "days": {"mon": []}},
    )

    # Nested profile format
    call_nested = ServiceCall(
        DOMAIN,
        "save_schedule_profile",
        {
            "profile": {
                "id": "nested_prof",
                "name": "Nested Profile",
                "baseline_preset": "comfort",
                "days": {"tue": []},
            }
        },
    )
    await handler(call_nested)
    coord.schedule_manager.async_save_profile.assert_called_with(
        "nested_prof",
        {"name": "Nested Profile", "baseline_preset": "comfort", "days": {"tue": []}},
    )
