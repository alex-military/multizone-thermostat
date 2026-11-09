"""Unit tests for Multizone Thermostat Phase 11 Step 1 (Core Data Model & Config Flow)."""
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, AsyncMock

# Base paths
dummy_ha_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "dummy_ha"))
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if dummy_ha_path not in sys.path:
    sys.path.insert(0, dummy_ha_path)
if repo_root not in sys.path:
    sys.path.insert(1, repo_root)


def _setup_clean_ha_environment():
    saved_meta_path = list(sys.meta_path)
    saved_modules = dict(sys.modules)
    sys.meta_path = [f for f in sys.meta_path if f.__class__.__name__ != "HomeAssistantMockFinder"]
    for mod_name in list(sys.modules.keys()):
        if (
            mod_name in ("homeassistant", "homeassistant.data_entry_flow", "homeassistant.config_entries", "homeassistant.helpers", "homeassistant.helpers.selector")
            or "config_flow" in mod_name
        ):
            del sys.modules[mod_name]

    data_entry_flow_mod = types.ModuleType("homeassistant.data_entry_flow")
    data_entry_flow_mod.section = lambda s, o=None: s
    sys.modules["homeassistant.data_entry_flow"] = data_entry_flow_mod
    return saved_meta_path, saved_modules


def _restore_ha_environment(saved_meta_path, saved_modules):
    sys.meta_path[:] = saved_meta_path
    sys.modules.clear()
    sys.modules.update(saved_modules)


