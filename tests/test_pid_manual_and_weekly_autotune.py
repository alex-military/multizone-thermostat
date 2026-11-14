"""Tests for PID manual control entities, Master Demand fix, and Weekly EMA autotuner."""
from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

# Clear any mock entries injected by earlier test modules
sys.meta_path[:] = [
    f for f in sys.meta_path if f.__class__.__name__ != "HomeAssistantMockFinder"
]
for _mod_name in (
    "homeassistant.components.select",
    "homeassistant.components.number",
    "homeassistant.components.switch",
    "homeassistant.components.button",
    "homeassistant.components.sensor",
    "homeassistant.helpers.restore_state",
    "homeassistant.helpers.entity",
):
    if _mod_name in sys.modules and isinstance(sys.modules[_mod_name], MagicMock):
        del sys.modules[_mod_name]

from custom_components.multizone_thermostat import async_setup_entry
from custom_components.multizone_thermostat.autotune import PassiveAutotuneObserver
from custom_components.multizone_thermostat.boiler.plant_orchestrator import PlantOrchestrator
from custom_components.multizone_thermostat.button import MultizoneResetAutotuneButton
from custom_components.multizone_thermostat.const import (
    CONF_BOILER_MODE,
    CONF_ZONE_NAME,
    CONF_ZONE_TEMP_SENSOR,
    CONF_ZONES,
    DOMAIN,
    MODE_CENTRAL,
    make_zone_entity_id,
)
from custom_components.multizone_thermostat.coordinator import MultizoneCoordinator
from custom_components.multizone_thermostat.number import MultizoneZonePIDNumber
from custom_components.multizone_thermostat.sensor import AutotuneSensor, MultizoneMasterDemandSensor
from custom_components.multizone_thermostat.switch import MultizonePIDManualUnlockSwitch
from custom_components.multizone_thermostat.thermal_model import ThermalObserver


class _FakeServices:
    def __init__(self) -> None:
        self.handlers = {}
        self.calls = []

    def async_register(self, domain, service, handler) -> None:
        self.handlers[(domain, service)] = handler

    async def async_call(self, domain, service, data=None, blocking=False) -> None:
        self.calls.append((domain, service, data or {}, blocking))
        handler = self.handlers.get((domain, service))
        if handler is not None:
            await handler(SimpleNamespace(data=data or {}))


class _FakeStates:
    def __init__(self, initial=None) -> None:
        self._states = dict(initial or {})

    def get(self, entity_id):
        return self._states.get(entity_id)

    def set(self, entity_id, state_obj):
        self._states[entity_id] = state_obj


def _make_fake_hass(states=None):
    hass = MagicMock()
    hass.data = {}
    hass.is_running = True
    hass.states = _FakeStates(states)
    hass.services = _FakeServices()
    hass.config = MagicMock()
    hass.config.path = lambda *parts: str(Path.cwd() / Path(*parts))
    hass.config.components = set()
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.async_create_task = lambda coro: asyncio.ensure_future(coro)
    hass.async_add_executor_job = AsyncMock(side_effect=lambda fn, *a: fn(*a))
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()
    return hass


def _make_entry(zones=None, entry_id="test_entry_pid"):
    if zones is None:
        zones = [
            {
                CONF_ZONE_NAME: "Soggiorno",
                CONF_ZONE_TEMP_SENSOR: "sensor.temp_soggiorno",
                "target_temp": 21.0,
            }
        ]
    return SimpleNamespace(
        entry_id=entry_id,
        data={CONF_BOILER_MODE: MODE_CENTRAL, CONF_ZONES: zones},
        options={},
        add_update_listener=lambda fn: (lambda: None),
        async_on_unload=lambda fn: None,
    )


