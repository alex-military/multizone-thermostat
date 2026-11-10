"""Unit tests for the unified FlowCurve and multi-emitter presets."""
import pytest
from custom_components.multizone_thermostat.boiler.flow_curve import (
    FlowCurve,
    create_flow_curve_for_emitter,
    EMITTER_RADIATOR,
    EMITTER_UNDERFLOOR,
    EMITTER_FANCOIL,
)


def test_radiator_flow_curve():
    """Verify radiator flow curve uses exponent 1.3 and respects limits."""
    curve = create_flow_curve_for_emitter(EMITTER_RADIATOR, t_min=35.0, t_max=70.0)
    assert curve.exponent == 1.3
    assert curve.t_min == 35.0
    assert curve.t_max == 70.0

    # Mild weather (10°C): ceiling should be bounded around 47°C, never 70°C
    c10 = curve.ceiling(10.0)
    assert 40.0 < c10 < 52.0

    # Cold design day (-5°C): ceiling reaches t_max
    assert curve.ceiling(-5.0) == 70.0

    # Flow at demand 0% is t_min
    assert curve.flow_for_demand(0.0, 10.0) == 35.0

    # Flow at demand 100% is ceiling
    assert curve.flow_for_demand(100.0, 10.0) == round(c10, 1)


def test_underfloor_flow_curve_and_safety():
    """Verify underfloor curve limits and mixed-plant safety cap."""
    # Dedicated underfloor
    uf_curve = create_flow_curve_for_emitter(EMITTER_UNDERFLOOR)
    assert uf_curve.exponent == 1.1
    assert uf_curve.t_min == 25.0
    assert uf_curve.t_max == 40.0
    assert uf_curve.ceiling(-10.0) == 40.0

    # Mixed underfloor + radiators WITHOUT mixing valve: must clamp t_max to 40°C
    mixed_no_valve = create_flow_curve_for_emitter(
        EMITTER_RADIATOR,
        t_max=70.0,
        has_mixing_valve=False,
        is_mixed_underfloor=True,
    )
    assert mixed_no_valve.t_max <= 40.0

    # Mixed underfloor + radiators WITH mixing valve: generator can go up to 70°C
    mixed_with_valve = create_flow_curve_for_emitter(
        EMITTER_RADIATOR,
        t_max=70.0,
        has_mixing_valve=True,
        is_mixed_underfloor=True,
    )
    assert mixed_with_valve.t_max == 70.0


def test_fancoil_flow_curve():
    """Verify fancoil curve uses linear exponent and comfortable min temp."""
    fc_curve = create_flow_curve_for_emitter(EMITTER_FANCOIL)
    assert fc_curve.exponent == 1.0
    assert fc_curve.t_min == 42.0
    assert fc_curve.t_max == 55.0
    assert fc_curve.flow_for_demand(0.0, 5.0) == 42.0
