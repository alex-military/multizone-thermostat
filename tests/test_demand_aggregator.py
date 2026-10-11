"""Unit test suite for DemandAggregator module."""

import importlib.abc
import importlib.machinery
import sys
from unittest.mock import MagicMock

# Custom finder to mock ANY homeassistant.* module


import pytest

from custom_components.multizone_thermostat.const import (
    CONF_ZONE_NAME,
    ZONE_MODE_BYPASS,
    ZONE_MODE_PRIMARY,
    ZONE_MODE_SECONDARY,
    make_zone_entity_id,
)
from custom_components.multizone_thermostat.demand_aggregator import (
    DEMAND_STRATEGY_MAX,
    DEMAND_STRATEGY_SUM_CAPPED,
    DEMAND_STRATEGY_WEIGHTED_AVERAGE,
    AggregatedDemand,
    DemandAggregator,
)


def test_initialization_empty():
    """Test initializing an empty demand aggregator."""
    aggregator = DemandAggregator()
    assert aggregator.strategy == DEMAND_STRATEGY_MAX
    assert aggregator.get_all_demands() == {}

    # Invalid strategy raises ValueError
    with pytest.raises(ValueError):
        DemandAggregator(strategy="invalid_strategy")


def test_initialization_with_zones():
    """Test initializing aggregator with zone definitions."""
    zones = [
        {CONF_ZONE_NAME: "Living Room"},
        {CONF_ZONE_NAME: "Bedroom"},
    ]
    aggregator = DemandAggregator(zones=zones)

    living_id = make_zone_entity_id("Living Room")
    bedroom_id = make_zone_entity_id("Bedroom")

    assert aggregator.get_zone_demand(living_id) == 0.0
    assert aggregator.get_zone_demand(bedroom_id) == 0.0
    assert aggregator.get_zone_mode(living_id) == ZONE_MODE_PRIMARY
    assert aggregator.get_zone_mode(bedroom_id) == ZONE_MODE_PRIMARY
    assert aggregator.get_zone_weight(living_id) == 1.0
    assert aggregator.get_zone_weight(bedroom_id) == 1.0


def test_demand_clamping_and_management():
    """Test setting, clamping, and resetting zone demands."""
    aggregator = DemandAggregator()
    zone_id = aggregator.register_zone("Kitchen")

    # Clamping negative to 0.0
    aggregator.set_zone_demand(zone_id, -15.0)
    assert aggregator.get_zone_demand(zone_id) == 0.0

    # Clamping over 100 to 100.0
    aggregator.set_zone_demand(zone_id, 125.0)
    assert aggregator.get_zone_demand(zone_id) == 100.0

    # Normal value
    aggregator.set_zone_demand(zone_id, 45.5)
    assert aggregator.get_zone_demand(zone_id) == 45.5

    # Reset single zone
    aggregator.reset_zone_demand(zone_id)
    assert aggregator.get_zone_demand(zone_id) == 0.0

    # Reset all demands
    zone2_id = aggregator.register_zone("Bathroom")
    aggregator.set_zone_demand(zone_id, 50.0)
    aggregator.set_zone_demand(zone2_id, 60.0)
    assert len(aggregator.get_all_demands()) == 2
    aggregator.reset_all_demands()
    assert aggregator.get_zone_demand(zone_id) == 0.0
    assert aggregator.get_zone_demand(zone2_id) == 0.0


def test_callbacks():
    """Test demand change and climate callbacks."""
    aggregator = DemandAggregator()
    zone_id = aggregator.register_zone("Office")

    demand_events = []
    aggregator.register_on_demand_changed(lambda cid, val: demand_events.append((cid, val)))

    climate_called = []
    aggregator.register_climate_callback(zone_id, lambda: climate_called.append(True))

    # Setting demand triggers callbacks
    aggregator.set_zone_demand(zone_id, 70.0)
    assert len(demand_events) == 1
    assert demand_events[0] == (zone_id, 70.0)
    assert len(climate_called) == 1

    # Setting identical demand does NOT trigger callbacks
    aggregator.set_zone_demand(zone_id, 70.0)
    assert len(demand_events) == 1
    assert len(climate_called) == 1

    # Exception in callback is caught gracefully
    aggregator.register_on_demand_changed(lambda cid, val: 1 / 0)
    aggregator.set_zone_demand(zone_id, 80.0)
    assert aggregator.get_zone_demand(zone_id) == 80.0


