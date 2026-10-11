import sys
import os

# Set up PYTHONPATH equivalent
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
dummy_ha_dir = os.path.join(current_dir, "dummy_ha")
sys.path.insert(0, dummy_ha_dir)
sys.path.insert(0, parent_dir)

from homeassistant.core import HomeAssistant

from custom_components.multizone_thermostat.plant_diagnostics.engine import PlantDiagnosticsEngine
from custom_components.multizone_thermostat.plant_diagnostics.const import (
    ANOMALY_NONE,
    ANOMALY_VALVE_STUCK_CLOSED,
)

class MockState:
    def __init__(self, state, attributes=None, last_reported=None):
        self.state = state
        self.attributes = attributes or {}
        self.last_reported = last_reported
        self.last_updated = last_reported

class MockHass:
    def __init__(self):
        self.states = MockStateRegistry()
        self.data = {}

class MockStateRegistry:
    def __init__(self):
        self._states = {}
    
    def get(self, entity_id):
        return self._states.get(entity_id)
        
    def set(self, entity_id, state_obj):
        self._states[entity_id] = state_obj

from custom_components.multizone_thermostat.const import make_zone_entity_id

class MockZoneManager:
    def __init__(self, zone):
        self._zone = zone
    def get_zone(self, climate_id):
        return self._zone
    def is_passive_heat_allowed(self, climate_id):
        return False

class MockCoordinator:
    def __init__(self, hass):
        self.hass = hass
        self.zones = [{"name": "Zona 1", "temp_sensor": "sensor.temp_1", "climate_entities": [], "zone_name": "zona_1"}]
        self.zone_manager = MockZoneManager(self.zones[0])
        cid = make_zone_entity_id("zona_1")
        self._zone_demands = {cid: 100.0}
        self._zone_modes = {cid: "heat"}
        self._master_state = True
        self.opentherm_entity = None
        self.weather_sensor_id = None
        
    def get_zone_demand(self, climate_id):
        return self._zone_demands.get(climate_id, 0.0)
        
    def get_zone_mode(self, climate_id):
        return self._zone_modes.get(climate_id, "heat")
        
    def get_master_state(self):
        return self._master_state

    def _get_zone(self, climate_id):
        return self.zones[0]

    def is_passive_heat_allowed(self, climate_id):
        return False

def test_engine():
    hass = MockHass()
    coordinator = MockCoordinator(hass)
    engine = PlantDiagnosticsEngine(coordinator)
    cid = make_zone_entity_id("zona_1")
    
    assert engine is not None
    assert cid in engine._zone_anomaly_state
    
    import time
    now = time.time()
    
    # Mock states
    hass.states.set(cid, MockState("heat", {"current_temperature": 20.0, "temperature": 22.0}))
    
    # Boiler on
    engine.record_boiler_state(True)
    
    # 1. First evaluation: sets start time
    anomaly, desc = engine.evaluate_zone_anomalies(cid)
    assert anomaly == ANOMALY_NONE
    
    # 2. Simulate 80 minutes later, temp same
    state = engine._zone_anomaly_state[cid]
    state["high_demand_start_time"] = now - 4800 # 80 mins ago
    state["high_demand_start_temp"] = 20.0
    
    anomaly, desc = engine.evaluate_zone_anomalies(cid)
    assert anomaly == ANOMALY_VALVE_STUCK_CLOSED
    print("All tests passed successfully.")

if __name__ == "__main__":
    test_engine()

