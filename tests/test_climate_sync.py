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


@pytest.mark.asyncio
async def test_pending_trv_confirmation_with_internal_context_unblocks_knob(sync_manager):
    """Verify that a TRV confirmation event carrying _internal_context clears _pending_trv_targets so subsequent physical knob turns work."""
    trv_state = MagicMock(
        state=HVACMode.HEAT,
        attributes={ATTR_TEMPERATURE: 20.0, "current_temperature": 19.5, "min_temp": 5.0, "max_temp": 35.0, "target_temp_step": 0.5},
    )
    sync_manager.hass.states.get.return_value = trv_state
    sync_manager._coordinator.get_persistent_data.return_value = True

    # 1. Sync sends 21.0 -> puts climate.trv_1 in _pending_trv_targets
    await sync_manager.async_sync_trvs(
        master_hvac_mode=HVACMode.HEAT,
        master_target_temp=21.0,
        master_current_temp=19.5,
        safety_fallback_active=False,
        has_external_sensor=False,
    )
    assert sync_manager._pending_trv_targets.get("climate.trv_1") == 21.0

    # 2. TRV echoes state change with _internal_context
    ack_event = MagicMock()
    ack_event.context.id = sync_manager.internal_context.id
    ack_event.data = {
        "entity_id": "climate.trv_1",
        "old_state": MagicMock(state=HVACMode.HEAT, attributes={ATTR_TEMPERATURE: 20.0}),
        "new_state": MagicMock(state=HVACMode.HEAT, attributes={ATTR_TEMPERATURE: 21.0}),
    }
    mode, delta = await sync_manager.process_trv_change(
        event=ack_event,
        master_context_id="master_ctx",
        master_hvac_mode=HVACMode.HEAT,
        master_min_temp=5.0,
        master_max_temp=35.0,
    )
    assert mode is None and delta is None
    assert "climate.trv_1" not in sync_manager._pending_trv_targets
    assert sync_manager.trv_health["climate.trv_1"]["sync_status"] == "IN_SYNC"

    # 3. User turns physical TRV knob from 21.0 to 22.5 (external context)
    knob_event = MagicMock()
    knob_event.context.id = "user_physical_knob_ctx"
    knob_event.data = {
        "entity_id": "climate.trv_1",
        "old_state": MagicMock(state=HVACMode.HEAT, attributes={ATTR_TEMPERATURE: 21.0}),
        "new_state": MagicMock(state=HVACMode.HEAT, attributes={ATTR_TEMPERATURE: 22.5}),
    }
    mode2, delta2 = await sync_manager.process_trv_change(
        event=knob_event,
        master_context_id="master_ctx",
        master_hvac_mode=HVACMode.HEAT,
        master_min_temp=5.0,
        master_max_temp=35.0,
    )
    assert mode2 is None
    assert delta2 == 1.5


@pytest.mark.asyncio
async def test_calibration_offset_does_not_double_before_trv_temp_updates(sync_manager):
    """Verify calling async_sync_trvs twice before TRV updates current_temperature does not double the calibration offset."""
    trv_state = MagicMock(
        state=HVACMode.HEAT,
        attributes={ATTR_TEMPERATURE: 21.0, "current_temperature": 22.0, "min_temp": 5.0, "max_temp": 35.0},
    )
    calib_state = MagicMock(state="0.0", attributes={"min": -5.0, "max": 5.0})

    def get_state(eid):
        if eid == "climate.trv_1":
            return trv_state
        if eid == "number.trv_1_cal":
            return calib_state
        return None

    sync_manager.hass.states.get.side_effect = get_state

    # Call 1: master_current_temp=20.0, trv_current=22.0, calib=0.0 -> offset = -2.0
    await sync_manager.async_sync_trvs(
        master_hvac_mode=HVACMode.HEAT,
        master_target_temp=21.0,
        master_current_temp=20.0,
        safety_fallback_active=False,
        has_external_sensor=True,
    )
    # Simulate HA immediately updating number.trv_1_cal to "-2.0" while trv_current is still 22.0
    calib_state.state = "-2.0"
    sync_manager.hass.services.async_call.reset_mock()

    # Call 2: trv_current is still 22.0 -> offset must stay -2.0 (NOT become -4.0!)
    await sync_manager.async_sync_trvs(
        master_hvac_mode=HVACMode.HEAT,
        master_target_temp=21.5,
        master_current_temp=20.0,
        safety_fallback_active=False,
        has_external_sensor=True,
    )
    for call in sync_manager.hass.services.async_call.call_args_list:
        domain, service, data = call.args[0], call.args[1], call.args[2]
        if domain == "number" and service == "set_value":
            assert data["value"] == -2.0
