"""Regression tests for Sprint 3 Wave 1 (#1-#15): Fahrenheit E2E, aliases, entities, lifecycle & protocols."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure dummy_ha modules are used cleanly if earlier tests injected mocks
sys.meta_path[:] = [
    f for f in sys.meta_path if f.__class__.__name__ != "HomeAssistantMockFinder"
]
for _mod_name in (
    "homeassistant.components.select",
    "homeassistant.helpers.restore_state",
    "homeassistant.helpers.entity",
):
    if _mod_name in sys.modules and isinstance(sys.modules[_mod_name], MagicMock):
        del sys.modules[_mod_name]

from homeassistant.components.climate import ClimateEntityFeature, HVACAction, HVACMode
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import Event, State

from custom_components.multizone_thermostat import _async_register_services, _migrate_config_data, async_setup_entry
from custom_components.multizone_thermostat.boiler.heat_pump_backend import CentralHeatPumpBackend
from custom_components.multizone_thermostat.boiler.opentherm_backend import OpenThermBoilerBackend
from custom_components.multizone_thermostat.boiler.plant_orchestrator import PlantOrchestrator
from custom_components.multizone_thermostat.binary_sensor import MultizonePlantAnomalyBinarySensor
from custom_components.multizone_thermostat.button import MultizoneResetAutotuneButton
from custom_components.multizone_thermostat.calendar_manager import CalendarManager
from custom_components.multizone_thermostat.climate import MultizoneVirtualThermostat
from custom_components.multizone_thermostat.config_flow.options_flow import MultizoneOptionsFlow
from custom_components.multizone_thermostat.config_flow.validators import validate_zone_input
from custom_components.multizone_thermostat.const import (
    CONF_BOILER_MODE,
    CONF_OPENTHERM_ENTITY,
    CONF_ZONE_NAME,
    CONF_ZONE_SPLIT_CLIMATE,
    CONF_ZONE_SPLIT_ROLE,
    CONF_ZONE_TEMP_SENSOR,
    CONF_ZONE_WINDOW_SENSOR,
    CONF_ZONES,
    DEFAULT_FROST_FLOW_TEMP,
    DOMAIN,
    HP_TYPE_CLIMATE,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    KEY_ANTI_FROST_ENABLED,
    KEY_FROST_FLOW_TEMP,
    KEY_FROST_PROTECTION_TEMP,
    KEY_HEAT_SOURCE_PRIORITY,
    MODE_CENTRAL,
    MODE_OPENTHERM,
    SOURCE_PRIORITY_COMBINED,
    SPLIT_ROLE_COOLING_ONLY,
    VALVE_SCALE_VOLT,
    ZONE_MODE_BYPASS,
    ZONE_MODE_PRIMARY,
    ZONE_MODE_SECONDARY,
    make_zone_entity_id,
)
from custom_components.multizone_thermostat.cooling_policy import CoolingPolicy
from custom_components.multizone_thermostat.diagnostics import async_get_config_entry_diagnostics
from custom_components.multizone_thermostat.listener_manager import ListenerManager
from custom_components.multizone_thermostat.master_controller import MasterController
from custom_components.multizone_thermostat.number import (
    MultizoneProtectionNumber,
    MultizoneZonePIDNumber,
    async_setup_entry as number_async_setup_entry,
)
from custom_components.multizone_thermostat.plant_diagnostics.anomalies import get_opentherm_diagnostics
from custom_components.multizone_thermostat.plant_diagnostics.engine import PlantDiagnosticsEngine
from custom_components.multizone_thermostat.protocols import (
    BoilerBackendProtocol,
    CoordinatorProtocol,
    ZoneControllerProtocol,
)
from custom_components.multizone_thermostat.safety.frost import FrostManager
from custom_components.multizone_thermostat.safety.watchdog import SensorWatchdog
from custom_components.multizone_thermostat.schedule.manager import ScheduleProfileManager
from custom_components.multizone_thermostat.schedule.smart_return import SmartReturnPlanner
from custom_components.multizone_thermostat.sensor import (
    CoolingRateSensor,
    HeatingRateSensor,
    MultizoneBoilerDailyRuntimeSensor,
    MultizonePlantHealthSensor,
    MultizoneZoneRetentionTimeSensor,
    ThermalInertiaSensor,
    async_setup_entry as sensor_async_setup_entry,
)
from custom_components.multizone_thermostat.split.split_controller import SplitZoneManager
from custom_components.multizone_thermostat.switch import (
    MultizoneAntiFrostSwitch,
    MultizonePassiveHeatSwitch,
    MultizoneSchedulerSwitch,
)
from custom_components.multizone_thermostat.sync_manager import ZoneSyncManager
from custom_components.multizone_thermostat.zone_manager import ZoneManager


def _make_hass(unit=UnitOfTemperature.CELSIUS, states=None):
    hass = MagicMock()
    hass.data = {DOMAIN: {}}
    hass.config = MagicMock()
    hass.config.units = MagicMock()
    hass.config.units.temperature_unit = unit
    hass.config.components = set()
    hass.config.path = lambda *parts: str(Path.cwd() / Path(*parts))
    hass.is_running = True
    state_map = dict(states or {})
    hass.states = MagicMock()
    hass.states.get = MagicMock(side_effect=lambda eid: state_map.get(eid))
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.async_create_task = MagicMock(side_effect=lambda coro: coro.close() if asyncio.iscoroutine(coro) else MagicMock())
    hass.async_add_executor_job = AsyncMock(side_effect=lambda fn, *a: fn(*a))
    return hass


# ---------------------------------------------------------------------------
# #1-#8: Fahrenheit End-to-End & Units
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_1_orchestrator_synthetic_state_carries_temperature_unit():
    """#1: _async_refresh_zones_proactively injects Celsius temperature_unit into synthetic state."""
    hass = _make_hass(unit=UnitOfTemperature.FAHRENHEIT)
    coord = MagicMock()
    cid = make_zone_entity_id("Living")
    ent = SimpleNamespace(
        entity_id=cid,
        hvac_mode=HVACMode.HEAT,
        current_temperature=20.0,
        target_temperature=22.0,
        preset_mode=None,
        temperature_unit=UnitOfTemperature.CELSIUS,
    )
    coord._climate_entities = {cid: ent}
    coord.zones = [{CONF_ZONE_NAME: "Living"}]
    coord.resolve_zone_id = lambda x: x
    coord.zone_controller = MagicMock()
    coord.zone_controller.get_pid.return_value = SimpleNamespace(has_evaluated=False)
    captured = {}

    async def _capture(zone_id, state_obj):
        captured["state"] = state_obj
        return 30.0

    coord.zone_controller.async_update_zone = _capture
    coord.demand_aggregator = MagicMock()
    coord.demand_aggregator._zone_demands = {cid: 0.0}
    coord.demand_aggregator.get_zone_demand.return_value = 0.0

    orch = PlantOrchestrator(hass, coord.demand_aggregator, MagicMock(), coord)
    await orch._async_refresh_zones_proactively(force=False)

    assert "state" in captured
    assert captured["state"].attributes["temperature_unit"] == UnitOfTemperature.CELSIUS


