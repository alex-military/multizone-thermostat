import sys
import os
import asyncio
from datetime import datetime, timedelta
import logging

sys.path.append(os.path.dirname(__file__))

from custom_components.multizone_thermostat.coordinator import MultizoneCoordinator
from custom_components.multizone_thermostat.const import CONF_ZONES, CONF_ZONE_NAME, CONF_GLOBAL_CALENDAR
import homeassistant.util.dt as dt_util

logging.basicConfig(level=logging.DEBUG)

class MockState:
    def __init__(self, state, attributes=None):
        self.state = state
        self.attributes = attributes or {}

class MockHass:
    def __init__(self):
        self.data = {}
        self.states = MockStateManager()
        self.services = MockServiceRegistry()
        self.config_entries = MockConfigEntries()
        
    def async_create_task(self, coro):
        return asyncio.create_task(coro)

class MockStateManager:
    def __init__(self):
        self._states = {
            "climate.multizone_thermostat_bagno": MockState("heat", {"current_temperature": 18.0, "temperature": 20.0}),
            "climate.multizone_thermostat_sala": MockState("heat", {"current_temperature": 19.5, "temperature": 21.0}),
        }
    def get(self, entity_id):
        return self._states.get(entity_id)

class MockServiceRegistry:
    def __init__(self):
        self.calendar_events = []
    
    async def async_call(self, domain, service, service_data, blocking=False, return_response=False, context=None):
        if domain == "calendar" and service == "get_events":
            return {
                service_data["entity_id"]: {
                    "events": self.calendar_events
                }
            }
        return None

class MockConfigEntries:
    def async_update_entry(self, entry, data):
        pass

class MockStore:
    def __init__(self, *args, **kwargs):
        pass
    async def async_load(self):
        return {}
    async def async_save(self, data):
        pass

class MockConfigEntry:
    def __init__(self, data):
        self.entry_id = "test_entry"
        self.data = data

async def run_simulation():
    print("--- Starting Calendar & Smart Start Simulation ---")
    
    # Mock Store to avoid file IO in tests
    from custom_components.multizone_thermostat import coordinator
    coordinator.Store = MockStore
    from custom_components.multizone_thermostat.const import make_zone_entity_id

    hass = MockHass()
    
    config_data = {
        CONF_ZONES: [
            {CONF_ZONE_NAME: "Bagno", "zone_climates": ["climate.multizone_thermostat_bagno"]},
            {CONF_ZONE_NAME: "Sala", "zone_climates": ["climate.multizone_thermostat_sala"]}
        ],
        CONF_GLOBAL_CALENDAR: "calendar.thermostat"
    }
    entry = MockConfigEntry(config_data)
    
    coord = MultizoneCoordinator(hass, entry)
    await coord.async_load_storage()
    
    bagno_id = make_zone_entity_id("Bagno")
    sala_id = make_zone_entity_id("Sala")
    
    # Fake thermal model for Smart Start (0.5 degrees per hour heating rate)
    coord._thermal_models[bagno_id].heating_rate = 0.5 
    coord._thermal_models[sala_id].heating_rate = 0.5 
    
    # Set a base preset to fallback on
    coord._presets["eco"] = {
        bagno_id: {"target_temp": 16.0},
        sala_id: {"target_temp": 16.0}
    }
    
    # Scenario 1: A standard event starts right now
    print("\n--- SCENARIO 1: Event Starts Now ---")
    now = dt_util.now()
    hass.services.calendar_events = [
        {
            "start": (now - timedelta(minutes=5)).isoformat(),
            "end": (now + timedelta(hours=2)).isoformat(),
            "summary": "Comfort, Bagno: 24, Sala: Bypass"
        }
    ]
    
    await coord._async_check_global_calendar(now)
    
    print(f"Calendar Active Event ID: {coord._calendar_active_event_id}")
    print(f"Calendar Temp Overrides: {coord._calendar_temp_overrides}")
    print(f"Calendar Mode Overrides: {coord._calendar_mode_overrides}")
    print(f"Zone Bagno Mode: {coord.get_zone_mode('climate.bagno')}")
    print(f"Zone Sala Mode: {coord.get_zone_mode('climate.sala')}")

    # Scenario 2: Smart Start (Next event requires pre-heating)
    # Current time is 10:00. Next event starts at 12:00. 
    # Bagno is currently 18.0C. Target will be 24.0C.
    # Delta is 6.0C. Heating rate is 0.5C/hour.
    # It takes 12 hours to heat! So it should start IMMEDIATELY.
    print("\n--- SCENARIO 2: Smart Start Pre-Heating ---")
    
    # Let's say target is 20.0C, current is 18.0C. Delta = 2.0C.
    # Time needed = 2.0 / 0.5 = 4 hours.
    # Next event starts in 2 hours (12:00). So it's already late, Smart Start MUST trigger.
    
    hass.services.calendar_events = [
        {
            "start": (now + timedelta(hours=2)).isoformat(),
            "end": (now + timedelta(hours=5)).isoformat(),
            "summary": "Eco, Bagno: 20 SET"
        }
    ]
    
    # Clear current event
    coord._calendar_active_event_id = None
    coord._calendar_temp_overrides.clear()
    coord._calendar_mode_overrides.clear()
    
    await coord._async_check_global_calendar(now)
    
    print(f"Calendar Temp Overrides (Smart Start injected): {coord._calendar_temp_overrides}")
    
    # Scenario 3: Smart Start (Too early to pre-heat)
    print("\n--- SCENARIO 3: Smart Start (Too early) ---")
    
    coord._calendar_temp_overrides.clear()
    
    # Target 19.0C, current 18.0C. Delta = 1.0C.
    # Time needed = 1.0 / 0.5 = 2 hours.
    # Next event starts in 5 hours. So it should NOT trigger yet.
    
    hass.services.calendar_events = [
        {
            "start": (now + timedelta(hours=5)).isoformat(),
            "end": (now + timedelta(hours=8)).isoformat(),
            "summary": "Eco, Bagno: 19.0"
        }
    ]
    
    await coord._async_check_global_calendar(now)
    
    print(f"Calendar Temp Overrides (Should be empty): {coord._calendar_temp_overrides}")

if __name__ == "__main__":
    asyncio.run(run_simulation())
