"""Unit tests for SmartReturnPlanner."""
from datetime import datetime
from unittest.mock import MagicMock
import pytest

from homeassistant.util import dt as dt_util

from custom_components.multizone_thermostat.const import CONF_ZONE_NAME
from custom_components.multizone_thermostat.schedule.smart_return import SmartReturnPlanner


def test_parse_arrival_time_time_only():
    """Test arrival time string format 'HH:MM'."""
    planner = SmartReturnPlanner(coordinator=MagicMock())
    now = datetime(2026, 11, 7, 10, 0, 0)
    arr = planner.parse_arrival_time("18:30", now)
    assert arr.hour == 18
    assert arr.minute == 30
    assert arr.day == 7


def test_parse_arrival_time_next_day_wrap():
    """Test arrival time string wrap to next day if time has already passed."""
    planner = SmartReturnPlanner(coordinator=MagicMock())
    now = datetime(2026, 11, 7, 20, 0, 0)
    arr = planner.parse_arrival_time("08:00", now)
    assert arr.hour == 8
    assert arr.minute == 0
    assert arr.day == 8


def test_calculate_plan_staggered():
    """Test thermal radar staggered preheating calculation."""
    coord = MagicMock()
    coord.zones = [
        {CONF_ZONE_NAME: "Living", "climate_id": "climate.living"},
        {CONF_ZONE_NAME: "Bedroom", "climate_id": "climate.bedroom"},
    ]
    coord._climate_entities = {
        "climate.living": MagicMock(current_temperature=19.0),
        "climate.bedroom": MagicMock(current_temperature=18.0),
    }
    coord._thermal_models = {
        "climate.living": MagicMock(heating_rate=1.0),   # 1°C per hour -> needs 2.0h to reach 21°C
        "climate.bedroom": MagicMock(heating_rate=0.5),  # 0.5°C per hour -> needs 4.0h to reach 20°C
    }

    def resolve_preset(preset, cid):
        return 21.0 if "living" in cid else 20.0

    planner = SmartReturnPlanner(
        coordinator=coord,
        resolve_preset_temp_fn=resolve_preset,
    )

    now = datetime(2026, 11, 7, 12, 0, 0)
    plan = planner.calculate_plan("18:00", preset="comfort", now=now)

    assert "climate.living" in plan
    assert "climate.bedroom" in plan

    # Living: 21 - 19 = 2°C / 1.0 = 2 hours -> ignition at 16:00
    assert plan["climate.living"]["minutes_needed"] == 120
    assert "16:00:00" in plan["climate.living"]["ignition_time"]

    # Bedroom: 20 - 18 = 2°C / 0.5 = 4 hours -> ignition at 14:00
    assert plan["climate.bedroom"]["minutes_needed"] == 240
    assert "14:00:00" in plan["climate.bedroom"]["ignition_time"]