class TestConfigFlowPhase11DataModel(unittest.TestCase):
    """Test validators, schemas and helpers for Phase 11."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._saved_meta, cls._saved_mods = _setup_clean_ha_environment()

        from custom_components.multizone_thermostat.const import (
            CONF_ZONE_NAME,
            CONF_ZONE_CLIMATES,
            CONF_ZONE_SWITCHES,
            CONF_ZONE_VALVES,
            CONF_ZONE_SPLIT_CLIMATE,
            CONF_ZONE_SPLIT_ROLE,
            SPLIT_ROLE_HEAT_COOL,
            SPLIT_ROLE_HEATING_ONLY,
            SPLIT_ROLE_COOLING_ONLY,
            DEFAULT_SPLIT_ROLE,
            CONF_ZONE_SPLIT_SOLAR_PRIORITY,
            DEFAULT_SPLIT_SOLAR_PRIORITY,
            CONF_ZONE_SPLIT_QUICK_BOOST,
            DEFAULT_SPLIT_QUICK_BOOST,
            CONF_ZONE_SPLIT_BOOST_DELTA,
            DEFAULT_SPLIT_BOOST_DELTA,
            CONF_ZONE_SPLIT_SENSOR_INJECTION,
            DEFAULT_SPLIT_SENSOR_INJECTION,
            CONF_ENABLE_GAS_HEATER,
            CONF_ENABLE_HEAT_PUMP,
            CONF_HEAT_PUMP_TYPE,
            HP_TYPE_CLIMATE,
            HP_TYPE_SWITCH,
            HP_TYPE_OPENTHERM,
            CONF_HEAT_PUMP_ENTITY,
            CONF_HEAT_PUMP_MIN_TEMP,
            CONF_HEAT_PUMP_MAX_TEMP,
            CONF_HEAT_PUMP_CH_SWITCH,
            CONF_ENERGY_MANAGEMENT_ENABLED,
            CONF_SOLAR_POWER_SENSOR,
            CONF_GRID_EXPORT_SENSOR,
            CONF_BATTERY_SOC_SENSOR,
            CONF_EXTERNAL_SOLAR_OVERRIDE_ENTITY,
            CONF_SOLAR_EXPORT_THRESHOLD,
            DEFAULT_SOLAR_EXPORT_THRESHOLD,
            CONF_BATTERY_MIN_RESERVE_SOC,
            DEFAULT_BATTERY_MIN_RESERVE_SOC,
        )
        from custom_components.multizone_thermostat.config_flow.validators import (
            validate_plants_selection,
            validate_heat_pump_temps,
            validate_zone_input,
        )
        from custom_components.multizone_thermostat.config_flow.helpers import flatten_zone_user_input
        from custom_components.multizone_thermostat.config_flow.schemas import (
            get_plants_selection_schema,
            get_heat_pump_schema,
            get_energy_management_schema,
            get_add_zone_schema,
            get_options_edit_zone_schema,
        )

        cls.CONF_ZONE_NAME = CONF_ZONE_NAME
        cls.CONF_ZONE_CLIMATES = CONF_ZONE_CLIMATES
        cls.CONF_ZONE_SPLIT_CLIMATE = CONF_ZONE_SPLIT_CLIMATE
        cls.CONF_ZONE_SPLIT_ROLE = CONF_ZONE_SPLIT_ROLE
        cls.CONF_ZONE_SPLIT_SOLAR_PRIORITY = CONF_ZONE_SPLIT_SOLAR_PRIORITY
        cls.CONF_ZONE_SPLIT_QUICK_BOOST = CONF_ZONE_SPLIT_QUICK_BOOST
        cls.CONF_ZONE_SPLIT_BOOST_DELTA = CONF_ZONE_SPLIT_BOOST_DELTA
        cls.CONF_ZONE_SPLIT_SENSOR_INJECTION = CONF_ZONE_SPLIT_SENSOR_INJECTION
        cls.CONF_ENABLE_GAS_HEATER = CONF_ENABLE_GAS_HEATER
        cls.CONF_ENABLE_HEAT_PUMP = CONF_ENABLE_HEAT_PUMP
        cls.CONF_HEAT_PUMP_TYPE = CONF_HEAT_PUMP_TYPE
        cls.CONF_HEAT_PUMP_ENTITY = CONF_HEAT_PUMP_ENTITY
        cls.CONF_ENERGY_MANAGEMENT_ENABLED = CONF_ENERGY_MANAGEMENT_ENABLED

        cls.validate_plants_selection = staticmethod(validate_plants_selection)
        cls.validate_heat_pump_temps = staticmethod(validate_heat_pump_temps)
        cls.validate_zone_input = staticmethod(validate_zone_input)
        cls.flatten_zone_user_input = staticmethod(flatten_zone_user_input)
        cls.get_plants_selection_schema = staticmethod(get_plants_selection_schema)
        cls.get_heat_pump_schema = staticmethod(get_heat_pump_schema)
        cls.get_energy_management_schema = staticmethod(get_energy_management_schema)
        cls.get_add_zone_schema = staticmethod(get_add_zone_schema)
        cls.get_options_edit_zone_schema = staticmethod(get_options_edit_zone_schema)

    @classmethod
    def tearDownClass(cls):
        _restore_ha_environment(cls._saved_meta, cls._saved_mods)
        super().tearDownClass()

    def test_validate_plants_selection(self):
        """Verify plant selection validation requires at least one generator."""
        self.assertEqual(self.validate_plants_selection(True, False), {})
        self.assertEqual(self.validate_plants_selection(False, True), {})
        self.assertEqual(self.validate_plants_selection(True, True), {})
        self.assertEqual(self.validate_plants_selection(False, False), {"base": "no_plants_selected"})

    def test_validate_heat_pump_temps(self):
        """Verify heat pump flow temperature range check."""
        self.assertEqual(self.validate_heat_pump_temps(25.0, 55.0), {})
        self.assertEqual(self.validate_heat_pump_temps(55.0, 25.0), {"base": "invalid_temp_range"})
        self.assertEqual(self.validate_heat_pump_temps(40.0, 40.0), {"base": "invalid_temp_range"})

    def test_validate_zone_input_with_split(self):
        """Verify zones with ONLY a split climate actuator are completely valid."""
        # Split-only zone (e.g. attic with AC split and no hydronic radiator)
        res = self.validate_zone_input("Mansarda", [], [], [], valves=[], split_climate="climate.mansarda_split")
        self.assertEqual(res, {})

        # Zone with both radiator and split
        res2 = self.validate_zone_input("Salotto", ["climate.trv_salotto"], [], [], valves=[], split_climate="climate.split_salotto")
        self.assertEqual(res2, {})

        # Zone with no actuators at all
        res3 = self.validate_zone_input("Vuota", [], [], [], valves=[], split_climate=None)
        self.assertEqual(res3, {"base": "no_actuators_selected"})

    def test_flatten_zone_user_input_with_split_settings(self):
        """Verify flatten_zone_user_input extracts split_settings fields properly."""
        nested = {
            self.CONF_ZONE_NAME: "Studio",
            "split_settings": {
                self.CONF_ZONE_SPLIT_CLIMATE: "climate.split_studio",
                self.CONF_ZONE_SPLIT_ROLE: "heating_only",
                self.CONF_ZONE_SPLIT_SOLAR_PRIORITY: True,
                self.CONF_ZONE_SPLIT_QUICK_BOOST: True,
                self.CONF_ZONE_SPLIT_BOOST_DELTA: 2.0,
                self.CONF_ZONE_SPLIT_SENSOR_INJECTION: True,
            }
        }
        flattened = self.flatten_zone_user_input(nested)
        self.assertEqual(flattened[self.CONF_ZONE_NAME], "Studio")
        self.assertEqual(flattened[self.CONF_ZONE_SPLIT_CLIMATE], "climate.split_studio")
        self.assertEqual(flattened[self.CONF_ZONE_SPLIT_ROLE], "heating_only")
        self.assertTrue(flattened[self.CONF_ZONE_SPLIT_SOLAR_PRIORITY])
        self.assertTrue(flattened[self.CONF_ZONE_SPLIT_QUICK_BOOST])
        self.assertEqual(flattened[self.CONF_ZONE_SPLIT_BOOST_DELTA], 2.0)
        self.assertTrue(flattened[self.CONF_ZONE_SPLIT_SENSOR_INJECTION])
        self.assertNotIn("split_settings", flattened)

    def test_schemas_contain_phase11_fields(self):
        """Verify schemas expose all Phase 11 fields."""
        plant_schema = self.get_plants_selection_schema()
        self.assertIsNotNone(plant_schema)

        hp_schema = self.get_heat_pump_schema()
        self.assertIsNotNone(hp_schema)

        energy_schema = self.get_energy_management_schema()
        self.assertIsNotNone(energy_schema)

        zone_schema = self.get_add_zone_schema()
        self.assertIn("split_settings", zone_schema.schema)

        edit_zone_schema = self.get_options_edit_zone_schema({
            self.CONF_ZONE_NAME: "Salotto",
            self.CONF_ZONE_SPLIT_CLIMATE: "climate.split_salotto",
        }, {}, {})
        self.assertIn("split_settings", edit_zone_schema.schema)


class TestConfigFlowPhase11Execution(unittest.IsolatedAsyncioTestCase):
    """Test ConfigFlow execution steps for Phase 11."""

    async def asyncSetUp(self):
        self._saved_meta, self._saved_mods = _setup_clean_ha_environment()
        from custom_components.multizone_thermostat.config_flow import MultizoneConfigFlow
        from custom_components.multizone_thermostat.const import (
            CONF_ENABLE_GAS_HEATER,
            CONF_ENABLE_HEAT_PUMP,
            CONF_BOILER_MODE,
            MODE_RELAY,
            CONF_BOILER_SWITCH,
            CONF_HEAT_PUMP_TYPE,
            HP_TYPE_CLIMATE,
            CONF_HEAT_PUMP_ENTITY,
            CONF_HEAT_PUMP_MIN_TEMP,
            CONF_HEAT_PUMP_MAX_TEMP,
            CONF_ZONE_NAME,
            CONF_ZONE_CLIMATES,
            CONF_ZONE_SPLIT_CLIMATE,
        )
        self.flow = MultizoneConfigFlow()
        self.flow.hass = MagicMock()
        self.flow.async_set_unique_id = AsyncMock(return_value=None)
        self.flow._abort_if_unique_id_configured = MagicMock(return_value=None)
        self.flow.async_show_form = MagicMock(side_effect=lambda **kwargs: {"type": "form", **kwargs})
        self.CONF_ENABLE_GAS_HEATER = CONF_ENABLE_GAS_HEATER
        self.CONF_ENABLE_HEAT_PUMP = CONF_ENABLE_HEAT_PUMP
        self.CONF_BOILER_MODE = CONF_BOILER_MODE
        self.MODE_RELAY = MODE_RELAY
        self.CONF_BOILER_SWITCH = CONF_BOILER_SWITCH
        self.CONF_HEAT_PUMP_TYPE = CONF_HEAT_PUMP_TYPE
        self.HP_TYPE_CLIMATE = HP_TYPE_CLIMATE
        self.CONF_HEAT_PUMP_ENTITY = CONF_HEAT_PUMP_ENTITY
        self.CONF_HEAT_PUMP_MIN_TEMP = CONF_HEAT_PUMP_MIN_TEMP
        self.CONF_HEAT_PUMP_MAX_TEMP = CONF_HEAT_PUMP_MAX_TEMP
        self.CONF_ZONE_NAME = CONF_ZONE_NAME
        self.CONF_ZONE_CLIMATES = CONF_ZONE_CLIMATES
        self.CONF_ZONE_SPLIT_CLIMATE = CONF_ZONE_SPLIT_CLIMATE

    async def asyncTearDown(self):
        _restore_ha_environment(self._saved_meta, self._saved_mods)

    async def test_step_user_gas_only(self):
        """User selects Gas boiler only."""
        res = await self.flow.async_step_user({
            self.CONF_ENABLE_GAS_HEATER: True,
            self.CONF_ENABLE_HEAT_PUMP: False,
        })
        self.assertEqual(res["step_id"], "boiler_mode")

    async def test_step_user_hp_only(self):
        """User selects Heat Pump only."""
        res = await self.flow.async_step_user({
            self.CONF_ENABLE_GAS_HEATER: False,
            self.CONF_ENABLE_HEAT_PUMP: True,
        })
        self.assertEqual(res["step_id"], "heat_pump")

    async def test_step_user_both_bivalent(self):
        """User selects both Gas and Heat Pump (Bivalent hybrid)."""
        res = await self.flow.async_step_user({
            self.CONF_ENABLE_GAS_HEATER: True,
            self.CONF_ENABLE_HEAT_PUMP: True,
        })
        self.assertEqual(res["step_id"], "boiler_mode")

    async def test_step_user_neither_fails(self):
        """Selecting neither plant raises error."""
        res = await self.flow.async_step_user({
            self.CONF_ENABLE_GAS_HEATER: False,
            self.CONF_ENABLE_HEAT_PUMP: False,
        })
        self.assertEqual(res["errors"], {"base": "no_plants_selected"})

    async def test_legacy_boiler_mode_backward_compatibility(self):
        """Calling step user with legacy boiler_mode directly works seamlessly."""
        self.flow.async_step_boiler_relay = AsyncMock(return_value={"type": "form", "step_id": "boiler_relay"})
        res = await self.flow.async_step_user({self.CONF_BOILER_MODE: self.MODE_RELAY})
        self.flow.async_step_boiler_relay.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
