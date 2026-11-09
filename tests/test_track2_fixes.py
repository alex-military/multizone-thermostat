"""Unit tests validating Track 2 fixes: Config Flow, Options Flow, Schedule, Routine, Diagnostics, Sensors, Select."""
import os
import sys
import json
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

# Ensure clean sys.meta_path without stray HomeAssistantMockFinder
sys.meta_path[:] = [
    f for f in sys.meta_path if f.__class__.__name__ != "HomeAssistantMockFinder"
]
if "homeassistant.components.sensor" in sys.modules and isinstance(sys.modules["homeassistant.components.sensor"], MagicMock):
    del sys.modules["homeassistant.components.sensor"]
if "custom_components.multizone_thermostat.sensor" in sys.modules:
    del sys.modules["custom_components.multizone_thermostat.sensor"]

# Base paths
dummy_ha_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "dummy_ha"))
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if dummy_ha_path not in sys.path:
    sys.path.insert(0, dummy_ha_path)
if repo_root not in sys.path:
    sys.path.insert(1, repo_root)

import types
import homeassistant
data_entry_flow_mod = types.ModuleType("homeassistant.data_entry_flow")
data_entry_flow_mod.section = lambda s, o=None: s
sys.modules["homeassistant.data_entry_flow"] = data_entry_flow_mod
homeassistant.data_entry_flow = data_entry_flow_mod

from homeassistant.components.climate.const import HVACMode
from custom_components.multizone_thermostat.const import (
    DOMAIN,
    CONF_ENABLE_GAS_HEATER,
    CONF_ENABLE_HEAT_PUMP,
    CONF_HEAT_PUMP_TYPE,
    CONF_HEAT_PUMP_ENTITY,
    CONF_HEAT_PUMP_COOLING,
    CONF_HEAT_PUMP_MIN_TEMP,
    CONF_HEAT_PUMP_MAX_TEMP,
    CONF_HEAT_PUMP_COOL_MIN_TEMP,
    CONF_HEAT_PUMP_COOL_MAX_TEMP,
    CONF_BOILER_MODE,
    CONF_BOILER_SWITCH,
    MODE_RELAY,
    CONF_ZONE_NAME,
    CONF_ZONE_SPLIT_CLIMATE,
    CONF_ZONE_WINDOW_SENSOR,
    ZONE_MODE_PRIMARY,
    ZONE_MODE_BYPASS,
    GLOBAL_PRESET_MANUAL,
    GLOBAL_PRESET_AWAY,
    GLOBAL_PRESET_SLEEP,
    GLOBAL_PRESET_COMFORT,
    KEY_NIGHT_TIME,
    KEY_MORNING_TIME,
    KEY_AUTO_NIGHT_MODE,
    KEY_PRE_NIGHT_PRESET,
    KEY_PRE_AWAY_PRESET,
    DEFAULT_COOLING_PRESET_TEMPS,
    DEFAULT_PRESET_TEMPS,
    make_zone_entity_id,
)
from custom_components.multizone_thermostat.config_flow.validators import (
    validate_heat_pump_cool_temps,
)
from custom_components.multizone_thermostat.config_flow.options_flow import MultizoneOptionsFlow
from custom_components.multizone_thermostat.zone_manager import ZoneManager
from custom_components.multizone_thermostat.routine_manager import RoutineManager
from custom_components.multizone_thermostat.schedule.manager import ScheduleProfileManager
from custom_components.multizone_thermostat.diagnostics import async_get_config_entry_diagnostics
from custom_components.multizone_thermostat.sensor import MultizoneZoneEnergyClassSensor
from custom_components.multizone_thermostat.select import MultizoneScheduleProfileSelect
from custom_components.multizone_thermostat import async_unload_entry


