"""Tests for the ZoneSyncManager."""
from unittest.mock import AsyncMock, MagicMock
import pytest

from homeassistant.components.climate import HVACMode
from homeassistant.const import ATTR_TEMPERATURE

from custom_components.multizone_thermostat.sync_manager import ZoneSyncManager

@pytest.fixture
def sync_manager():
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    coordinator = MagicMock()
    
    return ZoneSyncManager(
        hass=hass,
        coordinator=coordinator,
        zone_name="Living Room",
        entity_id="climate.living_room",
        climates=["climate.trv_1"],
        switches=["switch.relay_1"],
        calibrations={"climate.trv_1": "number.trv_1_cal"},
    )

@pytest.mark.asyncio
async def test_sync_trvs_off(sync_manager):
    """Test syncing TRVs when master is OFF."""
    sync_manager.hass.states.get.return_value = MagicMock(state=HVACMode.HEAT, attributes={})
    sync_manager.hass.services.async_call = AsyncMock()
    
    await sync_manager.async_sync_trvs(
        master_hvac_mode=HVACMode.OFF,
        master_target_temp=20.0,
        master_current_temp=21.0,
        safety_fallback_active=False,
        has_external_sensor=False
    )
    
    sync_manager.hass.services.async_call.assert_called_with(
        "climate", "set_hvac_mode", {"entity_id": "climate.trv_1", "hvac_mode": HVACMode.OFF},
        blocking=True, context=sync_manager.internal_context
    )

@pytest.mark.asyncio
async def test_process_trv_change_physical_sync(sync_manager):
    """Test processing a physical TRV knob change."""
    event = MagicMock()
    event.context.id = "external_context"
    event.data = {
        "entity_id": "climate.trv_1",
        "old_state": MagicMock(state=HVACMode.HEAT, attributes={ATTR_TEMPERATURE: 20.0}),
        "new_state": MagicMock(state=HVACMode.HEAT, attributes={ATTR_TEMPERATURE: 21.0})
    }
    sync_manager._last_known_trv_targets["climate.trv_1"] = 20.0
    sync_manager._coordinator.get_persistent_data.return_value = True
    
    new_mode, delta = await sync_manager.process_trv_change(
        event=event,
        master_context_id="master_context",
        master_hvac_mode=HVACMode.HEAT,
        master_min_temp=5.0,
        master_max_temp=35.0
    )
    
    assert new_mode is None
    assert delta == 1.0  # 21.0 - 20.0
