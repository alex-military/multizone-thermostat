"""Regression tests for SplitZoneManager fail-safe state checks, command retries, and frost priority."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.multizone_thermostat.const import (
    CONF_ZONE_NAME,
    CONF_ZONE_SPLIT_CLIMATE,
    CONF_ZONE_SPLIT_ROLE,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    SPLIT_ROLE_HEAT_COOL,
    make_zone_entity_id,
)
from custom_components.multizone_thermostat.split.split_controller import SplitZoneManager


def _make_split_manager(split_state="heat"):
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.states.get = MagicMock(return_value=SimpleNamespace(state=split_state, attributes={}))

    coord = MagicMock()
    coord.zones = [
        {
            CONF_ZONE_NAME: "Salotto",
            CONF_ZONE_SPLIT_CLIMATE: "climate.split_salotto",
            CONF_ZONE_SPLIT_ROLE: SPLIT_ROLE_HEAT_COOL,
        }
    ]
    coord.get_master_state.return_value = True
    coord.get_persistent_data.side_effect = lambda key, default=None: default
    coord.frost_protection = None
    coord.anti_frost = None

    mgr = SplitZoneManager(hass, coord)
    cid = make_zone_entity_id("Salotto")
    mgr._split_active_states[cid] = True
    return hass, coord, mgr, cid


def test_split_unavailable_does_not_suppress_hydronics():
    """If split entity is unavailable or unknown, hydronic demand must not be suppressed."""
    hass, _, mgr, cid = _make_split_manager("unavailable")
    assert mgr.should_suppress_hydronic_demand(cid) is False

    hass.states.get.return_value = SimpleNamespace(state="unknown", attributes={})
    assert mgr.should_suppress_hydronic_demand(cid) is False


def test_split_off_after_grace_period_does_not_suppress_hydronics():
    """If split remains off past command grace period, hydronics must not stay suppressed."""
    _, _, mgr, cid = _make_split_manager(HVAC_MODE_OFF)
    mgr._last_split_commands[cid] = {"mode": HVAC_MODE_HEAT, "target": 21.0}
    mgr._last_command_timestamps[cid] = 100.0

    # Within 30s grace period -> still suppressed while waiting for state update
    with patch("time.monotonic", return_value=110.0):
        assert mgr.should_suppress_hydronic_demand(cid) is True

    # Past 30s grace period -> fail-safe, stop suppressing and clear cached command
    with patch("time.monotonic", return_value=135.0):
        assert mgr.should_suppress_hydronic_demand(cid) is False
        assert cid not in mgr._last_split_commands


def test_split_frost_emergency_overrides_hydronic_suppression():
    """Active frost emergency on a zone must never be suppressed by an active split."""
    _, coord, mgr, cid = _make_split_manager("heat")
    assert mgr.should_suppress_hydronic_demand(cid) is True

    coord.frost_protection = MagicMock()
    coord.frost_protection.is_zone_in_frost_emergency = MagicMock(return_value=True)
    assert mgr.should_suppress_hydronic_demand(cid) is False


@pytest.mark.asyncio
async def test_split_sync_retries_when_service_call_fails():
    """Failed service call must not cache command so the next sync retries."""
    hass, _, mgr, cid = _make_split_manager("off")
    hass.services.async_call = AsyncMock(side_effect=RuntimeError("HA service error"))

    await mgr.async_sync_split(cid, HVAC_MODE_HEAT, 21.0)
    assert cid not in mgr._last_split_commands

    # Next attempt succeeds and caches command
    hass.services.async_call = AsyncMock()
    await mgr.async_sync_split(cid, HVAC_MODE_HEAT, 21.0)
    assert mgr._last_split_commands[cid] == {"mode": HVAC_MODE_HEAT, "target": 21.0}
    assert hass.services.async_call.await_count == 2
