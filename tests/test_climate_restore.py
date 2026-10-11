"""Tests for the ZoneStateRestorer."""
from unittest.mock import AsyncMock, MagicMock
import pytest

from homeassistant.components.climate import HVACMode
from homeassistant.const import ATTR_TEMPERATURE

from custom_components.multizone_thermostat.state_restorer import ZoneStateRestorer

@pytest.mark.asyncio
async def test_restore_state_success():
    """Test successful restoration of state."""
    entity = AsyncMock()
    last_state = MagicMock()
    last_state.state = HVACMode.HEAT
    last_state.attributes = {ATTR_TEMPERATURE: 22.5}
    entity.async_get_last_state.return_value = last_state

    hvac_mode, target_temp = await ZoneStateRestorer.async_restore_state(entity)

    assert hvac_mode == HVACMode.HEAT
    assert target_temp == 22.5

@pytest.mark.asyncio
async def test_restore_state_fallback():
    """Test restoration fallback when last state is missing."""
    entity = AsyncMock()
    entity.async_get_last_state.return_value = None

    hvac_mode, target_temp = await ZoneStateRestorer.async_restore_state(
        entity, default_hvac_mode=HVACMode.OFF, default_target_temp=19.0
    )

    assert hvac_mode == HVACMode.OFF
    assert target_temp == 19.0
