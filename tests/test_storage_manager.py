import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock
import sys
import os

# Aggiungo la root del component per permettere gli import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from homeassistant.core import HomeAssistant
from custom_components.multizone_thermostat.storage.storage_manager import StorageManager

class TestStorageManager(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.hass = MagicMock()
        def mock_create_task(coro):
            return asyncio.create_task(coro)
        self.hass.async_create_task = mock_create_task
        self.manager = StorageManager(self.hass, "test_entry")
        
        # Override asyncio.sleep to not waste time during tests
        self.original_sleep = asyncio.sleep
        asyncio.sleep = AsyncMock()

    async def asyncTearDown(self):
        asyncio.sleep = self.original_sleep
        self.manager.async_unload()

    async def test_initialization_loads_data(self):
        from unittest.mock import patch
        with patch('homeassistant.helpers.storage.Store.async_load', return_value={"zone_modes": {"z1": "primary"}}):
            await self.manager.async_initialize()
            self.assertEqual(self.manager.settings["zone_modes"]["z1"], "primary")

    async def test_debounced_save_thermal_states(self):
        class MockThermal:
            def dump_state(self):
                return {"val": 99}
                
        from unittest.mock import patch
        with patch.object(self.manager._settings_store, 'async_delay_save') as mock_delay_save:
            self.manager.debounced_save_thermal_states({"z1": MockThermal()})
            mock_delay_save.assert_called_once()
            self.assertEqual(self.manager.settings["thermal_models"]["z1"]["val"], 99)

    async def test_set_persistent_data(self):
        from unittest.mock import patch
        with patch.object(self.manager._settings_store, 'async_delay_save') as mock_delay_save:
            await self.manager.async_set_data("test_key", 42)
            self.assertEqual(self.manager.get_data("test_key"), 42)
            mock_delay_save.assert_called_once()

if __name__ == '__main__':
    unittest.main()