# 1. Config Flow & Options Flow Tests
@pytest.mark.asyncio
async def test_options_flow_heat_pump_validation():
    """Verify hp_cool_min_temp < hp_cool_max_temp and generator check."""
    flow = MultizoneOptionsFlow()
    flow.hass = MagicMock()
    flow.async_show_form = MagicMock(side_effect=lambda **kwargs: {"type": "form", **kwargs})
    flow.async_create_entry = MagicMock(side_effect=lambda **kwargs: {"type": "create_entry", **kwargs})
    flow.config_entry = MagicMock()
    flow.config_entry.data = {
        CONF_ENABLE_GAS_HEATER: False,
        CONF_ENABLE_HEAT_PUMP: True,
        "zones": [{"name": "Living", "climates": ["climate.trv"]}],
    }
    flow.config_entry.options = {}
    flow._enable_gas = False
    flow._enable_hp = True
    flow._zones = [{"name": "Living", "climates": ["climate.trv"]}]

    # Invalid cooling temperatures
    res = await flow.async_step_edit_heat_pump({
        CONF_ENABLE_HEAT_PUMP: True,
        CONF_HEAT_PUMP_COOLING: True,
        CONF_HEAT_PUMP_COOL_MIN_TEMP: 18.0,
        CONF_HEAT_PUMP_COOL_MAX_TEMP: 10.0,
    })
    assert res["type"] == "form"
    assert res["errors"]["base"] == "hp_temps_invalid"

    # Disabling HP when Gas is already False and no Split in zones -> no_plants_selected
    res2 = await flow.async_step_edit_heat_pump({
        CONF_ENABLE_HEAT_PUMP: False,
        CONF_HEAT_PUMP_COOLING: True,
        CONF_HEAT_PUMP_COOL_MIN_TEMP: 7.0,
        CONF_HEAT_PUMP_COOL_MAX_TEMP: 18.0,
    })
    assert res2["type"] == "form"
    assert res2["errors"]["base"] == "no_plants_selected"

    # If zone has split configured, disabling HP is allowed
    flow._zones[0][CONF_ZONE_SPLIT_CLIMATE] = "climate.ac_split"
    flow._save_options = MagicMock(return_value={"type": "create_entry"})
    res3 = await flow.async_step_edit_heat_pump({
        CONF_ENABLE_HEAT_PUMP: False,
        CONF_HEAT_PUMP_COOLING: True,
        CONF_HEAT_PUMP_COOL_MIN_TEMP: 7.0,
        CONF_HEAT_PUMP_COOL_MAX_TEMP: 18.0,
    })
    assert res3["type"] == "create_entry"


@pytest.mark.asyncio
async def test_options_flow_change_boiler_toggle():
    """Verify change_boiler step allows toggling CONF_ENABLE_GAS_HEATER."""
    flow = MultizoneOptionsFlow()
    flow.hass = MagicMock()
    flow.async_show_form = MagicMock(side_effect=lambda **kwargs: {"type": "form", **kwargs})
    flow.async_create_entry = MagicMock(side_effect=lambda **kwargs: {"type": "create_entry", **kwargs})
    flow.config_entry = MagicMock()
    flow.config_entry.data = {
        CONF_ENABLE_GAS_HEATER: True,
        CONF_ENABLE_HEAT_PUMP: True,
        "zones": [{"name": "Living"}],
    }
    flow.config_entry.options = {}
    flow._save_options = MagicMock(return_value={"type": "create_entry"})

    # Disable gas when HP is active -> succeeds and saves
    flow._enable_gas = True
    flow._enable_hp = True
    res = await flow.async_step_change_boiler({
        CONF_ENABLE_GAS_HEATER: False,
        CONF_BOILER_MODE: MODE_RELAY,
    })
    assert res["type"] == "create_entry"
    assert flow._enable_gas is False

    # Disabling gas when neither HP nor split exists -> error no_plants_selected
    flow._enable_hp = False
    flow._zones = [{"name": "Living"}]
    res2 = await flow.async_step_change_boiler({
        CONF_ENABLE_GAS_HEATER: False,
        CONF_BOILER_MODE: MODE_RELAY,
    })
    assert res2["type"] == "form"
    assert res2["errors"]["base"] == "no_plants_selected"


@pytest.mark.asyncio
async def test_options_flow_save_options_no_double_reload():
    """Verify _save_options does not trigger duplicate reloads."""
    flow = MultizoneOptionsFlow()
    hass = MagicMock()
    flow.hass = hass
    entry = MagicMock()
    entry.entry_id = "entry123"
    entry.data = {}
    entry.options = {}
    entry.update_listeners = [MagicMock()]
    flow.config_entry = entry

    flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})

    res = flow._save_options()
    assert res["type"] == "create_entry"
    hass.config_entries.async_update_entry.assert_called_once()
    hass.async_create_task.assert_not_called()


# 2. Zone Manager & Window Bypass Tests
@pytest.mark.asyncio
async def test_zone_manager_window_restore_off_state():
    """Verify that a zone turned OFF before window opened is restored to OFF upon window close."""
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.zones = [{CONF_ZONE_NAME: "Living", CONF_ZONE_WINDOW_SENSOR: "binary_sensor.window"}]
    coordinator.is_zone_in_frost_emergency.return_value = False
    coordinator._climate_entities = {}
    coordinator._select_entities = {}
    coordinator.record_diagnostic_event = MagicMock()
    coordinator._async_set_hvac_mode = AsyncMock()

    zone_id = make_zone_entity_id("Living")
    mock_climate = MagicMock()
    mock_climate.hvac_mode = HVACMode.OFF
    coordinator._climate_entities[zone_id] = mock_climate

    zm = ZoneManager(hass, coordinator)

    # 1. Open window
    event_open = MagicMock()
    event_open.data = {
        "entity_id": "binary_sensor.window",
        "new_state": MagicMock(state="on"),
    }
    zm.async_on_window_state_changed(event_open)

    assert zone_id in zm._pre_window_state
    saved = zm._pre_window_state[zone_id]
    assert isinstance(saved, dict)
    assert saved["was_off"] is True
    assert saved["mode"] == ZONE_MODE_PRIMARY

    # 2. Close window
    event_close = MagicMock()
    event_close.data = {
        "entity_id": "binary_sensor.window",
        "new_state": MagicMock(state="off"),
    }
    zm.async_on_window_state_changed(event_close)

    assert zone_id not in zm._pre_window_state
    # Verify coordinator._async_set_hvac_mode was called with HVACMode.OFF
    coordinator._async_set_hvac_mode.assert_called_with(zone_id, HVACMode.OFF)