def _complete_initial_cycles(tuner: PassiveAutotuneObserver, base_wall: float = 1_700_000_000.0) -> None:
    """Drive 3 synthetic heating cycles on mono/wall time until STATE_COMPLETED."""
    for idx in range(3):
        t0 = base_wall + idx * 3600.0
        tuner.update(19.0, True, now=t0)
        for step in range(1, 10):
            t = t0 + step * 60.0
            temp = 19.0 if step <= 2 else 19.0 + (step - 2) * 0.22
            tuner.update(temp, True, now=t)
        tuner.update(20.6, False, now=t0 + 600.0)
    assert tuner.state == tuner.STATE_COMPLETED


def test_thermal_observer_gates_heating_rate_on_high_demand():
    model = ThermalObserver("climate.multizone_thermostat_soggiorno")
    model._last_temp = 19.0
    model._last_temp_time = 100.0
    model._is_heating = True

    # Simulate low-duty maintenance (40%): must NOT update heating_rate
    orig_monotonic = sys.modules["custom_components.multizone_thermostat.thermal_model"].time.monotonic
    try:
        sys.modules["custom_components.multizone_thermostat.thermal_model"].time.monotonic = lambda: 1900.0
        model.update(19.4, is_heating=True, demand=40.0)
        assert model.heating_rate == 0.0

        # Next update at high demand (80% over 0.5h = 0.8 C/hr -> normalized 0.8/0.8 = 1.0 C/hr)
        model._last_temp = 19.0
        model._last_temp_time = 100.0
        model.update(19.4, is_heating=True, demand=80.0)
        assert model.heating_rate == pytest.approx(1.0, rel=1e-3)
    finally:
        sys.modules["custom_components.multizone_thermostat.thermal_model"].time.monotonic = orig_monotonic


def test_weekly_ema_autotuner_filtering_clamping_and_manual_override():
    tuner = PassiveAutotuneObserver("climate.multizone_thermostat_soggiorno", required_cycles=3)
    t0 = 1_700_000_000.0
    _complete_initial_cycles(tuner, base_wall=t0)

    learned_kp_0 = tuner._learned_kp
    learned_ki_0 = tuner._learned_ki
    learned_kd_0 = tuner._learned_kd
    assert learned_kp_0 > 0

    # Lock manual override on Kd only; Kp and Ki remain adaptive
    tuner.set_manual_pid(kd=456.0)
    assert tuner.kd == pytest.approx(456.0)
    assert tuner.kp == pytest.approx(learned_kp_0)

    # Record 3 high-demand ramps inside week 1 (+1..+3 days):
    # First 2 ramps normal, 3rd ramp slow/distorted, checking median & weekly gate
    for day_idx, slope_mult in enumerate((1.3, 1.35, 0.25), start=1):
        ramp_t = t0 + day_idx * 86400.0
        tuner.update(18.5, True, now=ramp_t, demand=92.0, cooling_rate=0.4)
        for s in range(1, 11):
            t_cur = ramp_t + s * 60.0
            temp = 18.5 if s <= 1 else 18.5 + (s - 1) * (0.18 * slope_mult)
            tuner.update(temp, True, now=t_cur, demand=92.0, cooling_rate=0.4)
        # End ramp (demand drops below 85%)
        tuner.update(20.0, True, now=ramp_t + 660.0, demand=40.0, cooling_rate=0.4)

    assert len(tuner.weekly_candidates) == 3
    # 7 days have NOT elapsed yet -> learned gains must stay untouched
    assert tuner._learned_kp == pytest.approx(learned_kp_0)

    # Cross the 7-day boundary -> weekly EMA triggers
    week_later = tuner.last_weekly_update + 7 * 86400.0 + 60.0
    tuner.update(20.5, False, now=week_later, demand=0.0, cooling_rate=0.4)
    assert tuner.weekly_updated_last_tick is True
    assert len(tuner.weekly_candidates) == 0

    # Step clamped to <= +/-10% per week
    assert abs(tuner._learned_kp - learned_kp_0) <= learned_kp_0 * 0.100001
    assert abs(tuner._learned_ki - learned_ki_0) <= learned_ki_0 * 0.100001
    assert abs(tuner._learned_kd - learned_kd_0) <= learned_kd_0 * 0.100001

    # Manual override on Kd MUST remain untouched even though _learned_kd changed
    assert tuner.kd == pytest.approx(456.0)
    assert tuner.kp == pytest.approx(tuner._learned_kp)