def test_2_opentherm_diagnostics_fahrenheit_pressure_and_atmospheric_filter():
    """#2: OpenTherm diagnostics convert °F -> °C, normalize kPa -> bar, and skip atmospheric pressure."""
    ot_id = "climate.ot_boiler"
    hass = _make_hass(
        unit=UnitOfTemperature.FAHRENHEIT,
        states={
            ot_id: State(
                ot_id,
                "heat",
                {
                    "current_temperature": 140.0,  # 60.0 °C
                    "return_temperature": 122.0,   # 50.0 °C (< 54 -> condensing_optimal True)
                    "temperature_unit": UnitOfTemperature.FAHRENHEIT,
                },
            ),
            "sensor.weather_barometric_pressure": State(
                "sensor.weather_barometric_pressure", "1013.25", {"device_class": "atmospheric_pressure", "unit_of_measurement": "hPa"}
            ),
            "sensor.boiler_water_pressure": State(
                "sensor.boiler_water_pressure", "150", {"device_class": "pressure", "unit_of_measurement": "kPa"}
            ),
        },
    )
    reg = MagicMock()
    ot_entry = SimpleNamespace(entity_id=ot_id, device_id="dev_ot", config_entry_id="ce_ot", domain="climate")
    baro_entry = SimpleNamespace(
        entity_id="sensor.weather_barometric_pressure",
        device_id="dev_other",
        config_entry_id="ce_ot",
        domain="sensor",
        original_device_class="atmospheric_pressure",
        device_class="atmospheric_pressure",
    )
    press_entry = SimpleNamespace(
        entity_id="sensor.boiler_water_pressure",
        device_id="dev_ot",
        config_entry_id="ce_ot",
        domain="sensor",
        original_device_class="pressure",
        device_class="pressure",
    )
    reg.async_get = lambda eid: ot_entry if eid == ot_id else None
    hass.data["entity_registry"] = reg

    with (
        patch("homeassistant.helpers.entity_registry.async_get", return_value=reg),
        patch("homeassistant.helpers.entity_registry.async_entries_for_device", return_value=[press_entry]),
        patch("homeassistant.helpers.entity_registry.async_entries_for_config_entry", return_value=[ot_entry, baro_entry, press_entry], create=True),
    ):
        coord = MagicMock()
        coord.boiler_mode = MODE_OPENTHERM
        coord.enable_gas_heater = True
        coord.opentherm_entity = ot_id
        coord.dhw_active_sensor = None
        diag = get_opentherm_diagnostics(coord, hass)

    assert diag["flow_temperature"] == pytest.approx(60.0)
    assert diag["return_temperature"] == pytest.approx(50.0)
    assert diag["condensing_optimal"] is True
    assert diag["water_pressure"] == pytest.approx(1.5)


@pytest.mark.asyncio
async def test_3_set_preset_temperature_converts_fahrenheit_and_services_yaml():
    """#3: set_preset_temperature converts °F to °C; services.yaml accepts up to 95.0."""
    hass = _make_hass(unit=UnitOfTemperature.FAHRENHEIT)
    registered = {}
    hass.services.async_register = lambda dom, name, fn, schema=None: registered.update({name: fn})
    coord = MagicMock()
    coord.zone_manager = MagicMock()
    coord.schedule_manager = MagicMock()
    coord.schedule_manager.async_evaluate_schedule = AsyncMock()
    hass.data[DOMAIN] = {"e1": {"coordinator": coord}}

    await _async_register_services(hass)
    handler = registered["set_preset_temperature"]
    await handler(SimpleNamespace(data={"preset": "comfort", "entity_id": "climate.x", "temperature": 71.6}))

    args = coord.zone_manager.update_preset_temperature.call_args[0]
    assert args[0] == "comfort"
    assert args[1] == "climate.x"
    assert args[2] == pytest.approx(22.0, abs=0.05)

    yaml_text = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "multizone_thermostat"
        / "services.yaml"
    ).read_text(encoding="utf-8")
    assert "max: 95.0" in yaml_text


