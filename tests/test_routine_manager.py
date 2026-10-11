import sys
import datetime
from unittest.mock import MagicMock, AsyncMock, patch

class MockModule(MagicMock):
    @classmethod
    def __getattr__(cls, name):
        return MagicMock()

sys.modules['homeassistant'] = MockModule()
sys.modules['homeassistant.core'] = MockModule()
sys.modules['homeassistant.helpers'] = MockModule()
sys.modules['homeassistant.helpers.event'] = MockModule()
sys.modules['homeassistant.helpers.entity'] = MockModule()
sys.modules['homeassistant.helpers.typing'] = MockModule()
sys.modules['homeassistant.helpers.restore_state'] = MockModule()
sys.modules['homeassistant.util'] = MockModule()
sys.modules['homeassistant.util.dt'] = MockModule()
sys.modules['homeassistant.components'] = MockModule()
sys.modules['homeassistant.components.http'] = MockModule()
sys.modules['homeassistant.components.climate'] = MockModule()
sys.modules['homeassistant.components.climate.const'] = MockModule()
sys.modules['homeassistant.components.water_heater'] = MockModule()
sys.modules['homeassistant.config_entries'] = MockModule()
sys.modules['homeassistant.const'] = MockModule()
sys.modules['homeassistant.helpers.update_coordinator'] = MockModule()


mock_core = sys.modules['homeassistant.core']
mock_core.HomeAssistant = MagicMock
mock_core.Event = MagicMock
mock_core.callback = lambda x: x

from custom_components.multizone_thermostat.routine_manager import RoutineManager
from custom_components.multizone_thermostat.const import (
    KEY_NIGHT_TIME,
    KEY_MORNING_TIME,
    KEY_AUTO_NIGHT_MODE,
    KEY_GEOFENCING_TOGGLE,
    KEY_PRE_AWAY_PRESET,
    KEY_PRE_NIGHT_PRESET,
    GLOBAL_PRESET_SLEEP,
    GLOBAL_PRESET_AWAY,
    GLOBAL_PRESET_COMFORT,
)

import asyncio

async def test_geofencing_everyone_left():
    hass = MagicMock()
    hass.async_create_task = MagicMock()
    
    get_persistent_data = MagicMock(return_value=True)
    async_set_persistent_data = AsyncMock()
    get_current_global_preset = MagicMock(return_value=GLOBAL_PRESET_COMFORT)
    async_set_global_preset = AsyncMock()
    
    manager = RoutineManager(hass, "sensor", get_persistent_data, async_set_persistent_data, get_current_global_preset, async_set_global_preset)
    
    event = MagicMock()
    event.data = {"old_state": MagicMock(state="home"), "new_state": MagicMock(state="not_home")}
    manager._async_on_presence_changed(event)
    
    assert hass.async_create_task.call_count == 2
    print("test_geofencing_everyone_left PASSED")

async def test_auto_night():
    hass = MagicMock()
    hass.async_create_task = MagicMock()
    
    def get_data(key, default=None):
        if key == KEY_AUTO_NIGHT_MODE: return True
        if key == KEY_NIGHT_TIME: return "22:30"
        return default
        
    get_persistent_data = MagicMock(side_effect=get_data)
    async_set_persistent_data = AsyncMock()
    get_current_global_preset = MagicMock(return_value=GLOBAL_PRESET_COMFORT)
    async_set_global_preset = AsyncMock()
    
    manager = RoutineManager(hass, "sensor", get_persistent_data, async_set_persistent_data, get_current_global_preset, async_set_global_preset)
    
    now = datetime.datetime(2023, 1, 1, 22, 30)
    with patch("custom_components.multizone_thermostat.routine_manager.dt_util.now", return_value=now):
        manager._async_check_schedule(now)
        assert hass.async_create_task.call_count == 2
        print("test_auto_night PASSED")

async def main():
    await test_geofencing_everyone_left()
    await test_auto_night()

if __name__ == "__main__":
    asyncio.run(main())