async def test_master_demand_updates_with_orchestrator_and_aliased_entity():
    hass = _make_fake_hass(
        states={
            "climate.custom_soggiorno_renamed": SimpleNamespace(
                entity_id="climate.custom_soggiorno_renamed",
                state="heat",
                attributes={"current_temperature": 18.0, "temperature": 21.0},
                last_reported=None,
                last_updated=None,
            )
        }
    )
    entry = _make_entry()
    coord = MultizoneCoordinator(hass, entry)
    coord.storage._settings["master_state"] = True
    coord._master_state = True

    canon_id = make_zone_entity_id("Soggiorno")
    climate_mock = SimpleNamespace(
        entity_id="climate.custom_soggiorno_renamed",
        current_temperature=18.0,
        target_temperature=21.0,
        hvac_mode="heat",
    )
    coord.register_climate(
        "climate.custom_soggiorno_renamed",
        lambda: None,
        climate_mock,
        canonical_id=canon_id,
    )

    assert coord.resolve_zone_id("climate.custom_soggiorno_renamed") == canon_id

    # Before tick, MasterDemandSensor fallback should read calculated demand (initially 0),
    # then _async_update_boiler evaluates zones proactively
    await coord.plant_orchestrator._async_update_boiler()
    assert coord.get_zone_demand(canon_id) == pytest.approx(100.0)
    assert coord.plant_orchestrator.last_aggregate is not None
    assert coord.plant_orchestrator.last_aggregate.demand == pytest.approx(100.0)

    sensor = MultizoneMasterDemandSensor(hass, entry.entry_id, coord)
    assert sensor.native_value == pytest.approx(100.0)

    # Fallback check when last_aggregate is cleared while Master ON
    coord.plant_orchestrator.last_aggregate = None
    assert sensor.native_value == pytest.approx(100.0)

    # When Master OFF and no frost emergency, MasterDemandSensor returns 0.0
    coord._master_state = False
    assert sensor.native_value == pytest.approx(0.0)


