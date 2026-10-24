"""Unit tests for Multizone Thermostat Config Flow & Translations (Phase 9 & 10)."""
import asyncio
import json
import os
import re
import sys
import types
import unittest
from unittest.mock import MagicMock

# Base paths
dummy_ha_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "dummy_ha"))
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if dummy_ha_path not in sys.path:
    sys.path.insert(0, dummy_ha_path)
if repo_root not in sys.path:
    sys.path.insert(1, repo_root)


def _setup_clean_ha_environment():
    """Ensure clean Home Assistant config_flow environment while preserving other loaded modules."""
    saved_meta_path = list(sys.meta_path)
    saved_modules = dict(sys.modules)
    sys.meta_path = [f for f in sys.meta_path if f.__class__.__name__ != "HomeAssistantMockFinder"]
    for mod_name in list(sys.modules.keys()):
        if (
            mod_name in ("homeassistant", "homeassistant.data_entry_flow", "homeassistant.config_entries", "homeassistant.helpers", "homeassistant.helpers.selector")
            or "config_flow" in mod_name
        ):
            del sys.modules[mod_name]

    # Provide data_entry_flow module for voluptuous sections
    data_entry_flow_mod = types.ModuleType("homeassistant.data_entry_flow")
    data_entry_flow_mod.section = lambda s, o=None: s
    sys.modules["homeassistant.data_entry_flow"] = data_entry_flow_mod
    return saved_meta_path, saved_modules


def _restore_ha_environment(saved_meta_path, saved_modules):
    """Restore original sys.meta_path and sys.modules."""
    sys.meta_path[:] = saved_meta_path
    sys.modules.clear()
    sys.modules.update(saved_modules)