@pytest.mark.asyncio
async def test_4_global_preset_and_master_controller_no_spurious_manual_override():
    """#4: async_set_global_preset & MasterController use async_apply_internal_target without manual override."""
    hass = _make_hass(unit=UnitOfTemperature.FAHRENHEIT)
    coord = MagicMock()
    cid = make_zone_entity_id("Living")
    coord.zones = [{CONF_ZONE_NAME: "Living"}]
    coord.master_hvac_mode = HVAC_MODE_HEAT
    coord.get_master_state.return_value = True
    coord.can_zone_cool.return_value = True
    coord.resolve_zone_id = lambda x: x
    coord.get_zone_mode.return_value = ZONE_MODE_PRIMARY
    coord.get_zone_demand.return_value = 0.0
    coord.get_global_preset.return_value = "eco"
    coord.get_pid_manual_unlock.return_value = False
    coord.boiler_switch = "switch.boiler"
    coord.demand_aggregator = MagicMock()
    coord.demand_aggregator.get_zone_weight.return_value = 1.0
    coord.async_set_persistent_data = AsyncMock()
    coord.async_update_all_climates = AsyncMock()
    coord._async_save_presets_storage = AsyncMock()
    coord._select_entities = {}
    coord._climate_callbacks = {}
    coord.zone_controller = MagicMock()
    coord.zone_controller.async_update_zone = AsyncMock(return_value=10.0)
    coord.schedule_manager = MagicMock()
    coord.schedule_manager.scheduler_enabled = True
    coord.schedule_manager.manual_overrides = {}
    coord.schedule_manager.smart_start_info = {}
    coord.schedule_manager.get_effective_target.return_value = None
    coord.split_manager = None
    coord.calendar_manager = SimpleNamespace(mode_overrides={})
    coord.plant_diagnostics = None
    hass.data[DOMAIN]["e1"] = {"coordinator": coord}

    climate_ent = MultizoneVirtualThermostat(hass, "e1", {CONF_ZONE_NAME: "Living"})
    climate_ent.async_write_ha_state = MagicMock()
    climate_ent._trigger_trv_sync = AsyncMock()
    coord._climate_entities = {}

    zm = ZoneManager(hass, coord)
    zm._presets_heat = {"eco": {cid: {"target_temp": 18.5}}}
    coord.zone_manager = zm

    # Switching from manual -> eco records manual temp converting °F HA state (71.6 °F -> 22.0 °C) when climate_ent unavailable
    zm._current_global_preset = "manual"
    hass.states.get = MagicMock(return_value=State(cid, "heat", {"temperature": 71.6, "temperature_unit": UnitOfTemperature.FAHRENHEIT}))
    await zm.async_set_global_preset("eco")
    assert zm._last_manual_temps[cid] == pytest.approx(22.0, abs=0.05)

    # Re-register climate_ent and switch back manual -> eco: uses async_apply_internal_target without manual override
    coord._climate_entities = {cid: climate_ent}
    hass.services.async_call.reset_mock()
    coord.schedule_manager.record_manual_override.reset_mock()
    zm._current_global_preset = "manual"
    climate_ent._target_temperature = 21.0
    await zm.async_set_global_preset("eco")
    assert climate_ent._target_temperature == pytest.approx(18.5)
    coord.schedule_manager.record_manual_override.assert_not_called()
    hass.services.async_call.assert_not_called()

    # MasterController.async_apply_master_on also routes via async_apply_internal_target
    ctrl = MasterController(coord)
    ctrl.async_set_hvac_mode = AsyncMock()
    await ctrl.async_apply_master_on()
    assert climate_ent._target_temperature == pytest.approx(18.5)
    coord.schedule_manager.record_manual_override.assert_not_called()
    hass.services.async_call.assert_not_called()


@pytest.mark.asyncio
async def test_5_calendar_and_smart_return_convert_fahrenheit_current_temp():
    """#5: CalendarManager Smart Start and SmartReturnPlanner convert °F state current_temperature."""
    cid = make_zone_entity_id("Living")
    hass = _make_hass(
        unit=UnitOfTemperature.FAHRENHEIT,
        states={cid: State(cid, "heat", {"current_temperature": 62.6, "temperature_unit": UnitOfTemperature.FAHRENHEIT})},  # 17.0 °C
    )
    coord = MagicMock()
    coord.hass = hass
    coord.zones = [{CONF_ZONE_NAME: "Living"}]
    coord._climate_entities = {}
    coord._climate_callbacks = {}
    coord.resolve_zone_id = lambda x: x
    coord.master_hvac_mode = HVAC_MODE_HEAT
    coord.zone_manager = MagicMock()
    coord.zone_manager.current_global_preset = "eco"
    coord.zone_manager.get_preset_temperature.return_value = 21.0
    model = SimpleNamespace(heating_rate=2.0, cooling_rate=0.5, active_cooling_rate=0.0)
    coord.zone_controller = MagicMock()
    coord.zone_controller.thermal_models = {cid: model}
    coord._thermal_models = {cid: model}

    # SmartReturnPlanner
    srp = SmartReturnPlanner(coord, hass)
    assert srp.get_zone_current_temp(cid) == pytest.approx(17.0, abs=0.05)

    # CalendarManager Smart Start: 21.0 - 17.0 = 4.0 °C at 2.0 °C/h -> 2h needed; event starts in 1h -> activates!
    cm = CalendarManager(coord)
    now = datetime(2026, 11, 21, 8, 0, tzinfo=timezone.utc)
    future = {"start": (now + timedelta(hours=1)).isoformat(), "end": (now + timedelta(hours=3)).isoformat(), "summary": "comfort"}
    await cm._async_process_calendar_events([], [future], now)
    assert cm.smart_start_overrides.get(cid) == pytest.approx(21.0)