async def test_pid_entities_safety_lock_button_and_services():
    hass = _make_fake_hass(
        states={
            "climate.multizone_thermostat_soggiorno": SimpleNamespace(
                entity_id="climate.multizone_thermostat_soggiorno",
                state="heat",
                attributes={"current_temperature": 20.0, "temperature": 21.0},
                last_reported=None,
                last_updated=None,
            )
        }
    )
    entry = _make_entry()
    coord = MultizoneCoordinator(hass, entry)
    coord.storage = MagicMock()
    coord.storage.async_set_persistent_data = AsyncMock()
    coord.async_set_persistent_data = AsyncMock(
        side_effect=lambda k, v: coord._settings.__setitem__(k, v)
    )
    coord.zone_controller.async_save_autotuner_states = AsyncMock()

    canon_id = make_zone_entity_id("Soggiorno")
    tuner = coord.get_autotuner(canon_id)
    _complete_initial_cycles(tuner)
    coord.zone_controller._apply_tuner_pid_to_controller(canon_id)
    initial_kp = tuner.kp

    device_info = MagicMock()
    unlock_sw = MultizonePIDManualUnlockSwitch(coord, entry.entry_id, "Soggiorno")
    kp_num = MultizoneZonePIDNumber(
        coord, entry.entry_id, "Soggiorno", "Kp", 0.1, 500.0, 0.1, 2, device_info
    )
    reset_btn = MultizoneResetAutotuneButton(coord, entry.entry_id, "Soggiorno", device_info)
    auto_sensor = AutotuneSensor(hass, entry.entry_id, "Soggiorno", canon_id, coord)

    unlock_sw.hass = hass
    kp_num.hass = hass
    reset_btn.hass = hass
    auto_sensor.hass = hass
    unlock_sw.async_write_ha_state = MagicMock()
    kp_num.async_write_ha_state = MagicMock()
    auto_sensor.async_write_ha_state = MagicMock()

    # Safety lock defaults OFF -> edit attempt is blocked + creates persistent_notification
    assert unlock_sw.is_on is False
    assert kp_num.extra_state_attributes["locked"] is True
    await kp_num.async_set_native_value(222.0)
    assert tuner.kp == pytest.approx(initial_kp)
    assert any(
        d == "persistent_notification" and s == "create"
        for d, s, _, _ in hass.services.calls
    )

    # Unlock switch ON -> edit is allowed and updates PID + sensor state
    await unlock_sw.async_turn_on()
    assert unlock_sw.is_on is True
    await kp_num.async_set_native_value(175.5)
    assert tuner.kp == pytest.approx(175.5)
    assert coord.zone_controller.get_pid(canon_id)._pid._Kp == pytest.approx(175.5)
    assert "Kp" in tuner.manual_overrides
    assert auto_sensor.native_value == "Smart PID + Manual"
    assert auto_sensor.extra_state_attributes["manual_overrides"] == ["Kp"]

    # Press Reset Autotuner button -> clears cycles and overrides
    await reset_btn.async_press()
    assert tuner.state == tuner.STATE_IDLE
    assert tuner.completed_cycles == []
    assert tuner.manual_overrides == {}
    assert coord.zone_controller.get_pid(canon_id)._pid._Kp == pytest.approx(100.0)


async def test_services_set_pid_and_reset_autotune_registered():
    hass = _make_fake_hass()
    hass.data[DOMAIN] = {"_static_path_registered": True}
    entry = _make_entry(entry_id="svc_test")
    ok = await async_setup_entry(hass, entry)
    assert ok is True

    assert (DOMAIN, "set_pid_parameters") in hass.services.handlers
    assert (DOMAIN, "reset_autotune") in hass.services.handlers

    coord = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    canon_id = make_zone_entity_id("Soggiorno")

    await hass.services.async_call(
        DOMAIN,
        "set_pid_parameters",
        {"climate_entity": canon_id, "kp": 140.0, "unlock": True},
    )
    assert coord.get_pid_manual_unlock("Soggiorno") is True
    assert coord.get_autotuner(canon_id).kp == pytest.approx(140.0)

    # Lock Kp back to automatic baseline
    await hass.services.async_call(
        DOMAIN,
        "set_pid_parameters",
        {"climate_entity": canon_id, "lock_parameter": "Kp", "unlock": False},
    )
    assert coord.get_pid_manual_unlock("Soggiorno") is False
    assert "Kp" not in coord.get_autotuner(canon_id).manual_overrides

    # Complete cycles then reset via service
    _complete_initial_cycles(coord.get_autotuner(canon_id))
    assert coord.get_autotuner(canon_id).state == PassiveAutotuneObserver.STATE_COMPLETED

    await hass.services.async_call(
        DOMAIN,
        "reset_autotune",
        {"climate_entity": canon_id},
    )
    assert coord.get_autotuner(canon_id).state == PassiveAutotuneObserver.STATE_IDLE


def test_frontend_bundle_contains_pid_controls_and_is_current():
    build_path = Path(__file__).resolve().parents[1] / "frontend" / "build.py"
    spec = importlib.util.spec_from_file_location("build", build_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.build(check_only=True) is True

    bundle_path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "multizone_thermostat"
        / "www"
        / "multizone-thermostat-card.js"
    )
    content = bundle_path.read_text(encoding="utf-8")
    for marker in (
        "pid-box-kp",
        "pid-box-ki",
        "pid-box-kd",
        "pid-modal-backdrop",
        "set_pid_parameters",
        "reset_autotune",
    ):
        assert marker in content
