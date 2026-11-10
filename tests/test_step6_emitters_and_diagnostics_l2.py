"""Unit tests for Emitter Type PWM adaptation and Isolated Plant Diagnostics (L2)."""
import time
from unittest.mock import MagicMock
import pytest

from custom_components.multizone_thermostat.const import (
    CONF_ZONE_EMITTER_TYPE,
    EMITTER_TYPE_RADIATOR,
    EMITTER_TYPE_UNDERFLOOR,
    EMITTER_TYPE_FANCOIL,
    CONF_HAS_MIXING_VALVE,
)
from custom_components.multizone_thermostat.sync_manager import (
    ZoneSyncManager,
    EMITTER_PWM_INTERVALS,
)
from custom_components.multizone_thermostat.plant_diagnostics.engine import (
    PlantDiagnosticsEngine,
)


def test_emitter_pwm_adaptation():
    """Verify ZoneSyncManager adapts PWM interval based on emitter_type."""
    coord = MagicMock()
    coord._min_cycle_on = 3
    coord._min_cycle_off = 3

    # 1. Radiators -> 900.0s (15m)
    sm_rad = ZoneSyncManager(
        hass=MagicMock(),
        coordinator=coord,
        zone_name="Living",
        entity_id="climate.multizone_living",
        climates=[],
        switches=[],
        calibrations={},
        emitter_type=EMITTER_TYPE_RADIATOR,
    )
    assert sm_rad._local_pwm.pwm_interval == 900.0

    # 2. Underfloor -> 1800.0s (30m)
    sm_floor = ZoneSyncManager(
        hass=MagicMock(),
        coordinator=coord,
        zone_name="Bath",
        entity_id="climate.multizone_bath",
        climates=[],
        switches=[],
        calibrations={},
        emitter_type=EMITTER_TYPE_UNDERFLOOR,
    )
    assert sm_floor._local_pwm.pwm_interval == 1800.0

    # 3. Fancoil -> 600.0s (10m)
    sm_fan = ZoneSyncManager(
        hass=MagicMock(),
        coordinator=coord,
        zone_name="Attic",
        entity_id="climate.multizone_attic",
        climates=[],
        switches=[],
        calibrations={},
        emitter_type=EMITTER_TYPE_FANCOIL,
    )
    assert sm_fan._local_pwm.pwm_interval == 600.0


def test_diagnostics_l2_generator_isolation():
    """Verify L2 fix: heat pump going idle does not close gas boiler running interval."""
    coord = MagicMock()
    coord.zones = []
    coord.get_master_state.return_value = True

    diag = PlantDiagnosticsEngine(coordinator=coord)

    # 1. Initially both idle
    assert not diag.is_any_generator_running()
    assert diag.get_boiler_cycles_per_hour("gas") == 0
    assert diag.get_boiler_cycles_per_hour("heat_pump") == 0

    # 2. Turn ON gas boiler
    diag.record_generator_state("gas", True)
    assert diag.is_any_generator_running()
    assert diag._current_generator_start.get("gas") is not None
    assert diag.get_boiler_cycles_per_hour("gas") == 1
    gas_start = diag._current_generator_start["gas"]

    # 3. Heat pump turns ON concurrently
    diag.record_generator_state("heat_pump", True)
    assert diag.is_any_generator_running()
    assert diag._current_generator_start.get("heat_pump") is not None
    assert diag.get_boiler_cycles_per_hour("heat_pump") == 1

    # 4. Heat pump goes OFF (e.g. demand drops or priority shifts)
    # CRITICAL L2 TEST: turning off heat_pump MUST NOT close the gas boiler run interval!
    diag.record_generator_state("heat_pump", False)
    assert diag._current_generator_start.get("heat_pump") is None
    # Gas must still be active with the exact same start timestamp!
    assert diag._current_generator_start.get("gas") == gas_start
    assert diag.is_any_generator_running()
    assert len(diag._generator_run_intervals.get("heat_pump", [])) == 1
    assert len(diag._generator_run_intervals.get("gas", [])) == 0

    # 5. Gas boiler turns OFF
    diag.record_generator_state("gas", False)
    assert diag._current_generator_start.get("gas") is None
    assert not diag.is_any_generator_running()
    assert len(diag._generator_run_intervals.get("gas", [])) == 1


def test_diagnostics_backward_compatibility():
    """Verify legacy record_boiler_state and _current_boiler_start work as expected."""
    coord = MagicMock()
    coord.zones = []
    diag = PlantDiagnosticsEngine(coordinator=coord)

    diag.record_boiler_state(True)
    assert diag._current_boiler_start is not None
    assert diag.get_boiler_cycles_per_hour() == 1

    diag.record_boiler_state(False)
    assert diag._current_boiler_start is None
    assert len(diag._boiler_run_intervals) == 1