class TestConfigFlowPhase910SchemasAndHelpers(unittest.TestCase):
    """Test schemas and helper functions for authoritative sync and zone weight."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._saved_meta, cls._saved_mods = _setup_clean_ha_environment()
        
        from custom_components.multizone_thermostat.const import (
            CONF_ZONE_NAME,
            CONF_ZONE_CLIMATES,
            CONF_ZONE_WEIGHT,
            DEFAULT_ZONE_WEIGHT,
            CONF_ZONE_AUTHORITATIVE_SYNC,
            DEFAULT_AUTHORITATIVE_SYNC,
            CONF_ZONE_TRV_SYNC,
            CONF_ZONE_SWITCHES,
            CONF_ZONE_VALVES,
        )
        from custom_components.multizone_thermostat.config_flow.helpers import flatten_zone_user_input
        from custom_components.multizone_thermostat.config_flow.schemas import (
            get_add_zone_schema,
            get_options_edit_zone_schema,
        )

        cls.CONF_ZONE_NAME = CONF_ZONE_NAME
        cls.CONF_ZONE_CLIMATES = CONF_ZONE_CLIMATES
        cls.CONF_ZONE_WEIGHT = CONF_ZONE_WEIGHT
        cls.DEFAULT_ZONE_WEIGHT = DEFAULT_ZONE_WEIGHT
        cls.CONF_ZONE_AUTHORITATIVE_SYNC = CONF_ZONE_AUTHORITATIVE_SYNC
        cls.DEFAULT_AUTHORITATIVE_SYNC = DEFAULT_AUTHORITATIVE_SYNC
        cls.CONF_ZONE_TRV_SYNC = CONF_ZONE_TRV_SYNC
        cls.CONF_ZONE_SWITCHES = CONF_ZONE_SWITCHES
        cls.CONF_ZONE_VALVES = CONF_ZONE_VALVES
        cls.flatten_zone_user_input = staticmethod(flatten_zone_user_input)
        cls.get_add_zone_schema = staticmethod(get_add_zone_schema)
        cls.get_options_edit_zone_schema = staticmethod(get_options_edit_zone_schema)

    @classmethod
    def tearDownClass(cls):
        _restore_ha_environment(cls._saved_meta, cls._saved_mods)
        super().tearDownClass()

    def test_flatten_zone_user_input_with_authoritative_sync_and_weight(self):
        """Verify flatten_zone_user_input extracts fields from collapsible sections."""
        nested_input = {
            self.CONF_ZONE_NAME: "Living Room",
            "trv_settings": {
                self.CONF_ZONE_CLIMATES: ["climate.trv_living"],
                self.CONF_ZONE_TRV_SYNC: True,
                self.CONF_ZONE_AUTHORITATIVE_SYNC: True,
            },
            "safety_settings": {
                self.CONF_ZONE_WEIGHT: 2.5,
                "sensor_timeout_min": 60,
            },
        }

        flattened = self.flatten_zone_user_input(nested_input)

        self.assertEqual(flattened[self.CONF_ZONE_NAME], "Living Room")
        self.assertTrue(flattened[self.CONF_ZONE_AUTHORITATIVE_SYNC])
        self.assertEqual(flattened[self.CONF_ZONE_WEIGHT], 2.5)
        self.assertEqual(flattened[self.CONF_ZONE_CLIMATES], ["climate.trv_living"])
        self.assertNotIn("trv_settings", flattened)
        self.assertNotIn("safety_settings", flattened)

    def test_get_add_zone_schema_contains_new_fields(self):
        """Verify get_add_zone_schema defines authoritative_climate_sync and weight with proper defaults."""
        schema = self.get_add_zone_schema()
        schema_dict = schema.schema

        # trv_settings section
        trv_sec = schema_dict.get("trv_settings")
        self.assertIsNotNone(trv_sec)
        trv_subschema = trv_sec.schema if hasattr(trv_sec, "schema") else trv_sec
        trv_keys = {str(k): k for k in trv_subschema.keys()}

        self.assertIn(self.CONF_ZONE_AUTHORITATIVE_SYNC, trv_keys)
        auth_key = trv_keys[self.CONF_ZONE_AUTHORITATIVE_SYNC]
        self.assertEqual(auth_key.default(), self.DEFAULT_AUTHORITATIVE_SYNC)

        # safety_settings section
        safety_sec = schema_dict.get("safety_settings")
        self.assertIsNotNone(safety_sec)
        safety_subschema = safety_sec.schema if hasattr(safety_sec, "schema") else safety_sec
        safety_keys = {str(k): k for k in safety_subschema.keys()}

        self.assertIn(self.CONF_ZONE_WEIGHT, safety_keys)
        weight_key = safety_keys[self.CONF_ZONE_WEIGHT]
        self.assertEqual(weight_key.default(), self.DEFAULT_ZONE_WEIGHT)

    def test_get_options_edit_zone_schema_defaults(self):
        """Verify get_options_edit_zone_schema uses existing zone data values as defaults."""
        existing_zone = {
            self.CONF_ZONE_NAME: "Office",
            self.CONF_ZONE_CLIMATES: ["climate.office"],
            self.CONF_ZONE_AUTHORITATIVE_SYNC: True,
            self.CONF_ZONE_WEIGHT: 3.2,
        }

        schema = self.get_options_edit_zone_schema(existing_zone, {}, {})
        schema_dict = schema.schema

        # trv_settings
        trv_sec = schema_dict.get("trv_settings")
        trv_subschema = trv_sec.schema if hasattr(trv_sec, "schema") else trv_sec
        trv_keys = {str(k): k for k in trv_subschema.keys()}
        auth_key = trv_keys[self.CONF_ZONE_AUTHORITATIVE_SYNC]
        self.assertEqual(auth_key.default(), True)

        # safety_settings
        safety_sec = schema_dict.get("safety_settings")
        safety_subschema = safety_sec.schema if hasattr(safety_sec, "schema") else safety_sec
        safety_keys = {str(k): k for k in safety_subschema.keys()}
        weight_key = safety_keys[self.CONF_ZONE_WEIGHT]
        self.assertEqual(weight_key.default(), 3.2)

    def test_get_options_edit_zone_schema_fallback(self):
        """Verify get_options_edit_zone_schema falls back to constants when keys are absent."""
        empty_zone = {self.CONF_ZONE_NAME: "Empty"}
        schema = self.get_options_edit_zone_schema(empty_zone, {}, {})
        schema_dict = schema.schema

        trv_sec = schema_dict.get("trv_settings")
        trv_subschema = trv_sec.schema if hasattr(trv_sec, "schema") else trv_sec
        trv_keys = {str(k): k for k in trv_subschema.keys()}
        auth_key = trv_keys[self.CONF_ZONE_AUTHORITATIVE_SYNC]
        self.assertEqual(auth_key.default(), self.DEFAULT_AUTHORITATIVE_SYNC)

        safety_sec = schema_dict.get("safety_settings")
        safety_subschema = safety_sec.schema if hasattr(safety_sec, "schema") else safety_sec
        safety_keys = {str(k): k for k in safety_subschema.keys()}
        weight_key = safety_keys[self.CONF_ZONE_WEIGHT]
        self.assertEqual(weight_key.default(), self.DEFAULT_ZONE_WEIGHT)


class TestConfigFlowPhase910Execution(unittest.TestCase):
    """Test config flow and options flow execution with new fields."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._saved_meta, cls._saved_mods = _setup_clean_ha_environment()
        
        from custom_components.multizone_thermostat.const import (
            CONF_ZONE_NAME,
            CONF_ZONE_CLIMATES,
            CONF_ZONE_WEIGHT,
            DEFAULT_ZONE_WEIGHT,
            CONF_ZONE_AUTHORITATIVE_SYNC,
            DEFAULT_AUTHORITATIVE_SYNC,
            CONF_ZONE_SWITCHES,
        )
        from custom_components.multizone_thermostat.config_flow import (
            MultizoneConfigFlow,
            MultizoneOptionsFlow,
        )

        cls.CONF_ZONE_NAME = CONF_ZONE_NAME
        cls.CONF_ZONE_CLIMATES = CONF_ZONE_CLIMATES
        cls.CONF_ZONE_WEIGHT = CONF_ZONE_WEIGHT
        cls.DEFAULT_ZONE_WEIGHT = DEFAULT_ZONE_WEIGHT
        cls.CONF_ZONE_AUTHORITATIVE_SYNC = CONF_ZONE_AUTHORITATIVE_SYNC
        cls.DEFAULT_AUTHORITATIVE_SYNC = DEFAULT_AUTHORITATIVE_SYNC
        cls.CONF_ZONE_SWITCHES = CONF_ZONE_SWITCHES
        cls.MultizoneConfigFlow = MultizoneConfigFlow
        cls.MultizoneOptionsFlow = MultizoneOptionsFlow

    @classmethod
    def tearDownClass(cls):
        _restore_ha_environment(cls._saved_meta, cls._saved_mods)
        super().tearDownClass()

    def setUp(self):
        self.hass = MagicMock()

    def test_config_flow_add_zone_with_authoritative_sync_and_weight(self):
        """Test MultizoneConfigFlow saves authoritative_climate_sync and weight."""
        flow = self.MultizoneConfigFlow()
        flow.hass = self.hass
        flow.async_show_form = MagicMock(return_value={"type": "form"})

        user_input = {
            self.CONF_ZONE_NAME: "Master Bedroom",
            "trv_settings": {
                self.CONF_ZONE_CLIMATES: ["climate.bedroom_trv"],
                self.CONF_ZONE_AUTHORITATIVE_SYNC: True,
            },
            "safety_settings": {
                self.CONF_ZONE_WEIGHT: 1.5,
            },
        }

        async def _run():
            return await flow.async_step_add_zone(user_input)

        asyncio.run(_run())

        self.assertEqual(len(flow._zones), 1)
        zone = flow._zones[0]
        self.assertEqual(zone[self.CONF_ZONE_NAME], "Master Bedroom")
        self.assertEqual(zone[self.CONF_ZONE_AUTHORITATIVE_SYNC], True)
        self.assertEqual(zone[self.CONF_ZONE_WEIGHT], 1.5)
        self.assertIsInstance(zone[self.CONF_ZONE_WEIGHT], float)

    def test_config_flow_add_zone_defaults(self):
        """Test MultizoneConfigFlow falls back to defaults when optional fields omitted."""
        flow = self.MultizoneConfigFlow()
        flow.hass = self.hass
        flow.async_show_form = MagicMock(return_value={"type": "form"})

        user_input = {
            self.CONF_ZONE_NAME: "Kitchen",
            self.CONF_ZONE_SWITCHES: ["switch.kitchen_relay"],
        }

        async def _run():
            return await flow.async_step_add_zone(user_input)

        asyncio.run(_run())

        self.assertEqual(len(flow._zones), 1)
        zone = flow._zones[0]
        self.assertEqual(zone[self.CONF_ZONE_AUTHORITATIVE_SYNC], self.DEFAULT_AUTHORITATIVE_SYNC)
        self.assertEqual(zone[self.CONF_ZONE_WEIGHT], self.DEFAULT_ZONE_WEIGHT)

    def test_options_flow_add_and_edit_zone(self):
        """Test MultizoneOptionsFlow adds and edits authoritative_climate_sync and weight."""
        flow = self.MultizoneOptionsFlow()
        flow.hass = self.hass
        flow.config_entry = MagicMock()
        flow.config_entry.data = {}
        flow.config_entry.options = {}
        flow._save_options = MagicMock(return_value={"type": "create_entry"})

        # 1. Add zone
        add_input = {
            self.CONF_ZONE_NAME: "Basement",
            "trv_settings": {
                self.CONF_ZONE_CLIMATES: ["climate.basement_trv"],
                self.CONF_ZONE_AUTHORITATIVE_SYNC: False,
            },
            "safety_settings": {
                self.CONF_ZONE_WEIGHT: 0.8,
            },
        }

        async def _run_add():
            return await flow.async_step_add_zone(add_input)

        asyncio.run(_run_add())

        self.assertEqual(len(flow._zones), 1)
        zone = flow._zones[0]
        self.assertEqual(zone[self.CONF_ZONE_AUTHORITATIVE_SYNC], False)
        self.assertEqual(zone[self.CONF_ZONE_WEIGHT], 0.8)

        # 2. Edit zone
        flow._current_zone_name = "Basement"
        edit_input = {
            "trv_settings": {
                self.CONF_ZONE_CLIMATES: ["climate.basement_trv"],
                self.CONF_ZONE_AUTHORITATIVE_SYNC: True,
            },
            "safety_settings": {
                self.CONF_ZONE_WEIGHT: 2.2,
            },
        }

        async def _run_edit():
            return await flow.async_step_edit_zone(edit_input)

        asyncio.run(_run_edit())

        self.assertEqual(len(flow._zones), 1)
        updated_zone = flow._zones[0]
        self.assertEqual(updated_zone[self.CONF_ZONE_AUTHORITATIVE_SYNC], True)
        self.assertEqual(updated_zone[self.CONF_ZONE_WEIGHT], 2.2)
        self.assertIsInstance(updated_zone[self.CONF_ZONE_WEIGHT], float)


