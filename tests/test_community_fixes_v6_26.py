"""Regression tests for community-reported issues (#62, #64) and competitor-inspired improvements (master)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.multizone_thermostat.autotune import PassiveAutotuneObserver
from custom_components.multizone_thermostat.const import (
    CONF_ZONES,
    CONF_ZONE_NAME,
    CONF_ZONE_TEMP_SENSOR,
    CONF_ZONE_WINDOW_SENSOR,
    DOMAIN,
    ZONE_MODE_BYPASS,
    ZONE_MODE_PRIMARY,
    make_zone_entity_id,
)
from custom_components.multizone_thermostat.coordinator import MultizoneCoordinator
from custom_components.multizone_thermostat.pwm_engine import PWMEngine
from custom_components.multizone_thermostat.sensor import AutotuneSensor, DemandSensor
from custom_components.multizone_thermostat.thermal_model import ThermalObserver
from custom_components.multizone_thermostat.zone_controller import ZoneController


def _complete_cycles(tuner: PassiveAutotuneObserver, base_wall: float = 1_700_000_000.0) -> None:
    for idx in range(tuner.required_cycles):
        t0 = base_wall + idx * 7200.0
        tuner.update(18.0, True, now=t0)
        for step in range(1, 12):
            t = t0 + step * 60.0
            temp = 18.0 if step <= 2 else 18.0 + (step - 2) * 0.2
            tuner.update(temp, True, now=t)
        tuner.update(20.5, False, now=t0 + 720.0)
    assert tuner.state == tuner.STATE_COMPLETED


def _make_zone_controller(window_open_sensor: bool = False, pre_window_bypass: bool = False):
    hass = MagicMock()
    ws_state = "on" if window_open_sensor else "off"
    hass.states = MagicMock()
    hass.states.get.side_effect = lambda eid: (
        SimpleNamespace(state=ws_state, attributes={})
        if eid == "binary_sensor.living_window"
        else None
    )
    entry = MagicMock()
    entry.entry_id = "community_fixes_entry"
    entry.version = 1
    entry.domain = DOMAIN
    entry.title = "Community Fixes Test"
    entry.data = {
        CONF_ZONES: [
            {
                CONF_ZONE_NAME: "Living",
                CONF_ZONE_TEMP_SENSOR: "sensor.living_temp",
                CONF_ZONE_WINDOW_SENSOR: "binary_sensor.living_window",
            }
        ]
    }
    entry.options = {}
    coord = MultizoneCoordinator(hass, entry)
    coord.storage = MagicMock()
    coord.storage.async_save_autotuner_states = AsyncMock()
    coord.storage.async_save_thermal_states = AsyncMock()
    coord.debounced_save_thermal_states = MagicMock()
    coord.async_notify_pid_entities = MagicMock()
    cid = make_zone_entity_id("Living")
    if pre_window_bypass:
        coord.zone_manager._pre_window_state[cid] = ZONE_MODE_PRIMARY
        coord.zone_manager._zone_modes[cid] = ZONE_MODE_BYPASS
    zc = ZoneController(hass, coord)
    coord.zone_controller = zc
    return hass, entry, coord, zc, cid


# ---------------------------------------------------------------------------
# 1. ThermalObserver anti-jitter, quiet cooling window & self-healing
# ---------------------------------------------------------------------------


def test_thermal_observer_rejects_jitter_and_open_window_learns_quiet_cooling():
    t = [1000.0]
    with patch("time.monotonic", side_effect=lambda: t[0]):
        obs = ThermalObserver("climate.living")
        obs.update(21.0, is_heating=False)

        # Short 0.1 C tick at +60s (AlainGH jitter scenario): must NOT update cooling_rate
        t[0] = 1060.0
        obs.update(20.9, is_heating=False)
        assert obs.cooling_rate == 0.0

        # Still under 30 min at +600s: must NOT update
        t[0] = 1600.0
        obs.update(20.85, is_heating=False)
        assert obs.cooling_rate == 0.0

        # At +1800s (0.5h), cumulative drop is 0.25 C -> staged as pending sample (not committed yet)
        t[0] = 2800.0
        obs.update(20.75, is_heating=False)
        assert obs.cooling_rate == 0.0

        # After 10 min confirmation (+600s) with no wall thermal rebound -> committed cleanly via OLS
        t[0] = 3400.0
        obs.update(20.68, is_heating=False)
        assert 0.35 <= obs.cooling_rate <= 0.55
        prev_rate = obs.cooling_rate

        # Implausible spike (> 2.0 C/hr, e.g., unmonitored window opened): discarded and triggers lockout
        t[0] = 3800.0
        obs.update(19.5, is_heating=False)
        assert obs.cooling_rate == pytest.approx(prev_rate, rel=1e-3)
        assert obs.is_draft_lockout_active is True

        # Monitored open window: resets baseline without erasing learned cooling_rate
        t[0] = 4000.0
        obs.update(17.0, is_heating=False, window_open=True)
        assert obs._last_temp is None
        assert obs.cooling_rate == pytest.approx(prev_rate, rel=1e-3)


def test_thermal_observer_sensorless_wall_rebound_discards_window_drop():
    t = [1000.0]
    with patch("time.monotonic", side_effect=lambda: t[0]):
        obs = ThermalObserver("climate.living")
        obs.update(21.0, is_heating=False)

        # Room drops 0.30 C over 30 min (0.60 C/hr -> below 2.0 cap, e.g. mild open window)
        t[0] = 2800.0
        obs.update(20.70, is_heating=False)
        assert obs.cooling_rate == 0.0

        # Window closes -> warm walls rebound air temperature by +0.15 C within 5 min
        t[0] = 3100.0
        obs.update(20.85, is_heating=False)
        assert obs.cooling_rate == 0.0
        assert obs._pending_cooling_sample is None
        assert obs.is_draft_lockout_active is True


def test_thermal_observer_sensorless_fast_draft_triggers_lockout():
    t = [1000.0]
    with patch("time.monotonic", side_effect=lambda: t[0]):
        obs = ThermalObserver("climate.living")
        obs.update(21.0, is_heating=False)

        # Sudden 0.50 C drop in 5 min (6.0 C/hr) triggers 40-min fast draft lockout
        t[0] = 1300.0
        obs.update(20.50, is_heating=False)
        assert obs.cooling_rate == 0.0
        assert obs.is_draft_lockout_active is True

        # During 40-min lockout, cooling drops are ignored
        t[0] = 3500.0  # still < 1300 + 2400 = 3700
        obs.update(20.00, is_heating=False)
        assert obs.cooling_rate == 0.0

        # After lockout expires (t=3700), 30-min+ drop (from t=3500 baseline -> 2100s) + 10-min confirm learns cleanly
        t[0] = 3800.0
        obs.update(20.00, is_heating=False)
        t[0] = 5600.0
        obs.update(19.75, is_heating=False)
        t[0] = 6200.0
        obs.update(19.68, is_heating=False)
        assert obs.cooling_rate == pytest.approx(0.25 / (2100.0 / 3600.0), rel=1e-3)


def test_thermal_observer_asymmetric_outlier_rejection_and_sample_persistence():
    t = [1000.0]
    with patch("time.monotonic", side_effect=lambda: t[0]):
        obs = ThermalObserver("climate.living")
        obs.update(21.0, is_heating=False)

        # Record 3 clean quiet samples: 0.25, 0.28, 0.24 C/hr
        cur_t = 21.0
        for rate in (0.25, 0.28, 0.24):
            drop = rate * 1.0  # 1h window
            t[0] += 3600.0
            cur_t -= drop
            obs.update(cur_t, is_heating=False)
            t[0] += 600.0
            cur_t -= 0.02
            obs.update(cur_t, is_heating=False)

        assert len(obs._cooling_samples) == 3
        rate_before_outlier = obs.cooling_rate

        # Persist and reload samples across restart
        dumped = obs.dump_state()
        assert len(dumped["cooling_samples"]) == 3
        reloaded = ThermalObserver("climate.living")
        reloaded.load_state(dumped)
        assert len(reloaded._cooling_samples) == 3
        reloaded.update(cur_t, is_heating=False)

        # Tilted window causes 1.4 C/hr drop (< 2.0 hard cap, > 2.5x median ~0.25) -> rejected!
        t[0] += 1800.0
        cur_t -= 0.70
        reloaded.update(cur_t, is_heating=False)
        t[0] += 600.0
        cur_t -= 0.02
        reloaded.update(cur_t, is_heating=False)
        assert len(reloaded._cooling_samples) == 3
        assert reloaded.cooling_rate == pytest.approx(rate_before_outlier)


def test_thermal_observer_post_shutdown_inertia_excluded_and_storage_sanitized():
    t = [1000.0]
    with patch("time.monotonic", side_effect=lambda: t[0]):
        obs = ThermalObserver("climate.living")
        obs.update(20.0, is_heating=True, demand=90.0)
        t[0] = 1600.0
        obs.update(20.5, is_heating=True, demand=90.0)

        # Shutdown -> inertia tracking starts
        t[0] = 1700.0
        obs.update(20.5, is_heating=False, demand=0.0)
        t[0] = 2000.0
        obs.update(20.8, is_heating=False, demand=0.0)  # peak +0.3 C
        # Still inside inertia window, cooling_rate must stay 0.0
        assert obs.cooling_rate == 0.0
        assert obs.last_inertia_event_id == 0

        # Drops 0.1 C from peak -> inertia event finalized, baseline reset
        t[0] = 2900.0
        obs.update(20.65, is_heating=False, demand=0.0)
        assert obs.last_inertia_event_id == 1
        assert obs.last_inertia_sample == pytest.approx(0.3, rel=1e-3)
        assert obs.cooling_rate == 0.0

    # Legacy corrupted cooling_rate (e.g. 8.5 C/hr = 0.12 h per 1 C) self-heals on load_state
    obs2 = ThermalObserver("climate.living")
    obs2.load_state({"heating_rate": 1.2, "cooling_rate": 8.5, "thermal_inertia": 0.2})
    assert obs2.heating_rate == pytest.approx(1.2)
    assert obs2.cooling_rate == 0.0
    assert obs2.thermal_inertia == pytest.approx(0.2)


@pytest.mark.asyncio
async def test_zone_controller_blocks_thermal_cooling_when_window_open():
    t = [1000.0]
    with patch("time.monotonic", side_effect=lambda: t[0]):
        hass, entry, coord, zc, cid = _make_zone_controller(window_open_sensor=False)
        st1 = SimpleNamespace(state="off", attributes={"current_temperature": 21.0, "temperature": 20.0})
        await zc.async_update_zone(cid, st1)

        # Window opens -> ZoneController must pass window_open=True and prevent cooling update
        hass.states.get.side_effect = lambda eid: (
            SimpleNamespace(state="on", attributes={})
            if eid == "binary_sensor.living_window"
            else None
        )
        t[0] = 2800.0
        st2 = SimpleNamespace(state="off", attributes={"current_temperature": 19.5, "temperature": 20.0})
        await zc.async_update_zone(cid, st2)
        assert zc.get_thermal_model(cid).cooling_rate == 0.0
        assert zc.get_zone_demand_attributes(cid)["window_open"] is True


# ---------------------------------------------------------------------------
# 2. PWMEngine anti-chattering & continuous-ON threshold
# ---------------------------------------------------------------------------


def test_pwm_engine_no_intra_cycle_double_switch_and_continuous_on():
    t = [1000.0]
    with patch("time.monotonic", side_effect=lambda: t[0]):
        pwm = PWMEngine(pwm_interval=900.0, min_on=300.0, min_off=300.0)

        # Continuous ON at >= 95% (prevents forced 5-min off pulse when rooms demand 96%)
        assert pwm.calculate(96.0) is True
        t[0] = 2500.0
        assert pwm.calculate(96.0) is True

        # Start fresh moderate cycle at 60% (time_on = 540s, time_off = 360s)
        pwm2 = PWMEngine(pwm_interval=900.0, min_on=180.0, min_off=180.0)
        t[0] = 3000.0
        assert pwm2.calculate(60.0) is True

        # At +360s, demand dips to 30% (time_on=270s < 360s) -> transitions to OFF phase
        t[0] = 3360.0
        assert pwm2.calculate(30.0) is False

        # 60s later (+420s), demand rises back to 80%: MUST NOT re-ignite inside the same cycle!
        t[0] = 3420.0
        assert pwm2.calculate(80.0) is False

        # Once current cycle finishes, fresh cycle starts cleanly
        t[0] = 3905.0
        assert pwm2.calculate(80.0) is True


# ---------------------------------------------------------------------------
# 3. DemandSensor live PID component breakdown attributes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_demand_sensor_exposes_live_pid_breakdown_attributes():
    t = [1000.0]
    with patch("time.monotonic", side_effect=lambda: t[0]):
        hass, entry, coord, zc, cid = _make_zone_controller()
        zc.get_autotuner(cid).seed_learned_pid(kp=50.0, ki=0.2, kd=0.0)
        zc._apply_tuner_pid_to_controller(cid)

        st1 = SimpleNamespace(state="heat", attributes={"current_temperature": 19.5, "temperature": 20.0})
        await zc.async_update_zone(cid, st1)

        t[0] = 1060.0
        st2 = SimpleNamespace(state="heat", attributes={"current_temperature": 19.5, "temperature": 20.0})
        demand = await zc.async_update_zone(cid, st2)
        assert demand > 0.0

        sensor = DemandSensor(hass, entry.entry_id, "Living", cid, coord)
        attrs = sensor.extra_state_attributes
        assert attrs["control_mode"] == "smart_pid"
        assert attrs["p_term"] == pytest.approx(25.0)
        assert attrs["i_term"] == pytest.approx(6.0)
        assert attrs["d_term"] == pytest.approx(0.0)
        assert attrs["error"] == pytest.approx(0.5)
        assert attrs["set_point"] == pytest.approx(20.0)
        assert attrs["raw_output"] == pytest.approx(31.0)
        assert attrs["clamped_output"] == pytest.approx(31.0)
        assert attrs["kp"] == pytest.approx(50.0)
        assert attrs["window_open"] is False


# ---------------------------------------------------------------------------
# 4. Weekly EMA Guardrail & Auto-Rollback
# ---------------------------------------------------------------------------


def test_weekly_ema_guardrail_reverts_on_degradation_and_confirms_when_stable():
    t0 = 1_700_000_000.0
    tuner = PassiveAutotuneObserver("climate.living", required_cycles=3)
    _complete_cycles(tuner, base_wall=t0)
    kp0, ki0, kd0 = tuner.kp, tuner.ki, tuner.kd

    # Record good baseline overshoots (~0.10 C)
    assert tuner.record_overshoot(0.10) is False
    assert tuner.record_overshoot(0.12) is False

    # Feed 3 weekly ramps and cross 7 days -> weekly EMA applies + monitoring begins
    for day_idx in range(1, 4):
        ramp_t = t0 + day_idx * 86400.0
        tuner.update(18.0, True, now=ramp_t, demand=92.0, cooling_rate=0.4)
        for s in range(1, 10):
            tuner.update(18.0 + s * 0.15, True, now=ramp_t + s * 60.0, demand=92.0, cooling_rate=0.4)
        tuner.update(19.5, True, now=ramp_t + 600.0, demand=30.0, cooling_rate=0.4)

    week_later = tuner.last_weekly_update + 7 * 86400.0 + 60.0
    tuner.update(20.0, False, now=week_later, demand=0.0, cooling_rate=0.4)
    assert tuner.weekly_updated_last_tick is True
    assert tuner.last_weekly_guardrail_status == "monitoring"
    assert (tuner.kp, tuner.ki, tuner.kd) != (kp0, ki0, kd0)

    # Persist & reload pending check cleanly
    saved = tuner.dump_state()
    reloaded = PassiveAutotuneObserver("climate.living", required_cycles=3)
    reloaded.load_state(saved)
    assert reloaded.last_weekly_guardrail_status == "monitoring"

    # Two degraded overshoots (0.55 C, 0.65 C -> mean 0.60 C vs baseline 0.11 C) -> AUTO-REVERT!
    assert reloaded.record_overshoot(0.55) is False
    assert reloaded.record_overshoot(0.65) is True
    assert reloaded.last_weekly_guardrail_status == "reverted"
    assert reloaded.weekly_updated_last_tick is True
    assert reloaded.kp == pytest.approx(kp0)
    assert reloaded.ki == pytest.approx(ki0)
    assert reloaded.kd == pytest.approx(kd0)

    # Second scenario: stable overshoots confirm the update
    tuner2 = PassiveAutotuneObserver("climate.living2", required_cycles=3)
    _complete_cycles(tuner2, base_wall=t0)
    tuner2.record_overshoot(0.15)
    for day_idx in range(1, 4):
        ramp_t = t0 + day_idx * 86400.0
        tuner2.update(18.0, True, now=ramp_t, demand=92.0, cooling_rate=0.4)
        for s in range(1, 10):
            tuner2.update(18.0 + s * 0.15, True, now=ramp_t + s * 60.0, demand=92.0, cooling_rate=0.4)
        tuner2.update(19.5, True, now=ramp_t + 600.0, demand=30.0, cooling_rate=0.4)
    tuner2.update(20.0, False, now=tuner2.last_weekly_update + 7 * 86400.0 + 60.0, demand=0.0, cooling_rate=0.4)
    assert tuner2.record_overshoot(0.14) is False
    assert tuner2.record_overshoot(0.16) is False
    assert tuner2.last_weekly_guardrail_status == "confirmed"

    # Manual override cancels pending guardrail check
    tuner2._pending_weekly_check = {"pre_kp": 10.0, "pre_ki": 0.01, "pre_kd": 100.0, "baseline_overshoot": 0.1, "post_overshoots": [], "applied_at": t0}
    tuner2.set_manual_pid(kp=42.0)
    assert tuner2.last_weekly_guardrail_status == "cancelled_manual"
    assert tuner2._pending_weekly_check is None


def test_autotune_sensor_exposes_guardrail_status():
    hass, entry, coord, zc, cid = _make_zone_controller()
    zc.get_autotuner(cid).last_weekly_guardrail_status = "monitoring"
    sensor = AutotuneSensor(hass, entry.entry_id, "Living", cid, coord)
    assert sensor.extra_state_attributes["weekly_guardrail_status"] == "monitoring"