def test_modes_and_priority_routing():
    """Test mode assignments and helper properties."""
    aggregator = DemandAggregator()
    z1 = aggregator.register_zone("Zone1", mode=ZONE_MODE_PRIMARY)
    z2 = aggregator.register_zone("Zone2", mode=ZONE_MODE_SECONDARY)
    z3 = aggregator.register_zone("Zone3", mode=ZONE_MODE_BYPASS)

    assert aggregator.is_primary(z1) is True
    assert aggregator.is_secondary(z1) is False
    assert aggregator.is_bypassed(z1) is False

    assert aggregator.is_primary(z2) is False
    assert aggregator.is_secondary(z2) is True
    assert aggregator.is_bypassed(z2) is False

    assert aggregator.is_primary(z3) is False
    assert aggregator.is_secondary(z3) is False
    assert aggregator.is_bypassed(z3) is True

    # Update mode
    aggregator.set_zone_mode(z1, ZONE_MODE_SECONDARY)
    assert aggregator.is_secondary(z1) is True

    # Load saved modes
    aggregator.load_saved_modes({z1: ZONE_MODE_PRIMARY, z2: ZONE_MODE_BYPASS})
    assert aggregator.is_primary(z1) is True
    assert aggregator.is_bypassed(z2) is True


def test_external_mode_getter():
    """Test external mode getter (e.g. calendar overrides priority)."""
    overrides = {}

    def get_calendar_mode(cid: str):
        return overrides.get(cid)

    aggregator = DemandAggregator(mode_getter=get_calendar_mode)
    z1 = aggregator.register_zone("Zone1", mode=ZONE_MODE_PRIMARY)

    assert aggregator.get_zone_mode(z1) == ZONE_MODE_PRIMARY

    # Calendar overrides to secondary
    overrides[z1] = ZONE_MODE_SECONDARY
    assert aggregator.get_zone_mode(z1) == ZONE_MODE_SECONDARY
    assert aggregator.is_secondary(z1) is True


def test_weights_management():
    """Test zone weight setting and bulk updating."""
    aggregator = DemandAggregator()
    z1 = aggregator.register_zone("Zone1", weight=25.0)
    z2 = aggregator.register_zone("Zone2")

    assert aggregator.get_zone_weight(z1) == 25.0
    assert aggregator.get_zone_weight(z2) == 1.0

    # Negative weight clamped to 0.0
    aggregator.set_zone_weight(z2, -5.0)
    assert aggregator.get_zone_weight(z2) == 0.0

    # Bulk update
    aggregator.set_zone_weights({z1: 30.0, z2: 40.0})
    assert aggregator.get_zone_weight(z1) == 30.0
    assert aggregator.get_zone_weight(z2) == 40.0


