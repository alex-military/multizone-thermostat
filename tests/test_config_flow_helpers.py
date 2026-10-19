import pytest
import importlib.abc
import importlib.machinery
import sys
from unittest.mock import MagicMock

class HomeAssistantMockLoader(importlib.abc.Loader):
    def __init__(self, mock_module):
        self.mock_module = mock_module
    def create_module(self, spec):
        return self.mock_module
    def exec_module(self, module):
        pass

class HomeAssistantMockFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname == 'homeassistant' or fullname.startswith('homeassistant.'):
            mock_module = MagicMock()
            mock_module.__path__ = []
            if fullname == 'homeassistant.components.climate':
                mock_module.DOMAIN = 'climate'
            if fullname == 'homeassistant.components.switch':
                mock_module.DOMAIN = 'switch'
            if fullname == 'homeassistant.components.sensor':
                mock_module.DOMAIN = 'sensor'
            if fullname == 'homeassistant.components.binary_sensor':
                mock_module.DOMAIN = 'binary_sensor'
            if fullname == 'homeassistant.core':
                mock_module.HomeAssistant = MagicMock
                mock_module.callback = lambda f: f
            if fullname == 'homeassistant.helpers.entity_registry':
                del mock_module.async_entries_for_domain
            return importlib.machinery.ModuleSpec(fullname, HomeAssistantMockLoader(mock_module))
        return None

if not any(isinstance(finder, HomeAssistantMockFinder) for finder in sys.meta_path):
    sys.meta_path.insert(0, HomeAssistantMockFinder())

import unittest
import sys
import os
from unittest.mock import MagicMock

# Aggiungo la root del component per permettere gli import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'dummy_ha')))

from homeassistant.core import HomeAssistant
from custom_components.multizone_thermostat.config_flow.helpers import (
    _get_switch_entities,
    _get_climate_entities,
    _get_binary_sensor_entities,
    _get_temperature_sensor_entities,
    _remove_entity_from_registry,
)

class TestConfigFlowHelpers(unittest.TestCase):
    def setUp(self):
        self.hass = MagicMock(spec=HomeAssistant)
        
        # Mocks per registry entities
        self.registry_entities = {}
        
        # Mock per er.async_get(hass)
        self.mock_er = MagicMock()
        self.mock_er.entities = self.registry_entities
        self.mock_er.async_get.side_effect = lambda entity_id: self.registry_entities.get(entity_id)
        
        # Patch dell'entity_registry
        self.er_patcher = unittest.mock.patch("custom_components.multizone_thermostat.config_flow.helpers.er.async_get")
        self.mock_async_get = self.er_patcher.start()
        self.mock_async_get.return_value = self.mock_er
        
        # Mocks per states
        self.states_dict = {}
        self.hass.states = MagicMock()
        
        def mock_get_state(entity_id):
            return self.states_dict.get(entity_id)
            
        def mock_async_all(domain=None):
            if domain:
                return [s for s in self.states_dict.values() if s.domain == domain]
            return list(self.states_dict.values())
            
        self.hass.states.get = mock_get_state
        self.hass.states.async_all = mock_async_all

    def tearDown(self):
        self.er_patcher.stop()

    def _add_registry_entity(self, entity_id, domain, disabled=False):
        entry = MagicMock()
        entry.entity_id = entity_id
        entry.domain = domain
        entry.disabled = disabled
        self.registry_entities[entity_id] = entry
        
    def _add_state(self, entity_id, domain, friendly_name=None, attributes=None):
        state = MagicMock()
        state.entity_id = entity_id
        state.domain = domain
        
        attrs = attributes or {}
        if friendly_name:
            attrs["friendly_name"] = friendly_name
            
        state.attributes = attrs
        self.states_dict[entity_id] = state

    def test_get_switch_entities(self):
        # 1. Uno switch nel registry con state
        self._add_registry_entity("switch.uno", "switch")
        self._add_state("switch.uno", "switch", "Switch 1")
        
        # 2. Uno switch disabled nel registry E con state (deve essere ignorato)
        self._add_registry_entity("switch.disabled", "switch", disabled=True)
        self._add_state("switch.disabled", "switch", "Disabled Switch")
        
        # 3. Uno switch solo in states (non nel registry)
        self._add_state("switch.due", "switch", "Switch 2")

        # 4. Uno switch nel registry senza state (fallback su entity_id)
        self._add_registry_entity("switch.tre", "switch")
        
        res = _get_switch_entities(self.hass)
        
        self.assertEqual(len(res), 3)
        self.assertEqual(res["switch.uno"], "Switch 1")
        self.assertEqual(res["switch.due"], "Switch 2")
        self.assertEqual(res["switch.tre"], "switch.tre")
        self.assertNotIn("switch.disabled", res)
        
        # Deve essere ordinato alfabeticamente per nome
        self.assertEqual(list(res.keys()), ["switch.uno", "switch.due", "switch.tre"])

    def test_get_climate_entities(self):
        self._add_registry_entity("climate.a", "climate")
        self._add_state("climate.a", "climate", "Z Climate")
        
        self._add_state("climate.b", "climate", "A Climate")
        
        res = _get_climate_entities(self.hass)
        self.assertEqual(len(res), 2)
        
        # Sorting (A Climate prima di Z Climate)
        self.assertEqual(list(res.keys()), ["climate.b", "climate.a"])

    def test_get_binary_sensor_entities(self):
        self._add_state("binary_sensor.win", "binary_sensor", "Window")
        
        res = _get_binary_sensor_entities(self.hass)
        
        # Deve includere "none" di default
        self.assertEqual(len(res), 2)
        self.assertIn("none", res)
        self.assertEqual(res["binary_sensor.win"], "Window")

    def test_get_temperature_sensor_entities(self):
        # 1. Un sensore non temperatura
        self._add_state("sensor.power", "sensor", attributes={"device_class": "power"})
        
        # 2. Un sensore temperatura
        self._add_state("sensor.temp", "sensor", "Room Temp", attributes={"device_class": "temperature"})
        
        # 3. Un meteo (weather)
        self._add_state("weather.home", "weather", "Home Weather")
        
        res = _get_temperature_sensor_entities(self.hass)
        
        self.assertEqual(len(res), 2)
        self.assertNotIn("sensor.power", res)
        self.assertEqual(res["sensor.temp"], "Room Temp")
        self.assertEqual(res["weather.home"], "Home Weather")

    def test_remove_entity_from_registry(self):
        self.mock_er.async_get.side_effect = None
        self.mock_er.async_get.return_value = True # simula che l'entita esiste
        _remove_entity_from_registry(self.hass, "climate.old")
        self.mock_er.async_remove.assert_called_once_with("climate.old")

if __name__ == '__main__':
    unittest.main()