def test_6_frost_outdoor_fallback_converts_fahrenheit():
    """#6: FrostManager L5 outdoor fallback converts 35 °F -> 1.67 °C (triggers) vs 45 °F -> 7.22 °C (safe)."""
    cid = make_zone_entity_id("Basement")
    coord = MagicMock()
    coord.zones = [{CONF_ZONE_NAME: "Basement"}]
    coord.weather_sensor_id = "sensor.outdoor_temp"
    coord.plant_diagnostics = None
    coord.zone_manager = MagicMock()
    coord.zone_manager.get_zone.return_value = coord.zones[0]
    coord.get_persistent_data = MagicMock(side_effect=lambda k, d=None: True if k == KEY_ANTI_FROST_ENABLED else (10.0 if k == KEY_FROST_PROTECTION_TEMP else d))

    # Case 1: 35.0 °F = 1.67 °C <= 2.0 °C -> Frost emergency!
    hass_cold = _make_hass(
        unit=UnitOfTemperature.FAHRENHEIT,
        states={"sensor.outdoor_temp": State("sensor.outdoor_temp", "35.0", {"unit_of_measurement": UnitOfTemperature.FAHRENHEIT})},
    )
    fm_cold = FrostManager(hass_cold, coord)
    assert fm_cold.is_zone_in_frost_emergency(cid) is True

    # Case 2: 45.0 °F = 7.22 °C > 2.0 °C -> NOT frost emergency!
    hass_mild = _make_hass(
        unit=UnitOfTemperature.FAHRENHEIT,
        states={"sensor.outdoor_temp": State("sensor.outdoor_temp", "45.0", {"unit_of_measurement": UnitOfTemperature.FAHRENHEIT})},
    )
    fm_mild = FrostManager(hass_mild, coord)
    assert fm_mild.is_zone_in_frost_emergency(cid) is False


def test_7_sync_manager_and_split_controller_explicit_state_units():
    """#7: SyncManager and SplitZoneManager convert explicit °F device units even on °C HA."""
    hass_c = _make_hass(
        unit=UnitOfTemperature.CELSIUS,
        states={
            "climate.trv_f": State("climate.trv_f", "heat", {"temperature": 68.0, "temperature_unit": UnitOfTemperature.FAHRENHEIT}),
            "climate.split_f": State("climate.split_f", "heat", {"current_temperature": 77.0, "temperature_unit": UnitOfTemperature.FAHRENHEIT}),
        },
    )
    coord = MagicMock()
    coord.zones = [{CONF_ZONE_NAME: "Living", CONF_ZONE_SPLIT_CLIMATE: "climate.split_f"}]
    coord.resolve_zone_id = lambda x: x

    sm = ZoneSyncManager(hass_c, coord, "Living", "climate.multizone_thermostat_living", ["climate.trv_f"], [], {})
    sm.init_known_targets()
    assert sm._last_known_trv_targets["climate.trv_f"] == pytest.approx(20.0, abs=0.05)

    split_mgr = SplitZoneManager(hass_c, coord)
    cid = make_zone_entity_id("Living")
    # room=20.0, target=21.0, ceiling=77°F=25.0°C (+5°C ceiling offset) -> 21+5 = 26.0°C
    inj = split_mgr.calculate_injected_target(cid, 20.0, 21.0)
    assert inj == pytest.approx(26.0, abs=0.1)


def test_8_number_device_classes_and_sensor_fahrenheit_scaling():
    """#8: Frost numbers expose temperature device_class; duration sensors expose duration; thermal sensors scale to °F."""
    hass_f = _make_hass(unit=UnitOfTemperature.FAHRENHEIT)
    coord = MagicMock()
    coord.zones = [{CONF_ZONE_NAME: "Living"}]
    coord._min_cycle_on = 7
    coord._min_cycle_off = 4
    coord._valve_delay = 20
    coord.is_modulating_plant = True
    coord.enable_heat_pump = False
    model = SimpleNamespace(heating_rate=2.0, cooling_rate=0.5, thermal_inertia=1.0)
    coord.zone_controller = MagicMock()
    coord.zone_controller.get_thermal_model.return_value = model
    coord.zone_controller.get_autotuner.return_value = None
    hass_f.data[DOMAIN]["e1"] = {"coordinator": coord}
    entry = MagicMock(entry_id="e1")

    nums = []
    asyncio.run(number_async_setup_entry(hass_f, entry, nums.extend))
    frost_nums = [n for n in nums if getattr(n, "_key", "") in (KEY_FROST_PROTECTION_TEMP, KEY_FROST_FLOW_TEMP)]
    assert len(frost_nums) == 2
    assert all(getattr(n, "device_class", None) == "temperature" or getattr(n, "_attr_device_class", None) == "temperature" for n in frost_nums)

    cid = make_zone_entity_id("Living")
    hr = HeatingRateSensor(hass_f, "e1", "Living", cid, coord)
    cr = CoolingRateSensor(hass_f, "e1", "Living", cid, coord)
    ti = ThermalInertiaSensor(hass_f, "e1", "Living", cid, coord)
    rt = MultizoneZoneRetentionTimeSensor(hass_f, "e1", "Living", cid, coord)
    dr = MultizoneBoilerDailyRuntimeSensor(hass_f, "e1", coord)

    assert hr.native_unit_of_measurement == "°F/hr"
    assert hr.native_value == pytest.approx(3.6)
    assert cr.native_unit_of_measurement == "°F/hr"
    assert cr.native_value == pytest.approx(0.9)
    assert ti.native_unit_of_measurement == "°F"
    assert ti.native_value == pytest.approx(1.8)
    assert getattr(rt, "_attr_device_class", None) == "duration"
    assert getattr(dr, "_attr_device_class", None) == "duration"