def test_strategy_max_calculation():
    """Test default MAX strategy with Primary, Secondary, and Bypass zones."""
    aggregator = DemandAggregator(strategy=DEMAND_STRATEGY_MAX)

    z_prim1 = aggregator.register_zone("Living", mode=ZONE_MODE_PRIMARY)
    z_prim2 = aggregator.register_zone("Master Bed", mode=ZONE_MODE_PRIMARY)
    z_sec = aggregator.register_zone("Attic", mode=ZONE_MODE_SECONDARY)
    z_byp = aggregator.register_zone("Guest", mode=ZONE_MODE_BYPASS)

    # 1. All at 0%
    result = aggregator.calculate()
    assert result.demand == 0.0
    assert result.peak_zone is None
    assert result.strategy == DEMAND_STRATEGY_MAX
    assert result.active_primary_count == 0
    assert result.active_secondary_count == 0

    # Test tuple unpacking compatibility
    demand, peak_zone = result
    assert demand == 0.0
    assert peak_zone is None

    # 2. Primary demands
    aggregator.set_zone_demand(z_prim1, 40.0)
    aggregator.set_zone_demand(z_prim2, 85.0)
    aggregator.set_zone_demand(z_sec, 95.0)  # Secondary higher than primary!
    aggregator.set_zone_demand(z_byp, 100.0)  # Bypass at 100%

    result = aggregator.calculate()
    # Secondary and Bypass must NOT dictate boiler demand!
    # Max of Primary is Master Bed at 85.0%
    assert result.demand == 85.0
    assert result.peak_zone == "Master Bed"
    assert result.active_primary_count == 2
    assert result.active_secondary_count == 1
    assert result.secondary_demands["Attic"] == 95.0

    # 3. Only Secondary requesting heat
    aggregator.set_zone_demand(z_prim1, 0.0)
    aggregator.set_zone_demand(z_prim2, 0.0)
    result = aggregator.calculate()

    # Generator should remain OFF (demand=0, peak_zone=None)
    assert result.demand == 0.0
    assert result.peak_zone is None
    assert aggregator.has_active_primary_demand() is False
    assert aggregator.has_active_secondary_demand() is True
    assert aggregator.is_secondary_only_active() is True


def test_strategy_weighted_average():
    """Test WEIGHTED_AVERAGE strategy calculation."""
    aggregator = DemandAggregator(strategy=DEMAND_STRATEGY_WEIGHTED_AVERAGE)

    # Zone A: 20 m2, Zone B: 80 m2
    z_a = aggregator.register_zone("Small Room", weight=20.0, mode=ZONE_MODE_PRIMARY)
    z_b = aggregator.register_zone("Large Hall", weight=80.0, mode=ZONE_MODE_PRIMARY)

    aggregator.set_zone_demand(z_a, 50.0)
    aggregator.set_zone_demand(z_b, 100.0)

    result = aggregator.calculate()
    # Weighted average: (50*20 + 100*80) / (20 + 80) = (1000 + 8000) / 100 = 90.0%
    assert result.demand == 90.0
    assert result.peak_zone == "Large Hall"
    assert result.strategy == DEMAND_STRATEGY_WEIGHTED_AVERAGE

    # If only Small Room is active
    aggregator.set_zone_demand(z_b, 0.0)
    result = aggregator.calculate()
    assert result.demand == 50.0
    assert result.peak_zone == "Small Room"

    # All primary at 0%
    aggregator.set_zone_demand(z_a, 0.0)
    result = aggregator.calculate()
    assert result.demand == 0.0
    assert result.peak_zone is None


def test_strategy_sum_capped():
    """Test SUM_CAPPED strategy calculation."""
    aggregator = DemandAggregator(strategy=DEMAND_STRATEGY_SUM_CAPPED)

    z1 = aggregator.register_zone("Room1", mode=ZONE_MODE_PRIMARY)
    z2 = aggregator.register_zone("Room2", mode=ZONE_MODE_PRIMARY)

    # Sum under 100%
    aggregator.set_zone_demand(z1, 20.0)
    aggregator.set_zone_demand(z2, 35.0)
    result = aggregator.calculate()
    assert result.demand == 55.0
    assert result.peak_zone == "Room2"

    # Sum exceeding 100% capped to 100.0%
    aggregator.set_zone_demand(z1, 60.0)
    aggregator.set_zone_demand(z2, 70.0)
    result = aggregator.calculate()
    assert result.demand == 100.0
    assert result.peak_zone == "Room2"