@pytest.mark.asyncio
async def test_zone_manager_window_backward_compatibility():
    """Verify that a legacy string saved in _pre_window_state restores cleanly."""
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.zones = [{CONF_ZONE_NAME: "Bed", CONF_ZONE_WINDOW_SENSOR: "binary_sensor.bed_window"}]
    coordinator.is_zone_in_frost_emergency.return_value = False
    coordinator._climate_entities = {}
    coordinator._select_entities = {}
    coordinator.record_diagnostic_event = MagicMock()

    zone_id = make_zone_entity_id("Bed")
    zm = ZoneManager(hass, coordinator)
    zm._pre_window_state[zone_id] = ZONE_MODE_PRIMARY

    event_close = MagicMock()
    event_close.data = {
        "entity_id": "binary_sensor.bed_window",
        "new_state": MagicMock(state="off"),
    }
    zm.async_on_window_state_changed(event_close)
    assert zone_id not in zm._pre_window_state


# 3. Routine Manager & Manual Setpoint Restoration Tests
@pytest.mark.asyncio
async def test_zone_manager_manual_setpoint_preservation():
    """Verify that manual setpoint is preserved and restored upon return from Away/Night."""
    hass = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    coordinator = MagicMock()
    zone_id = make_zone_entity_id("Salotto")
    coordinator.zones = [{CONF_ZONE_NAME: "Salotto"}]
    mock_climate = MagicMock()
    mock_climate.target_temperature = 22.5
    coordinator._climate_entities = {zone_id: mock_climate}
    coordinator._select_entities = {}

    zm = ZoneManager(hass, coordinator)
    zm.set_global_preset(GLOBAL_PRESET_MANUAL)

    # Transition from manual to Away
    await zm.async_set_global_preset(GLOBAL_PRESET_AWAY)
    assert zm._last_manual_temps.get(zone_id) == 22.5

    # Change mock climate to away temp
    mock_climate.target_temperature = 16.0

    # Transition back to manual (e.g. Returned home)
    await zm.async_set_global_preset(GLOBAL_PRESET_MANUAL)
    # Target temp must be resolved to 22.5
    assert zm.get_preset_temperature(GLOBAL_PRESET_MANUAL, zone_id) == 22.5
    assert mock_climate._target_temperature == 22.5


# 4. Schedule Manager Tests
@pytest.mark.asyncio
async def test_schedule_manager_cooling_preset_and_overrides():
    """Verify schedule manager cooling fallback preset and cooling zone filter."""
    coordinator = MagicMock()
    coordinator.master_hvac_mode = "cool"
    coordinator.zone_manager = MagicMock()
    coordinator.zone_manager.get_preset_temperature.return_value = None

    sm = ScheduleProfileManager(coordinator)

    # 1. In cooling mode, _resolve_preset_temp falls back to DEFAULT_COOLING_PRESET_TEMPS
    temp = sm._resolve_preset_temp("comfort", "climate.zone1")
    assert temp == DEFAULT_COOLING_PRESET_TEMPS["comfort"]

    # In heating mode, falls back to DEFAULT_PRESET_TEMPS
    coordinator.master_hvac_mode = "heat"
    temp_heat = sm._resolve_preset_temp("comfort", "climate.zone1")
    assert temp_heat == DEFAULT_PRESET_TEMPS["comfort"]

    # 2. In cooling mode, record_manual_override ignores heating-only zones
    coordinator.master_hvac_mode = "cool"
    coordinator.can_zone_cool = MagicMock(side_effect=lambda cid: cid == "climate.cool_zone")

    sm.record_manual_override("climate.heat_only", 23.0)
    assert "climate.heat_only" not in sm.manual_overrides

    sm.record_manual_override("climate.cool_zone", 23.0)
    assert "climate.cool_zone" in sm.manual_overrides


