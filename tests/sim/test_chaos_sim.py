"""Deterministic chaos simulation & mutation oracle tests inside the repository."""
import pytest

from tests.sim.chaos_engine import ChaosConfig, async_run_chaos_simulation


@pytest.mark.asyncio
async def test_chaos_3_day_winter_run_no_violations():
    """Run a 3-day seeded chaos simulation with DHW, cold snap, noise and dropouts."""
    report = await async_run_chaos_simulation(ChaosConfig(seed=20261117, days=3))
    assert report.steps == 3 * 24 * 60
    assert report.dhw_events >= 1
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
    assert report.energy_delivered_wh > 0.0
    assert report.violations == []


@pytest.mark.asyncio
async def test_chaos_oracle_mutation_catches_bad_demand_and_raw_celsius_in_f_mode():
    """Mutation test: verify chaos oracles detect out-of-bounds demand and raw C in F mode."""
    r_dem = await async_run_chaos_simulation(
        ChaosConfig(seed=101, days=1, inject_fault_mode="bad_demand")
    )
    assert any("demand out of bounds" in v for v in r_dem.violations)

    r_f = await async_run_chaos_simulation(
        ChaosConfig(seed=101, days=1, fahrenheit_mode=True, inject_fault_mode="raw_celsius_in_f")
    )
    assert any("raw Celsius value" in v for v in r_f.violations)