# ---------------------------------------------------------------------------
# #9-#12: Aliases, Collision & Cleanup, Climate, Entity Platforms
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_9_entity_alias_resolution_across_managers():
    """#9: Aliased entity IDs resolve cleanly to canonical zone ID across managers & diagnostics."""
    canon_id = make_zone_entity_id("Living")
    alias_id = "climate.custom_living_alias"
    hass = _make_hass()
    coord = MagicMock()
    coord.zones = [{CONF_ZONE_NAME: "Living", "climate_id": canon_id, CONF_ZONE_SPLIT_CLIMATE: "climate.split_l"}]
    coord.resolve_zone_id = lambda eid: canon_id if eid == alias_id else eid
    coord.enable_heat_pump = True
    coord.heat_pump_cooling = True
    coord.enable_gas_heater = False
    coord.master_hvac_mode = HVAC_MODE_HEAT
    coord._settings = {}

    zm = ZoneManager(hass, coord)
    zm.set_zone_mode(alias_id, ZONE_MODE_SECONDARY, save_to_preset=False)
    assert zm.get_zone_mode(canon_id) == ZONE_MODE_SECONDARY
    assert zm.get_zone_mode(alias_id) == ZONE_MODE_SECONDARY
    assert zm.get_zone(alias_id)[CONF_ZONE_NAME] == "Living"

    split_mgr = SplitZoneManager(hass, coord)
    coord.split_manager = split_mgr
    assert split_mgr.has_split(alias_id) is True

    policy = CoolingPolicy(coord)
    assert policy.can_zone_cool(alias_id) is True

    sched = ScheduleProfileManager(coord)
    sched.scheduler_enabled = True
    sched.schedule_overrides[canon_id] = 21.5
    assert sched.get_effective_target(alias_id) == 21.5

    diag_eng = PlantDiagnosticsEngine(coord)
    assert diag_eng.has_critical_sensor_fault(alias_id) is False


def test_10_slug_collision_and_remove_zone_full_cleanup():
    """#10: validate_zone_input blocks slug collisions; remove_zone deletes PID & zone entities/devices."""
    errs = validate_zone_input("Room-1", ["climate.trv"], [], ["Room 1"])
    assert errs.get(CONF_ZONE_NAME) == "zone_name_exists"

    flow = MultizoneOptionsFlow()
    flow.hass = _make_hass()
    flow.config_entry = SimpleNamespace(entry_id="entry_rm", data={CONF_ZONES: []}, options={})
    flow._zones = [{CONF_ZONE_NAME: "Room 1"}]

    removed_entities = []
    removed_devices = []
    ent_reg = MagicMock()
    ent_reg.async_get_entity_id = MagicMock(side_effect=lambda dom, domain_key, uid: f"{dom}.fake_{uid}")
    ent_reg.async_remove = MagicMock(side_effect=lambda eid: removed_entities.append(eid))
    ent_reg.async_entries_for_device = MagicMock(return_value=[SimpleNamespace(entity_id="sensor.stray_zone_entity")])
    dev_reg = MagicMock()
    dev_reg.async_get_device = MagicMock(side_effect=lambda identifiers: SimpleNamespace(id="dev_room_1") if (DOMAIN, "entry_rm_zone_room_1") in identifiers else None)
    dev_reg.async_remove_device = MagicMock(side_effect=lambda did: removed_devices.append(did))

    flow._save_options = MagicMock(return_value={"type": "create_entry"})
    with (
        patch("homeassistant.helpers.entity_registry.async_get", return_value=ent_reg),
        patch("homeassistant.helpers.entity_registry.async_entries_for_device", side_effect=lambda reg, did, **kw: [SimpleNamespace(entity_id="sensor.stray_zone_entity")]),
        patch("homeassistant.helpers.device_registry.async_get", return_value=dev_reg),
        patch("custom_components.multizone_thermostat.config_flow.options_flow._remove_entity_from_registry"),
    ):
        asyncio.run(flow.async_step_remove_zone({"zone_name": "Room 1"}))

    assert any("_pid_manual_unlock_" in e for e in removed_entities)
    assert any("_pid_kp_" in e for e in removed_entities)
    assert any("_pid_ki_" in e for e in removed_entities)
    assert any("_pid_kd_" in e for e in removed_entities)
    assert any("_reset_autotune_" in e for e in removed_entities)
    assert "sensor.stray_zone_entity" in removed_entities
    assert "dev_room_1" in removed_devices