def test_dhw_and_frost_emergency_priorities():
    """Test DHW suppression and Anti-Frost overrides."""
    aggregator = DemandAggregator()
    z1 = aggregator.register_zone("Main", mode=ZONE_MODE_PRIMARY)
    aggregator.set_zone_demand(z1, 80.0)

    # 1. Domestic Hot Water Active -> Immediately forces demand to 0.0%
    result = aggregator.calculate(is_dhw_active=True)
    assert result.demand == 0.0
    assert result.peak_zone is None
    assert result.dhw_active is True

    # 2. Anti-Frost Emergency -> Immediately forces demand to 100.0%
    result = aggregator.calculate(frost_emergency=True)
    assert result.demand == 100.0
    assert result.peak_zone == "Frost Emergency"
    assert result.frost_emergency is True


def test_changing_strategy_dynamically():
    """Test changing aggregation strategy on the fly."""
    aggregator = DemandAggregator(strategy=DEMAND_STRATEGY_MAX)
    z1 = aggregator.register_zone("Z1", weight=2.0)
    z2 = aggregator.register_zone("Z2", weight=8.0)
    aggregator.set_zone_demand(z1, 40.0)
    aggregator.set_zone_demand(z2, 80.0)

    # MAX
    assert aggregator.calculate().demand == 80.0

    # Switch to SUM_CAPPED
    aggregator.strategy = DEMAND_STRATEGY_SUM_CAPPED
    assert aggregator.strategy == DEMAND_STRATEGY_SUM_CAPPED
    assert aggregator.calculate().demand == 100.0  # 40 + 80 = 120 -> capped to 100

    # Switch to WEIGHTED_AVERAGE
    aggregator.strategy = DEMAND_STRATEGY_WEIGHTED_AVERAGE
    # (40*2 + 80*8) / (2+8) = (80 + 640) / 10 = 72.0%
    assert aggregator.calculate().demand == 72.0

    # Invalid strategy raises ValueError
    with pytest.raises(ValueError):
        aggregator.strategy = "non_existent"


def test_calculate_with_explicit_zones_parameter():
    """Test calculate() when explicit zone configurations are passed."""
    aggregator = DemandAggregator()
    z1 = aggregator.register_zone("Zone Alpha")
    z2 = aggregator.register_zone("Zone Beta")
    aggregator.set_zone_demand(z1, 30.0)
    aggregator.set_zone_demand(z2, 70.0)

    # Filter to evaluate only Zone Alpha
    alpha_only = [{CONF_ZONE_NAME: "Zone Alpha"}]
    res = aggregator.calculate(zones=alpha_only)
    assert res.demand == 30.0
    assert res.peak_zone == "Zone Alpha"


def test_empty_aggregator_calculate():
    """Test calculate() when no zones are registered."""
    aggregator = DemandAggregator()
    res = aggregator.calculate()
    assert res.demand == 0.0
    assert res.peak_zone is None
    assert res.active_primary_count == 0
    assert res.active_secondary_count == 0


def test_zero_weights_weighted_average():
    """Test WEIGHTED_AVERAGE when weights sum to zero (graceful fallback)."""
    aggregator = DemandAggregator(strategy=DEMAND_STRATEGY_WEIGHTED_AVERAGE)
    z1 = aggregator.register_zone("Z1", weight=0.0)
    z2 = aggregator.register_zone("Z2", weight=0.0)
    aggregator.set_zone_demand(z1, 40.0)
    aggregator.set_zone_demand(z2, 80.0)

    res = aggregator.calculate()
    assert res.demand == 80.0
    assert res.peak_zone == "Z2"


def test_equal_demands_peak_zone():
    """Test deterministic selection when two zones have the exact same peak demand."""
    aggregator = DemandAggregator()
    z1 = aggregator.register_zone("Z1")
    z2 = aggregator.register_zone("Z2")
    aggregator.set_zone_demand(z1, 50.0)
    aggregator.set_zone_demand(z2, 50.0)

    res = aggregator.calculate()
    assert res.demand == 50.0
    assert res.peak_zone in ("Z1", "Z2")



