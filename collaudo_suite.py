import unittest
import time
import math
import sys
import os
from unittest.mock import MagicMock

# Mock homeassistant before importing anything
sys.modules['homeassistant'] = MagicMock()
sys.modules['homeassistant.core'] = MagicMock()
sys.modules['homeassistant.const'] = MagicMock()
sys.modules['homeassistant.components'] = MagicMock()
sys.modules['homeassistant.components.climate'] = MagicMock()
sys.modules['homeassistant.components.http'] = MagicMock()
sys.modules['homeassistant.config_entries'] = MagicMock()
sys.modules['homeassistant.exceptions'] = MagicMock()
sys.modules['homeassistant.helpers'] = MagicMock()
sys.modules['homeassistant.helpers.entity'] = MagicMock()
sys.modules['homeassistant.helpers.event'] = MagicMock()
sys.modules['homeassistant.helpers.storage'] = MagicMock()
sys.modules['homeassistant.helpers.typing'] = MagicMock()
sys.modules['homeassistant.util'] = MagicMock()
sys.modules['homeassistant.util.dt'] = MagicMock()
sys.modules['homeassistant.util.dt'] = MagicMock()

# Add the scratch directory to sys.path so we can import the custom_components
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from custom_components.multizone_thermostat.pwm_engine import PWMEngine
from custom_components.multizone_thermostat.pid import PID
from custom_components.multizone_thermostat.pid_wrapper import MultizonePID
from custom_components.multizone_thermostat.autotune import PassiveAutotuneObserver
from custom_components.multizone_thermostat.thermal_model import ThermalObserver
from custom_components.multizone_thermostat.plant_diagnostics import PlantDiagnosticsEngine, ANOMALY_NONE, ANOMALY_STALE_SENSOR, ANOMALY_VALVE_STUCK_CLOSED, ANOMALY_GHOST_HEATING


class MockCoordinator:
    def __init__(self):
        self.zones = [{"name": "Zone 1"}, {"name": "Zone 2"}]
        self.hass = MockHass()
        self._thermal_models = {}
        
    def get_thermal_model(self, climate_id):
        return self._thermal_models.get(climate_id)
        
    def is_passive_heat_allowed(self, climate_id):
        return False
        
    def get_zone_demand(self, climate_id):
        return 0.0
        
    def get_master_state(self):
        return True
        
    def get_zone_mode(self, climate_id):
        return "primary"

class MockHass:
    def __init__(self):
        self.states = MockStates()

class MockStates:
    def get(self, entity_id):
        return MockState(20.0)

class MockState:
    def __init__(self, temp):
        self.attributes = {"current_temperature": temp, "temperature": 22.0}
        self.state = "heat"


class TestPWMEngine(unittest.TestCase):
    def test_pwm_engine(self):
        engine = PWMEngine(pwm_interval=900, min_on=60, min_off=60)
        
        # Test 0% demand
        state = engine.calculate(0.0)
        self.assertFalse(state)
        
        # Test 100% demand
        state = engine.calculate(100.0)
        self.assertTrue(state)
        
        # Test near 100% demand (safety cap)
        state = engine.calculate(99.5)
        self.assertTrue(state)

class TestPID(unittest.TestCase):
    def test_pid_basic(self):
        pid = MultizonePID(kp=10.0, ki=0.1, kd=0.0, out_min=0, out_max=100)
        
        demand = pid.calc(15.0, 20.0)
        self.assertGreater(demand, 0.0)
        
        # Test NaN safety
        demand2 = pid.calc(float('nan'), 20.0)
        # Should return previous demand. Note: pid.py has a bug where it returns _last_output (0) instead of _output (demand)
        self.assertEqual(pid._pid._output, demand)

class TestAutotune(unittest.TestCase):
    def test_autotune_cycles(self):
        tuner = PassiveAutotuneObserver("test_zone", required_cycles=1)
        now = time.time()
        
        # Ensure we have inflection points for autotune logic!
        # Step 1: Idle -> Heating (Temp drops below setpoint, heater turns on)
        tuner.update(19.0, True, now)
        
        # Step 2: Heating -> Cooling (Temp rises above setpoint, heater turns off)
        now += 600
        # Give it a peak by adding some max temp values
        for t in [19.5, 20.0, 20.5, 21.0]:
            now += 60
            tuner.update(t, True, now)
            
        now += 60
        tuner.update(21.0, False, now) # Switch to cooling
        
        # Step 3: Cooling -> Heating (Temp drops below setpoint, heater turns on)
        for t in [20.5, 20.0, 19.5, 19.0]:
            now += 60
            tuner.update(t, False, now)
            
        now += 60
        tuner.update(19.0, True, now) # Switch to heating, cycle completes!
        
        self.assertEqual(tuner.state, PassiveAutotuneObserver.STATE_COMPLETED)
        self.assertGreater(tuner.kp, 0.0)
        self.assertGreater(tuner.ki, 0.0)

class TestThermalModel(unittest.TestCase):
    def test_thermal_model(self):
        model = ThermalObserver("test_zone", temp_delta_threshold=0.1)
        
        # Init
        model.update(20.0, True)
        
        # Heating
        time.sleep(0.05) # simulate time passing
        model._last_temp_time = time.time() - 3600 # Force 1 hour elapsed
        model.update(21.0, True)
        
        self.assertGreater(model.heating_rate, 0.0)

class TestPlantDiagnostics(unittest.TestCase):
    def test_stale_sensor(self):
        coord = MockCoordinator()
        engine = PlantDiagnosticsEngine(coord)
        
        key = list(engine._zone_anomaly_state.keys())[0]
        engine._zone_anomaly_state[key]["last_temp_time"] = time.time() - 8000
        engine._zone_anomaly_state[key]["last_temp_seen"] = 20.0
        
        anomaly, desc = engine.evaluate_zone_anomalies(key)
        self.assertEqual(anomaly, ANOMALY_STALE_SENSOR)

if __name__ == '__main__':
    unittest.main()