@pytest.mark.asyncio
async def test_11_climate_turn_on_off_modes_nan_and_hvac_action():
    """#11: Climate supports TURN_ON/TURN_OFF, rejects unsupported mode, ignores NaN, COOL hvac_action uses demand."""
    hass = _make_hass(states={"sensor.t": State("sensor.t", "26.0")})
    coord = MagicMock()
    coord.enable_gas_heater = True
    coord.enable_heat_pump = False
    coord.can_zone_cool.return_value = True
    coord.master_hvac_mode = "cool"
    coord.get_master_state.return_value = True
    coord.get_zone_demand.return_value = 0.0
    coord.get_zone_mode.return_value = ZONE_MODE_PRIMARY
    coord.demand_aggregator.get_zone_weight.return_value = 1.0
    coord.zone_manager.is_passive_heat_allowed.return_value = False
    coord.split_manager = None
    coord.calendar_manager = None
    coord.schedule_manager = None
    coord.plant_diagnostics = None
    coord.zone_controller = None
    hass.data[DOMAIN]["e1"] = {"coordinator": coord}

    ent = MultizoneVirtualThermostat(
        hass,
        "e1",
        {
            CONF_ZONE_NAME: "Attic",
            CONF_ZONE_TEMP_SENSOR: "sensor.t",
            CONF_ZONE_SPLIT_CLIMATE: "climate.split_attic",
            CONF_ZONE_SPLIT_ROLE: SPLIT_ROLE_COOLING_ONLY,
        },
    )
    ent.async_write_ha_state = MagicMock()
    ent._trigger_trv_sync = AsyncMock()
    ent._sync_manager.async_sync_switches = AsyncMock()
    ent._sync_manager.async_sync_proportional_valves = AsyncMock()

    features = getattr(ent, "supported_features", ent._attr_supported_features)
    assert features & ClimateEntityFeature.TURN_ON
    assert features & ClimateEntityFeature.TURN_OFF
    # No local hydronics + cooling-only split -> omits HEAT even with enable_gas_heater=True
    assert ent.hvac_modes == [HVACMode.COOL, HVACMode.OFF]

    # Rejects HVACMode.HEAT when unsupported
    await ent.async_set_hvac_mode(HVACMode.HEAT)
    assert ent.hvac_mode == HVACMode.OFF

    # turn_on selects COOL when master_hvac_mode is cool
    await ent.async_turn_on()
    assert ent.hvac_mode == HVACMode.COOL

    # COOL hvac_action is IDLE when demand == 0 even if current_temp > target + 0.2
    ent._current_temperature = 26.0
    ent._target_temperature = 22.0
    coord.get_zone_demand.return_value = 0.0
    assert ent.hvac_action == HVACAction.IDLE
    coord.get_zone_demand.return_value = 40.0
    assert ent.hvac_action == HVACAction.COOLING

    # turn_off -> OFF
    await ent.async_turn_off()
    assert ent.hvac_mode == HVACMode.OFF

    # NaN temperature ignored safely
    ent._current_temperature = 21.5
    ent._on_temp_changed(Event("state_changed", {"new_state": State("sensor.t", "nan")}))
    assert ent._current_temperature == 21.5


@pytest.mark.asyncio
async def test_12_platform_guards_empty_zones_notifications_switches_numbers():
    """#12: Protection defaults, PID None when idle, empty zones plant sensors, scoped notification, switch/button guards."""
    hass = _make_hass()
    coord = MagicMock()
    coord.zones = []
    coord._min_cycle_on = 12
    coord._min_cycle_off = 9
    coord._valve_delay = 45
    coord.is_modulating_plant = False
    coord.enable_heat_pump = False
    coord.zone_controller = None
    coord.notify_climate = MagicMock()
    coord.async_set_persistent_data = AsyncMock()
    coord.plant_orchestrator = MagicMock()
    coord.plant_orchestrator.async_refresh = AsyncMock()
    hass.data[DOMAIN]["e_empty"] = {"coordinator": coord}
    entry = MagicMock(entry_id="e_empty")

    # Sensor setup still registers 4 plant sensors even when zones == []
    sensors = []
    await sensor_async_setup_entry(hass, entry, sensors.extend)
    assert any(isinstance(s, MultizonePlantHealthSensor) for s in sensors)
    assert len(sensors) == 4

    # Protection number initialized from coordinator config
    nums = []
    await number_async_setup_entry(hass, entry, nums.extend)
    by_key = {getattr(n, "_key", None): n for n in nums if isinstance(n, MultizoneProtectionNumber)}
    assert by_key["min_cycle_on"]._default_val == 12.0
    assert by_key["min_cycle_off"]._default_val == 9.0
    assert by_key["valve_opening_delay"]._default_val == 45.0

    # PID number returns None when tuner is missing or below min_value (e.g. Kp=0 while idle)
    coord.zone_controller = MagicMock()
    coord.zone_controller.get_autotuner.return_value = SimpleNamespace(kp=0.0, ki=0.0, kd=0.0, manual_overrides={}, state="idle")
    pid_kp = MultizoneZonePIDNumber(coord, "e_empty", "Salotto", "Kp", 0.1, 500.0, 0.1, 2)
    assert pid_kp.native_value is None

    # Scheduler switch clears reference on removal; PassiveHeat notifies; AntiFrost refreshes orchestrator
    sched_sw = MultizoneSchedulerSwitch(coord, "e_empty")
    sched_sw.hass = hass
    assert coord._scheduler_switch is sched_sw
    await sched_sw.async_will_remove_from_hass()
    assert coord._scheduler_switch is None

    passive_sw = MultizonePassiveHeatSwitch(coord, "e_empty", "Salotto")
    passive_sw.async_write_ha_state = MagicMock()
    await passive_sw.async_turn_on()
    coord.notify_climate.assert_called_once()

    frost_sw = MultizoneAntiFrostSwitch(coord, "e_empty")
    frost_sw.async_write_ha_state = MagicMock()
    await frost_sw.async_turn_off()
    coord.plant_orchestrator.async_refresh.assert_awaited()

    # Button safe when zone_controller is None
    coord.zone_controller = None
    coord.async_set_pid_manual_unlock = AsyncMock()
    btn = MultizoneResetAutotuneButton(coord, "e_empty", "Salotto")
    await btn.async_press()

    # Binary sensor entry-scoped notification & rollback on service failure
    bs = MultizonePlantAnomalyBinarySensor(coord, "e_empty")
    bs.hass = hass
    bs.async_write_ha_state = MagicMock()
    bs.async_on_remove = MagicMock()
    coord.plant_diagnostics = MagicMock()
    coord.plant_diagnostics.get_plant_health_summary.return_value = {
        "status": "warning",
        "anomalies_count": 1,
        "anomalies": [{"zone": "Living", "description": "Lagging"}],
        "cycles_per_hour": 0,
        "daily_runtime_hours": 1.0,
    }
    captured_cb = []
    with patch("custom_components.multizone_thermostat.binary_sensor.async_track_time_interval", side_effect=lambda h, fn, td: captured_cb.append(fn) or (lambda: None)):
        await bs.async_added_to_hass()
    hass.services.async_call = AsyncMock(side_effect=RuntimeError("notify down"))
    await captured_cb[0](None)
    assert bs._notified_active is False
    hass.services.async_call = AsyncMock()
    await captured_cb[0](None)
    assert bs._notified_active is True
    assert hass.services.async_call.call_args[0][2]["notification_id"] == "multizone_thermostat_plant_anomaly_e_empty"


