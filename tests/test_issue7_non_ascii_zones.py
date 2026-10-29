"""Tests for Issue #7: Non-ASCII zone names transliteration and slugify handling."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from custom_components.multizone_thermostat.const import (
    DOMAIN,
    CONF_ZONE_NAME,
    HVAC_MODE_HEAT,
    ZONE_MODE_PRIMARY,
    make_zone_entity_id,
)
from custom_components.multizone_thermostat.zone_controller import ZoneController


class DummyState:
    def __init__(self, state, current_temp=None, target_temp=None, domain="climate"):
        self.state = state
        self.attributes = {}
        if current_temp is not None:
            self.attributes["current_temperature"] = current_temp
        if target_temp is not None:
            self.attributes["temperature"] = target_temp
        self.domain = domain


def create_mock_coordinator(zones):
    coordinator = MagicMock()
    coordinator.zones = zones
    coordinator.weather_sensor_id = None
    coordinator.is_dhw_active = False
    zone_demands = {}

    def get_demand(cid):
        return zone_demands.get(cid, 0.0)

    def set_demand(cid, val):
        zone_demands[cid] = val

    coordinator.zone_manager = MagicMock()
    coordinator.zone_manager.get_zone_mode = MagicMock(return_value=ZONE_MODE_PRIMARY)
    coordinator.get_zone_mode = coordinator.zone_manager.get_zone_mode

    coordinator.demand_aggregator = MagicMock()
    coordinator.demand_aggregator.get_zone_demand = MagicMock(side_effect=get_demand)
    coordinator.demand_aggregator.set_zone_demand = MagicMock(side_effect=set_demand)
    coordinator.get_zone_demand = coordinator.demand_aggregator.get_zone_demand
    coordinator.set_zone_demand = coordinator.demand_aggregator.set_zone_demand

    coordinator.get_persistent_data = MagicMock(return_value=0.0)
    coordinator.debounced_save_thermal_states = MagicMock()
    coordinator.storage = MagicMock()
    coordinator.storage.async_save_autotuner_states = AsyncMock()
    coordinator.storage.async_save_thermal_states = AsyncMock()
    coordinator.storage.async_debounced_save_thermal_states = MagicMock()
    coordinator.plant_diagnostics = MagicMock()
    coordinator.plant_diagnostics.has_critical_sensor_fault = MagicMock(return_value=False)
    return coordinator, zone_demands


def test_make_zone_entity_id_ascii_backward_compatibility():
    """Verify that standard ASCII names produce identical entity IDs as before."""
    assert make_zone_entity_id("Living Room") == f"climate.{DOMAIN}_living_room"
    assert make_zone_entity_id("Camera da letto") == f"climate.{DOMAIN}_camera_da_letto"
    assert make_zone_entity_id("Zone-1") == f"climate.{DOMAIN}_zone_1"
    assert make_zone_entity_id("Bedroom") == f"climate.{DOMAIN}_bedroom"
    assert make_zone_entity_id("zona_1") == f"climate.{DOMAIN}_zona_1"


def test_make_zone_entity_id_cyrillic_names():
    """Verify Cyrillic zone names are properly transliterated to valid HA slugs."""
    cid_spalnaia = make_zone_entity_id("Спальная")
    assert cid_spalnaia == f"climate.{DOMAIN}_spalnaia"

    cid_kukhnia = make_zone_entity_id("Кухня")
    assert cid_kukhnia == f"climate.{DOMAIN}_kukhnia"

    cid_gostinaia = make_zone_entity_id("Гостиная")
    assert cid_gostinaia == f"climate.{DOMAIN}_gostinaia"

    # All characters after prefix must be strictly in [a-z0-9_]
    object_id = cid_spalnaia.replace(f"climate.{DOMAIN}_", "")
    assert object_id.isascii()
    assert all(c.isalnum() or c == "_" for c in object_id)


def test_make_zone_entity_id_accented_names():
    """Verify Latin accented names are normalized and stripped of diacritics."""
    assert make_zone_entity_id("Café") == f"climate.{DOMAIN}_cafe"
    assert make_zone_entity_id("Büro") == f"climate.{DOMAIN}_buro"
    assert make_zone_entity_id("Séjour") == f"climate.{DOMAIN}_sejour"


def test_make_zone_entity_id_fallback_robustness():
    """Verify fallback behavior when slugify receives empty, invalid, or error inputs."""
    assert make_zone_entity_id("") == f"climate.{DOMAIN}_zone"
    assert make_zone_entity_id(None) == f"climate.{DOMAIN}_zone"
    assert make_zone_entity_id("---___---") == f"climate.{DOMAIN}_zone"

    # Simulate slugify exception
    with patch("custom_components.multizone_thermostat.const.slugify", side_effect=Exception("Mocked error")):
        assert make_zone_entity_id("Safe Fallback Zone") == f"climate.{DOMAIN}_safe_fallback_zone"
        assert make_zone_entity_id("") == f"climate.{DOMAIN}_zone"


@pytest.mark.asyncio
async def test_zone_controller_non_ascii_integration():
    """Verify ZoneController properly initializes and updates demand for non-ASCII zones."""
    zones = [
        {CONF_ZONE_NAME: "Спальная"},
        {CONF_ZONE_NAME: "Кухня"},
        {CONF_ZONE_NAME: "Café"},
        {CONF_ZONE_NAME: "Büro"},
    ]
    hass = MagicMock()
    coordinator, demands = create_mock_coordinator(zones)
    zc = ZoneController(hass, coordinator)

    expected_ids = [
        f"climate.{DOMAIN}_spalnaia",
        f"climate.{DOMAIN}_kukhnia",
        f"climate.{DOMAIN}_cafe",
        f"climate.{DOMAIN}_buro",
    ]

    for eid in expected_ids:
        assert eid in zc.pids
        assert eid in zc.autotuners
        assert eid in zc.thermal_models

    # Update state for Cyrillic zone 'Спальная'
    spalnaia_id = f"climate.{DOMAIN}_spalnaia"
    state = DummyState(HVAC_MODE_HEAT, current_temp=18.0, target_temp=21.0)
    demand = await zc.async_update_zone(spalnaia_id, state)

    # PID default Kp=100 with error=3.0 produces 100% demand
    assert demand == 100.0
    assert demands.get(spalnaia_id) == 100.0


@pytest.mark.asyncio
async def test_zone_controller_warning_on_unregistered_entity(caplog):
    """Verify that an unregistered entity_id logs a WARNING and aborts demand calculation."""
    zones = [{CONF_ZONE_NAME: "Living Room"}]
    hass = MagicMock()
    coordinator, demands = create_mock_coordinator(zones)
    zc = ZoneController(hass, coordinator)

    unknown_id = f"climate.{DOMAIN}_unknown_non_existent"
    state = DummyState(HVAC_MODE_HEAT, current_temp=19.0, target_temp=22.0)

    with caplog.at_level("WARNING"):
        demand = await zc.async_update_zone(unknown_id, state)

    assert demand == 0.0
    assert unknown_id not in demands
    # Check that warning was logged
    warning_records = [r for r in caplog.records if r.levelname == "WARNING" and unknown_id in r.message]
    assert len(warning_records) >= 1
    assert "not registered" in warning_records[0].message or "Unknown zone entity" in warning_records[0].message