# 5. Diagnostics Telemetry Tests
@pytest.mark.asyncio
async def test_diagnostics_telemetry():
    """Verify diagnostics dump contains summer telemetry, HP parameters, split configs, and energy telemetry."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.version = 1
    entry.domain = DOMAIN
    entry.title = "Multizone"
    entry.data = {}
    entry.options = {}

    coordinator = MagicMock()
    coordinator.enable_heat_pump = True
    coordinator.heat_pump_cooling = True
    coordinator.hp_cool_min_temp = 7.0
    coordinator.hp_cool_max_temp = 18.0
    coordinator.heat_pump_backend.status_reason = "idle_cooling"
    coordinator.energy_management_enabled = True
    coordinator.energy_manager.get_diagnostics.return_value = {
        "enabled": True,
        "is_solar_surplus": True,
    }

    zone_id = make_zone_entity_id("Salotto")
    coordinator.zones = [{
        "name": "Salotto",
        "split_climate_entity": "climate.ac_salotto",
        "split_role": "heat_cool",
        "split_solar_priority": True,
        "split_quick_boost": False,
    }]
    coordinator._climate_entities = {}
    coordinator._pids = {}
    coordinator._pids_cool = {}

    mock_autotuner_cool = MagicMock()
    mock_autotuner_cool.state = "completed"
    mock_autotuner_cool.completed_cycles = [1, 2, 3]
    mock_autotuner_cool.required_cycles = 3
    mock_autotuner_cool.kp = 2.5
    mock_autotuner_cool.ki = 0.01
    mock_autotuner_cool.kd = 10.0
    coordinator.zone_controller.get_autotuner.side_effect = lambda cid, mode="heat": mock_autotuner_cool if mode == "cool" else None

    hass.data = {DOMAIN: {entry.entry_id: {"coordinator": coordinator}}}

    diag = await async_get_config_entry_diagnostics(hass, entry)

    # Check coordinator info
    coord_info = diag["coordinator"]
    assert coord_info["enable_heat_pump"] is True
    assert coord_info["heat_pump_cooling"] is True
    assert coord_info["hp_cool_min_temp"] == 7.0
    assert coord_info["hp_cool_max_temp"] == 18.0
    assert coord_info["heat_pump_status_reason"] == "idle_cooling"
    assert coord_info["energy_management_enabled"] is True

    # Check energy management telemetry
    assert diag["energy_management"]["is_solar_surplus"] is True

    # Check zone telemetry
    z_diag = diag["zones"][zone_id]
    assert z_diag["autotuner_cool"]["state"] == "completed"
    assert z_diag["autotuner_cool"]["kp"] == 2.5
    assert z_diag["split"]["split_climate_entity"] == "climate.ac_salotto"
    assert z_diag["split"]["split_role"] == "heat_cool"


# 6. Entity Translations & Naming Tests
def test_sensor_and_select_entity_naming():
    """Verify sensor returns English 'Energy Class' and select uses translation key."""
    hass = MagicMock()
    coordinator = MagicMock()
    sensor = MultizoneZoneEnergyClassSensor(hass, "entry1", "Salotto", "climate.salotto", coordinator)
    assert sensor.name == "Energy Class"
    assert sensor._attr_translation_key == "energy_class"

    select = MultizoneScheduleProfileSelect(coordinator, "entry1")
    assert not hasattr(select, "_attr_name")
    assert select._attr_translation_key == "schedule_profile"


# 7. Translations JSON Verification
def test_translations_json_content():
    """Verify strings.json and translations contain energy_class and menu options."""
    base_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "custom_components", "multizone_thermostat")
    )
    files = ["strings.json", "translations/en.json", "translations/it.json", "translations/de.json", "translations/es.json", "translations/fr.json", "translations/ru.json"]
    for rel_path in files:
        full_path = os.path.join(base_dir, rel_path)
        with open(full_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "energy_class" in data.get("entity", {}).get("sensor", {})
        init_menu = data.get("options", {}).get("step", {}).get("init", {}).get("menu_options", {})
        assert "change_boiler" in init_menu
        assert "edit_heat_pump" in init_menu
        assert "edit_energy_management" in init_menu


# 8. Unload Entry Emergency Off Test
@pytest.mark.asyncio
async def test_unload_entry_emergency_off():
    """Verify heat pump emergency off is called on entry unload."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_entry"
    coordinator = MagicMock()
    coordinator.async_save_storage = AsyncMock()
    coordinator.boiler_backend = AsyncMock()
    coordinator.heat_pump_backend = AsyncMock()
    coordinator.async_teardown_listeners = MagicMock()

    hass.data = {DOMAIN: {entry.entry_id: {"coordinator": coordinator}}}
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    res = await async_unload_entry(hass, entry)
    assert res is True
    coordinator.heat_pump_backend.async_emergency_off.assert_awaited_once()
    coordinator.boiler_backend.async_emergency_off.assert_awaited_once()