# ---------------------------------------------------------------------------
# #13-#15: Window Restore, Lifecycle, Protocols, Watchdog & Diagnostics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_13_window_close_when_was_off_does_not_call_select_option():
    """#13 [#14.5]: Restoring window closure when zone was OFF skips zone_select.async_select_option."""
    hass = _make_hass()
    tasks = []

    def _capture_task(coro):
        t = asyncio.create_task(coro)
        tasks.append(t)
        return t

    hass.async_create_task = _capture_task
    cid = make_zone_entity_id("Living")
    coord = MagicMock()
    coord.zones = [{CONF_ZONE_NAME: "Living", CONF_ZONE_WINDOW_SENSOR: "binary_sensor.win"}]
    coord.is_zone_in_frost_emergency.return_value = False
    coord._climate_entities = {cid: SimpleNamespace(hvac_mode=HVACMode.OFF)}
    zone_select = MagicMock()
    zone_select.async_write_ha_state = MagicMock()
    coord._select_entities = {f"zone_mode_{cid}": zone_select}
    coord._async_set_hvac_mode = AsyncMock()
    coord.async_save_storage = AsyncMock()
    coord.async_set_persistent_data = AsyncMock()
    coord.resolve_zone_id = lambda x: x

    zm = ZoneManager(hass, coord)
    zone_select.async_select_option = AsyncMock(
        side_effect=lambda opt: zm.set_zone_mode(cid, opt, save_to_preset=False)
    )
    zm.async_on_window_state_changed(Event("state_changed", {"entity_id": "binary_sensor.win", "new_state": State("binary_sensor.win", "on")}))
    if tasks:
        await asyncio.gather(*tasks)
        tasks.clear()
    assert zm._zone_modes[cid] == ZONE_MODE_BYPASS
    assert zone_select.async_select_option.await_count == 1

    zm.async_on_window_state_changed(Event("state_changed", {"entity_id": "binary_sensor.win", "new_state": State("binary_sensor.win", "off")}))
    if tasks:
        await asyncio.gather(*tasks)
        tasks.clear()
    assert zm._zone_modes[cid] == ZONE_MODE_PRIMARY
    assert zone_select.async_select_option.await_count == 1  # NOT called again on close when was_off
    zone_select.async_write_ha_state.assert_called()
    coord._async_set_hvac_mode.assert_awaited_with(cid, HVACMode.OFF)


@pytest.mark.asyncio
async def test_14_proportional_valve_no_zero_spam_and_lifecycle_dedup():
    """#14: Confirmed 0 valve skips set_value(0.0); VT migration deduplicated; teardown cancels HP & startup tasks."""
    # Proportional valve confirmed at 0.0 -> zero service calls
    hass = _make_hass(
        states={
            "number.dac_output": State("number.dac_output", "0.0"),
            "valve.rad_v": State("valve.rad_v", "closed", {"current_position": 0}),
        }
    )
    coord = MagicMock()
    coord.get_zone_demand.return_value = 0.0
    coord.get_zone_mode.return_value = ZONE_MODE_PRIMARY
    coord.get_master_state.return_value = True
    sm = ZoneSyncManager(
        hass, coord, "Living", "climate.living", [], [], {}, valves=["number.dac_output", "valve.rad_v"], valve_scale=VALVE_SCALE_VOLT
    )
    await sm.async_sync_proportional_valves(HVACMode.HEAT)
    await sm.async_sync_proportional_valves(HVACMode.OFF)
    hass.services.async_call.assert_not_called()

    # Migration deduplication
    new_data, _, migrated = _migrate_config_data(
        {
            CONF_ZONES: [{CONF_ZONE_NAME: "Studio"}],
            "virtual_thermostats": [{"name": "Studio"}, {"name": "Bagno"}],
        },
        {},
    )
    assert migrated is True
    assert [z[CONF_ZONE_NAME] for z in new_data[CONF_ZONES]] == ["Studio", "Bagno"]

    # ListenerManager teardown cancels startup tasks and HP backend tasks
    lm = ListenerManager(coord)
    fake_task = MagicMock()
    fake_task.done.return_value = False
    lm._startup_tasks.append(fake_task)
    coord.heat_pump_backend = MagicMock()
    lm.async_teardown_listeners()
    fake_task.cancel.assert_called_once()
    coord.heat_pump_backend.cancel_pending_tasks.assert_called_once()


