"""Unit tests for extracted CoolingPolicy and MasterController modules."""
from unittest.mock import MagicMock, AsyncMock
import pytest

from custom_components.multizone_thermostat.cooling_policy import CoolingPolicy
from custom_components.multizone_thermostat.master_controller import MasterController
from custom_components.multizone_thermostat.const import (
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    HVAC_MODE_OFF,
    CONF_ZONE_NAME,
    SPLIT_ROLE_COOLING_ONLY,
    make_zone_entity_id,
)


def test_cooling_policy_central_and_zone_rules():
    """Verify CoolingPolicy determines cooling availability accurately."""
    coord = MagicMock()
    coord.enable_heat_pump = True
    coord.heat_pump_cooling = True
    coord.split_manager.has_split.return_value = False
    coord.zones = [
        {"name": "Salotto", "allow_cooling": True},
        {"name": "Camera", "allow_cooling": False},
        {"name": "Bagno", "emitter_type": "radiator"},
        {"name": "Mansarda", "emitter_type": "fancoil"},
    ]

    policy = CoolingPolicy(coord)

    # 1. Central cool is enabled
    assert policy.can_central_cool() is True

    # 2. Zone cooling capabilities
    salotto_id = make_zone_entity_id("Salotto")
    camera_id = make_zone_entity_id("Camera")
    bagno_id = make_zone_entity_id("Bagno")
    mansarda_id = make_zone_entity_id("Mansarda")

    assert policy.can_zone_cool(salotto_id) is True
    assert policy.can_zone_cool(camera_id) is False
    assert policy.can_zone_cool(bagno_id) is False
    assert policy.can_zone_cool(mansarda_id) is True

    # 3. If central cool disabled, hydronic cooling disabled unless split AC present
    coord.heat_pump_cooling = False
    assert policy.can_central_cool() is False
    assert policy.can_zone_cool(salotto_id) is False

    # 4. Split AC cooling
    coord.split_manager.has_split.return_value = True
    coord.split_manager.get_split_info.return_value = {"split_role": SPLIT_ROLE_COOLING_ONLY}
    assert policy.can_zone_cool(salotto_id) is True


@pytest.mark.asyncio
async def test_master_controller_set_mode_and_apply():
    """Verify MasterController coordinates whole-house modes."""
    coord = MagicMock()
    coord.hass.services.async_call = AsyncMock()
    coord.zones = [{"name": "Living"}]
    coord.master_hvac_mode = HVAC_MODE_HEAT
    coord.get_master_state.return_value = True
    coord.can_zone_cool.return_value = True
    coord.zone_manager.get_zone_mode.return_value = "primary"
    coord.zone_manager.get_preset_temperature.return_value = 21.0
    coord.async_set_persistent_data = AsyncMock()
    coord.async_update_all_climates = AsyncMock()
    coord._select_entities = {}

    ctrl = MasterController(coord)

    # 1. Switch to COOL mode
    await ctrl.async_set_master_hvac_mode(HVAC_MODE_COOL)
    assert coord.master_hvac_mode == HVAC_MODE_COOL
    coord.async_set_persistent_data.assert_called_once()

    # 2. Apply master OFF
    coord.plant_orchestrator.boiler_backend.async_emergency_off = AsyncMock()
    await ctrl.async_apply_master_off()
    coord.plant_orchestrator.boiler_backend.async_emergency_off.assert_called_once()
