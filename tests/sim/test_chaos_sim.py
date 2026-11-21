"""Deterministic chaos simulation & mutation oracle tests inside the repository."""
import pytest

from tests.sim.chaos_engine import ChaosConfig, async_run_chaos_simulation
from tests.sim.thermal_simulator import PlantSimulator, SimulatedRoom


@pytest.mark.asyncio
async def test_chaos_3_day_winter_run_no_violations():
    """Run a 3-day seeded chaos simulation with DHW, cold snap, noise and dropouts."""
    report = await async_run_chaos_simulation(ChaosConfig(seed=20261117, days=3))
    assert report.steps == 3 * 24 * 60
    assert report.dhw_events >= 1
    assert report.ot_boiler_commands > 0
    assert report.distinct_boiler_flow_targets >= 2
    assert report.frozen_dropout_steps >= 1
    assert report.energy_delivered_wh > 0.0
    assert report.violations == []


@pytest.mark.asyncio
async def test_chaos_reproducible_by_seed():
    """Same seed must yield identical simulation metrics."""
    r1 = await async_run_chaos_simulation(ChaosConfig(seed=777, days=1))
    r2 = await async_run_chaos_simulation(ChaosConfig(seed=777, days=1))
    assert r1.dhw_events == r2.dhw_events
    assert r1.sensor_dropouts == r2.sensor_dropouts
    assert r1.setpoint_changes == r2.setpoint_changes
    assert r1.energy_delivered_wh == pytest.approx(r2.energy_delivered_wh)
    assert r1.discomfort_degree_hours == pytest.approx(r2.discomfort_degree_hours)


@pytest.mark.asyncio
async def test_chaos_fahrenheit_full_io_scenario():
    """Full Fahrenheit I/O chaos run validates inbound and outbound temperatures."""
    report = await async_run_chaos_simulation(
        ChaosConfig(seed=1516, days=2, fahrenheit_mode=True)
    )
    assert report.outbound_temp_commands > 0
    assert report.energy_delivered_wh > 0.0
    assert report.violations == []


@pytest.mark.asyncio
async def test_chaos_high_inertia_hysteresis_band_scenario():
    """High thermal inertia (0.8C) must not collapse hysteresis band during learning."""
    report = await async_run_chaos_simulation(
        ChaosConfig(seed=9901, days=2, high_inertia_hysteresis=True)
    )
    assert report.energy_delivered_wh > 0.0
    assert report.violations == []


@pytest.mark.asyncio
async def test_chaos_mid_cycle_ha_restart_scenario():
    """Simulating HA restart mid-heating cycle preserves controller safety."""
    report = await async_run_chaos_simulation(
        ChaosConfig(seed=4242, days=2, mid_cycle_restart_step=720)
    )
    assert report.restart_events == 1
    assert report.restart_verified is True
    assert report.energy_delivered_wh > 0.0
    assert report.violations == []


@pytest.mark.asyncio
async def test_chaos_oracle_mutation_catches_bad_demand_and_raw_celsius_in_f_mode():
    """Mutation test: verify chaos oracles detect bad demand, raw C in F (zone & boiler), and overheat."""
    r_dem = await async_run_chaos_simulation(
        ChaosConfig(seed=101, days=1, inject_fault_mode="bad_demand")
    )
    assert any("demand out of bounds" in v for v in r_dem.violations)

    r_f = await async_run_chaos_simulation(
        ChaosConfig(seed=101, days=1, fahrenheit_mode=True, inject_fault_mode="raw_celsius_in_f")
    )
    assert any("raw Celsius value" in v for v in r_f.violations)

    r_boiler_f = await async_run_chaos_simulation(
        ChaosConfig(seed=101, days=1, fahrenheit_mode=True, inject_fault_mode="raw_celsius_boiler_in_f")
    )
    assert any("out-of-range boiler value" in v for v in r_boiler_f.violations)

    r_overheat = await async_run_chaos_simulation(
        ChaosConfig(seed=101, days=1, inject_fault_mode="overheat_runaway")
    )
    assert any("overheated room temp" in v for v in r_overheat.violations)


def test_thermal_simulator_residual_radiator_inertia_and_overshoot_penalty():
    """Radiator water decay continues releasing residual heat after boiler off and overshoot increases discomfort."""
    sim = PlantSimulator(
        rooms=[SimulatedRoom(name="Test", current_temp=20.0, target_temp=20.0)],
        t_out=5.0,
    )
    sim.boiler.ch_enabled = True
    sim.boiler.target_flow_temp = 60.0
    sim.step(dt_seconds=1200.0)
    assert sim.boiler.current_flow_temp > 50.0

    # Shut off boiler -> residual hot water remains well above outdoor temp on subsequent step
    sim.boiler.ch_enabled = False
    sim.step(dt_seconds=60.0)
    assert sim.last_effective_flow > sim.t_out + 10.0

    # Verify overshoot penalty and > 0.5 C deadband discomfort
    room = SimulatedRoom(name="Warm", current_temp=22.0, target_temp=20.0, valve_pct=0.0)
    room.step(dt_hours=1.0, t_flow=20.0, t_out=22.0)
    assert room.overshoot_degree_hours == pytest.approx(2.0)
    assert room.discomfort_degree_hours == pytest.approx(1.5)