@pytest.mark.asyncio
async def test_15_protocols_frost_flow_combined_delta_watchdog_central_diag():
    """#15: Protocols, DEFAULT_FROST_FLOW_TEMP, COMBINED max_delta exclusions, watchdog naive dt, central diag."""
    # Watchdog naive datetime + 1e9 threshold
    wd = SensorWatchdog()
    naive_old = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)
    assert wd.is_sensor_stale(naive_old, 600) is True
    naive_fresh = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=10)
    assert wd.is_sensor_stale(naive_fresh, 600) is False
    # Monotonic timestamps (> 1e8, < 1e9) must use time.monotonic(), not time.time()
    with patch("custom_components.multizone_thermostat.safety.watchdog.time.monotonic", return_value=200_000_050.0):
        assert wd.is_sensor_stale(200_000_000.0, 600) is False

    # DEFAULT_FROST_FLOW_TEMP alignment
    hass = _make_hass(states={"climate.ot": State("climate.ot", "heat"), "climate.hp": State("climate.hp", "heat")})
    coord_ff = MagicMock()
    coord_ff.frost_flow_temp = None  # force fallback
    coord_ff.get_persistent_data.return_value = None
    coord_ff.zones = []
    coord_ff.weather_sensor_id = None
    ot = OpenThermBoilerBackend(hass, coord_ff, "climate.ot", 25.0, 75.0)
    hp = CentralHeatPumpBackend(hass, coord_ff, HP_TYPE_CLIMATE, "climate.hp", min_temp=25.0, max_temp=55.0)
    await ot.async_update(50.0, None, frost_emergency=True)
    await hp.async_update(50.0, None, frost_emergency=True)
    ot_temp = next(
        c[0][2]["temperature"]
        for c in hass.services.async_call.call_args_list
        if c[0][1] == "set_temperature" and c[0][2].get("entity_id") == "climate.ot"
    )
    hp_temp = next(
        c[0][2]["temperature"]
        for c in hass.services.async_call.call_args_list
        if c[0][1] == "set_temperature" and c[0][2].get("entity_id") == "climate.hp"
    )
    assert ot_temp == pytest.approx(DEFAULT_FROST_FLOW_TEMP)
    assert hp_temp == pytest.approx(DEFAULT_FROST_FLOW_TEMP)

    # COMBINED max_delta skips secondary, critical fault, split-suppressed
    cid_p = make_zone_entity_id("Primary")
    cid_s = make_zone_entity_id("Secondary")
    cid_f = make_zone_entity_id("Faulty")
    cid_sp = make_zone_entity_id("Split")
    coord_comb = MagicMock()
    coord_comb.zones = [
        {CONF_ZONE_NAME: "Primary"},
        {CONF_ZONE_NAME: "Secondary"},
        {CONF_ZONE_NAME: "Faulty"},
        {CONF_ZONE_NAME: "Split"},
    ]
    coord_comb._climate_entities = {
        cid_p: SimpleNamespace(hvac_mode=HVACMode.HEAT, current_temperature=19.0, target_temperature=20.0),   # delta 1.0
        cid_s: SimpleNamespace(hvac_mode=HVACMode.HEAT, current_temperature=12.0, target_temperature=22.0),   # excluded (secondary)
        cid_f: SimpleNamespace(hvac_mode=HVACMode.HEAT, current_temperature=10.0, target_temperature=22.0),   # excluded (faulty)
        cid_sp: SimpleNamespace(hvac_mode=HVACMode.HEAT, current_temperature=14.0, target_temperature=22.0),  # excluded (split suppressed)
    }
    coord_comb.get_master_state.return_value = True
    coord_comb.master_hvac_mode = HVAC_MODE_HEAT
    coord_comb.enable_gas_heater = True
    coord_comb.enable_heat_pump = True
    coord_comb.get_zone_mode.side_effect = lambda cid: ZONE_MODE_SECONDARY if cid == cid_s else ZONE_MODE_PRIMARY
    coord_comb.plant_diagnostics = MagicMock()
    coord_comb.plant_diagnostics.has_critical_sensor_fault.side_effect = lambda cid: cid == cid_f
    coord_comb.split_manager = MagicMock()
    coord_comb.split_manager.should_suppress_hydronic_demand.side_effect = lambda cid: cid == cid_sp
    coord_comb.energy_manager = MagicMock()
    coord_comb.energy_manager.get_heat_source_priority.return_value = SOURCE_PRIORITY_COMBINED
    coord_comb.energy_manager.is_solar_surplus.return_value = False
    coord_comb.is_zone_in_frost_emergency.return_value = False
    coord_comb.is_dhw_active = False

    dem_agg = MagicMock()
    dem_agg.calculate.return_value = SimpleNamespace(demand=40.0, peak_zone="Primary")
    orch = PlantOrchestrator(hass, dem_agg, MagicMock(), coord_comb)
    with patch("custom_components.multizone_thermostat.boiler.plant_orchestrator.decide_heating", wraps=lambda inp: SimpleNamespace(gas_demand=0.0, hp_demand=0.0, reason=f"delta={inp.max_zone_delta}")) as spy_dec:
        await orch._async_update_boiler(force_refresh_zones=False)
        assert spy_dec.call_args[0][0].max_zone_delta == pytest.approx(1.0)

    # PlantDiagnosticsEngine MODE_CENTRAL active when demand > 0
    coord_cent = MagicMock()
    coord_cent.hass = hass
    coord_cent.zones = []
    coord_cent.boiler_mode = MODE_CENTRAL
    coord_cent.enable_heat_pump = False
    coord_cent.plant_orchestrator = SimpleNamespace(last_aggregate=SimpleNamespace(demand=25.0))
    eng = PlantDiagnosticsEngine(coord_cent)
    assert eng.is_any_generator_running() is True

    # Protocol conformance check
    assert isinstance(coord_cent, object)
    assert BoilerBackendProtocol is not None
    assert ZoneControllerProtocol is not None
    assert CoordinatorProtocol is not None
