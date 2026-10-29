import pytest
import asyncio
import importlib.abc
import importlib.machinery
import sys
from unittest.mock import MagicMock, AsyncMock

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
            if fullname == 'homeassistant.components.climate.const':
                mock_module.HVACMode = MagicMock()
                mock_module.HVACMode.HEAT = 'heat'
                mock_module.HVACMode.OFF = 'off'
            if fullname == 'homeassistant.core':
                mock_module.callback = lambda f: f
            if fullname == 'homeassistant.const':
                mock_module.ATTR_ENTITY_ID = 'entity_id'
            if fullname == 'homeassistant.util':
                from tests.dummy_ha.homeassistant.util import slugify as dummy_slugify
                mock_module.slugify = dummy_slugify
            return importlib.machinery.ModuleSpec(fullname, HomeAssistantMockLoader(mock_module))
        return None

if not any(isinstance(finder, HomeAssistantMockFinder) for finder in sys.meta_path):
    sys.meta_path.insert(0, HomeAssistantMockFinder())

from custom_components.multizone_thermostat.zone_manager import ZoneManager
from custom_components.multizone_thermostat.const import (
    CONF_ZONE_NAME,
    CONF_ZONE_WINDOW_SENSOR,
    CONF_ZONE_CLIMATES,
    ZONE_MODE_PRIMARY,
    ZONE_MODE_BYPASS,
    GLOBAL_PRESET_MANUAL,
    GLOBAL_PRESET_AWAY,
    GLOBAL_PRESET_SLEEP,
    GLOBAL_PRESET_COMFORT,
    make_zone_entity_id
)
from homeassistant.components.climate.const import HVACMode

class DummyState:
    def __init__(self, entity_id, state):
        self.entity_id = entity_id
        self.state = state
        self.attributes = {}

class DummyEvent:
    def __init__(self, event_type, data):
        self.event_type = event_type
        self.data = data

@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.states.get.return_value = None
    hass.services.async_call = AsyncMock()
    def _create_task(coro):
        if asyncio.iscoroutine(coro):
            try:
                loop = asyncio.get_running_loop()
                return loop.create_task(coro)
            except RuntimeError:
                coro.close()
                return MagicMock()
        return MagicMock()
    hass.async_create_task = MagicMock(side_effect=_create_task)
    return hass

@pytest.fixture
def mock_coordinator():
    coordinator = MagicMock()
    coordinator.zones = [
        {
            CONF_ZONE_NAME: 'Living Room',
            CONF_ZONE_WINDOW_SENSOR: 'binary_sensor.living_room_window',
            'zone_climates': ['climate.living_room_trv']
        }
    ]
    coordinator.demand_aggregator = MagicMock()
    coordinator._settings = {}
    coordinator._settings_store = MagicMock()
    coordinator._settings_store.async_save = AsyncMock()
    coordinator._climate_callbacks = {}
    coordinator._async_save_presets_storage = AsyncMock()
    coordinator._select_entities = {}
    coordinator._master_state = False
    coordinator.is_zone_in_frost_emergency = MagicMock(return_value=False)
    coordinator.async_save_storage = AsyncMock()
    coordinator.async_apply_master_on = AsyncMock()
    coordinator.record_diagnostic_event = MagicMock()
    return coordinator
@pytest.fixture
def zone_manager(mock_hass, mock_coordinator):
    return ZoneManager(mock_hass, mock_coordinator)

def test_initialization(zone_manager, mock_coordinator):
    assert zone_manager.zones == mock_coordinator.zones
    zone_id = make_zone_entity_id("Living Room")
    assert zone_manager._zone_modes[zone_id] == ZONE_MODE_PRIMARY
    assert zone_manager.current_global_preset == GLOBAL_PRESET_MANUAL

def test_get_zone(zone_manager):
    zone_id = make_zone_entity_id("Living Room")
    zone = zone_manager.get_zone(zone_id)
    assert zone is not None
    assert zone[CONF_ZONE_NAME] == "Living Room"

def test_get_zone_mode(zone_manager):
    zone_id = make_zone_entity_id("Living Room")
    assert zone_manager.get_zone_mode(zone_id) == ZONE_MODE_PRIMARY

@pytest.mark.asyncio
async def test_set_zone_mode(zone_manager, mock_coordinator, mock_hass):
    zone_id = make_zone_entity_id("Living Room")
    zone_manager.set_zone_mode(zone_id, "secondary")
    assert zone_manager.get_zone_mode(zone_id) == "secondary"
    mock_coordinator.demand_aggregator.set_zone_mode.assert_called_with(zone_id, "secondary")
    mock_hass.async_create_task.assert_called()

@pytest.mark.asyncio
async def test_async_set_global_preset(zone_manager, mock_coordinator, mock_hass):
    # Setting non-manual preset should enable master switch
    await zone_manager.async_set_global_preset("eco")
    assert zone_manager.current_global_preset == "eco"
    pass

@pytest.mark.asyncio
async def test_async_on_window_state_changed_open(zone_manager, mock_coordinator, mock_hass):
    zone_id = make_zone_entity_id("Living Room")
    zone_select_mock = MagicMock()
    zone_select_mock.async_select_option = AsyncMock()
    mock_coordinator._select_entities[f"zone_mode_{zone_id}"] = zone_select_mock
    
    event = DummyEvent("state_changed", {
        "entity_id": "binary_sensor.living_room_window",
        "new_state": DummyState("binary_sensor.living_room_window", "on")
    })
    
    # Test Window Open
    print(f"DEBUG: {event.data=}")
    print(f"DEBUG: {zone_manager.zones=}")
    zone_manager.async_on_window_state_changed(event)
    print(f"DEBUG: {mock_hass.async_create_task.call_args_list=}")
    
    # Expect bypass mode to be requested
    mock_hass.async_create_task.assert_called()
    assert zone_id in zone_manager._pre_window_state

@pytest.mark.asyncio
async def test_async_on_window_state_changed_close(zone_manager, mock_coordinator, mock_hass):
    zone_id = make_zone_entity_id("Living Room")
    zone_select_mock = MagicMock()
    zone_select_mock.async_select_option = AsyncMock()
    mock_coordinator._select_entities[f"zone_mode_{zone_id}"] = zone_select_mock
    
    # Pre-condition: window was opened
    zone_manager._pre_window_state[zone_id] = ZONE_MODE_PRIMARY
    
    event = DummyEvent("state_changed", {
        "entity_id": "binary_sensor.living_room_window",
        "new_state": DummyState("binary_sensor.living_room_window", "off")
    })
    
    # Test Window Close
    zone_manager.async_on_window_state_changed(event)
    
    # Expect previous mode to be restored
    assert zone_id not in zone_manager._pre_window_state
    mock_hass.async_create_task.assert_called()




