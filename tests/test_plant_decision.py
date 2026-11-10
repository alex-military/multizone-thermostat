"""Unit tests for deterministic heating plant arbitration (decide_heating)."""
import pytest
from custom_components.multizone_thermostat.boiler.plant_decision import (
    PlantInputs,
    decide_heating,
    AUTO,
    HYBRID,
    COMBINED,
    GAS_ONLY,
    ELECTRIC_ONLY,
    GAS_PRIORITY,
    ELECTRIC_PRIORITY,
)


def _inp(**kwargs) -> PlantInputs:
    base = dict(
        demand=50.0,
        priority=AUTO,
        gas_enabled=True,
        hp_enabled=True,
        hp_available=True,
        solar_surplus=False,
        max_zone_delta=0.0,
        frost_emergency=False,
    )
    base.update(kwargs)
    return PlantInputs(**base)


def test_frost_emergency_overrides_any_priority():
    """Verify frost emergency activates any available generator regardless of priority."""
    # With electric_only, gas is still turned on for frost emergency
    cmd = decide_heating(_inp(priority=ELECTRIC_ONLY, frost_emergency=True, demand=80.0))
    assert cmd.gas_demand == 80.0
    assert cmd.hp_demand == 80.0
    assert "FROST" in cmd.reason

    # With gas_only, HP is still turned on if available for frost protection
    cmd2 = decide_heating(_inp(priority=GAS_ONLY, frost_emergency=True, demand=100.0))
    assert cmd2.gas_demand == 100.0
    assert cmd2.hp_demand == 100.0


def test_electric_priority_fallback_on_hp_failure():
    """Verify electric_priority uses HP when available, but falls back to gas if HP fails."""
    # Healthy HP
    cmd_ok = decide_heating(_inp(priority=ELECTRIC_PRIORITY, hp_available=True, demand=60.0))
    assert cmd_ok.hp_demand == 60.0
    assert cmd_ok.gas_demand == 0.0

    # Failed / unavailable HP: gas must pick up the load
    cmd_fail = decide_heating(_inp(priority=ELECTRIC_PRIORITY, hp_available=False, demand=60.0))
    assert cmd_fail.hp_demand == 0.0
    assert cmd_fail.gas_demand == 60.0
    assert cmd_fail.reason == "GAS_ONLY_NO_HP"


def test_gas_priority_pure():
    """Verify gas_priority never activates HP even during solar surplus (Option 1)."""
    cmd = decide_heating(_inp(priority=GAS_PRIORITY, solar_surplus=True, demand=45.0))
    assert cmd.gas_demand == 45.0
    assert cmd.hp_demand == 0.0
    assert cmd.reason == "GAS_PRIORITY"


def test_combined_mode_boost():
    """Verify combined mode runs gas as baseline and HP as boost when delta >= 1.5°C."""
    # Low delta, no solar: gas only
    cmd_base = decide_heating(_inp(priority=COMBINED, max_zone_delta=0.8, solar_surplus=False, demand=50.0))
    assert cmd_base.gas_demand == 50.0
    assert cmd_base.hp_demand == 0.0

    # High delta (2.0°C): both active
    cmd_boost = decide_heating(_inp(priority=COMBINED, max_zone_delta=2.0, demand=50.0))
    assert cmd_boost.gas_demand == 50.0
    assert cmd_boost.hp_demand == 50.0
    assert cmd_boost.reason == "COMBINED_ASSIST"


def test_auto_solar_surplus():
    """Verify AUTO uses HP during solar surplus and Gas otherwise."""
    cmd_normal = decide_heating(_inp(priority=AUTO, solar_surplus=False, demand=30.0))
    assert cmd_normal.gas_demand == 30.0
    assert cmd_normal.hp_demand == 0.0

    cmd_solar = decide_heating(_inp(priority=AUTO, solar_surplus=True, demand=30.0))
    assert cmd_solar.gas_demand == 0.0
    assert cmd_solar.hp_demand == 30.0
