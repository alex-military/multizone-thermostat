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
            return importlib.machinery.ModuleSpec(fullname, HomeAssistantMockLoader(mock_module))
        return None

if not any(isinstance(finder, HomeAssistantMockFinder) for finder in sys.meta_path):
    sys.meta_path.insert(0, HomeAssistantMockFinder())

import unittest
import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from custom_components.multizone_thermostat.config_flow.validators import (
    validate_opentherm_temps,
    validate_zone_input,
    validate_geofencing,
)

class TestConfigFlowValidators(unittest.TestCase):
    def test_validate_opentherm_temps(self):
        self.assertEqual(validate_opentherm_temps(35, 75), {})
        self.assertEqual(validate_opentherm_temps(75, 35), {"base": "invalid_temp_range"})
        self.assertEqual(validate_opentherm_temps(50, 50), {"base": "invalid_temp_range"})

    def test_validate_zone_input(self):
        self.assertEqual(validate_zone_input("Zone 1", ["climate.a"], [], []), {})
        self.assertEqual(validate_zone_input("Zone 1", [], ["switch.a"], []), {})
        self.assertEqual(validate_zone_input("Zone 1", [], [], [], valves=["number.valve1"]), {})
        self.assertEqual(validate_zone_input("", ["climate.a"], [], []), {"name": "zone_name_required"})
        self.assertEqual(validate_zone_input("Zone 1", ["climate.a"], [], ["Zone 1"]), {"name": "zone_name_exists"})
        self.assertEqual(validate_zone_input("Zone 1", [], [], []), {"base": "no_actuators_selected"})

    def test_validate_geofencing(self):
        self.assertEqual(validate_geofencing(False, None), {})
        self.assertEqual(validate_geofencing(True, "sensor.presence"), {})
        self.assertEqual(validate_geofencing(True, None), {"presence_sensor": "presence_sensor_required"})

    def test_options_flow_imports_and_time_parsing(self):
        import importlib
        from custom_components.multizone_thermostat.config_flow import options_flow
        self.assertTrue(hasattr(options_flow, "_get_temperature_sensor_entities"))

        time_mod = MagicMock()
        time_mod.TimeEntity = object
        sys.modules["homeassistant.components.time"] = time_mod
        import custom_components.multizone_thermostat.time as mzt_time
        importlib.reload(mzt_time)

        coord = MagicMock()
        coord.get_persistent_data.return_value = "22:30:00"
        night_entity = mzt_time.MultizoneNightTimeEntity(coord, "entry1")
        self.assertEqual(night_entity.native_value.hour, 22)
        self.assertEqual(night_entity.native_value.minute, 30)

        coord.get_persistent_data.return_value = "07:15:00"
        morning_entity = mzt_time.MultizoneMorningTimeEntity(coord, "entry1")
        self.assertEqual(morning_entity.native_value.hour, 7)
        self.assertEqual(morning_entity.native_value.minute, 15)


if __name__ == '__main__':
    unittest.main()