class TestConfigFlowPhase910Translations(unittest.TestCase):
    """Test 100% key parity, valid placeholders, and translations across all supported languages."""

    LANGUAGES = ["de", "en", "es", "fr", "it", "ru"]
    BASE_DIR = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../custom_components/multizone_thermostat")
    )
    STRINGS_PATH = os.path.join(BASE_DIR, "strings.json")
    TRANSLATIONS_DIR = os.path.join(BASE_DIR, "translations")
    PLACEHOLDER_REGEX = re.compile(r"\{([a-zA-Z0-9_]+)\}")

    def _extract_leaf_keys_and_placeholders(self, data, prefix=""):
        res = {}
        for k, v in data.items():
            full_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                res.update(self._extract_leaf_keys_and_placeholders(v, full_key))
            else:
                placeholders = set(self.PLACEHOLDER_REGEX.findall(str(v)))
                res[full_key] = placeholders
        return res

    def test_strings_and_all_translations_exist_and_parse(self):
        """Verify strings.json and all 6 language files exist and are valid JSON."""
        self.assertTrue(os.path.isfile(self.STRINGS_PATH), f"Missing {self.STRINGS_PATH}")
        with open(self.STRINGS_PATH, "r", encoding="utf-8") as f:
            strings_doc = json.load(f)
        self.assertIsInstance(strings_doc, dict)

        for lang in self.LANGUAGES:
            trans_path = os.path.join(self.TRANSLATIONS_DIR, f"{lang}.json")
            self.assertTrue(os.path.isfile(trans_path), f"Missing {trans_path}")
            with open(trans_path, "r", encoding="utf-8") as f:
                trans_doc = json.load(f)
            self.assertIsInstance(trans_doc, dict)

    def test_translations_100_percent_key_parity_and_placeholders(self):
        """Verify all 6 translation files match strings.json keys and placeholders 100%."""
        with open(self.STRINGS_PATH, "r", encoding="utf-8") as f:
            strings_doc = json.load(f)
        strings_map = self._extract_leaf_keys_and_placeholders(strings_doc)

        for lang in self.LANGUAGES:
            trans_path = os.path.join(self.TRANSLATIONS_DIR, f"{lang}.json")
            with open(trans_path, "r", encoding="utf-8") as f:
                trans_doc = json.load(f)
            trans_map = self._extract_leaf_keys_and_placeholders(trans_doc)

            missing_keys = set(strings_map.keys()) - set(trans_map.keys())
            extra_keys = set(trans_map.keys()) - set(strings_map.keys())

            self.assertEqual(
                missing_keys,
                set(),
                f"Language '{lang}' is missing keys: {missing_keys}",
            )
            self.assertEqual(
                extra_keys,
                set(),
                f"Language '{lang}' has extra keys: {extra_keys}",
            )

            # Check placeholders
            for key, expected_placeholders in strings_map.items():
                actual_placeholders = trans_map[key]
                self.assertEqual(
                    expected_placeholders,
                    actual_placeholders,
                    f"Placeholder mismatch in '{lang}' for key '{key}': expected {expected_placeholders}, got {actual_placeholders}",
                )

    def test_demand_strategy_present_in_all_translations(self):
        """Verify demand_strategy is in entity.select in strings.json and all translations."""
        docs = [self.STRINGS_PATH] + [
            os.path.join(self.TRANSLATIONS_DIR, f"{lang}.json") for lang in self.LANGUAGES
        ]
        for path in docs:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            selects = data.get("entity", {}).get("select", {})
            self.assertIn("demand_strategy", selects, f"Missing demand_strategy in {path}")
            ds = selects["demand_strategy"]
            self.assertIn("name", ds)
            self.assertIn("state", ds)
            states = ds["state"]
            self.assertIn("max", states)
            self.assertIn("weighted_average", states)
            self.assertIn("sum_capped", states)

    def test_authoritative_sync_and_weight_present_in_all_translations(self):
        """Verify authoritative_climate_sync and weight are in all zone steps."""
        docs = [self.STRINGS_PATH] + [
            os.path.join(self.TRANSLATIONS_DIR, f"{lang}.json") for lang in self.LANGUAGES
        ]
        for path in docs:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # config.step.add_zone
            cfg_add = data["config"]["step"]["add_zone"]["sections"]
            self.assertIn("authoritative_climate_sync", cfg_add["trv_settings"]["data"])
            self.assertIn("weight", cfg_add["safety_settings"]["data"])

            # options.step.add_zone
            opt_add = data["options"]["step"]["add_zone"]["sections"]
            self.assertIn("authoritative_climate_sync", opt_add["trv_settings"]["data"])
            self.assertIn("weight", opt_add["safety_settings"]["data"])

            # options.step.edit_zone
            opt_edit = data["options"]["step"]["edit_zone"]["sections"]
            self.assertIn("authoritative_climate_sync", opt_edit["trv_settings"]["data"])
            self.assertIn("weight", opt_edit["safety_settings"]["data"])

    def test_boiler_opentherm_dual_path_description_in_all_translations(self):
        """Verify boiler_opentherm step description explains the dual path setup."""
        docs = [self.STRINGS_PATH] + [
            os.path.join(self.TRANSLATIONS_DIR, f"{lang}.json") for lang in self.LANGUAGES
        ]
        for path in docs:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            cfg_desc = data["config"]["step"]["boiler_opentherm"]["description"]
            opt_desc = data["options"]["step"]["boiler_opentherm"]["description"]

            self.assertTrue(len(cfg_desc) > 30)
            self.assertEqual(cfg_desc, opt_desc)


if __name__ == "__main__":
    unittest.main()
