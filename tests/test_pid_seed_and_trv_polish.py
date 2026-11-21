"""Tests for PID Auto EMA baseline seeding (@serv2002) and TRV review polish."""
from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from homeassistant.components.climate import HVACMode
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import Event, State

from custom_components.multizone_thermostat import async_setup_entry
from custom_components.multizone_thermostat.autotune import PassiveAutotuneObserver
from custom_components.multizone_thermostat.climate import MultizoneVirtualThermostat
from custom_components.multizone_thermostat.const import (
    CONF_BOILER_MODE,
    CONF_ZONE_CLIMATES,
    CONF_ZONE_NAME,
    CONF_ZONE_TEMP_SENSOR,
    CONF_ZONE_TRV_CONTROL_MODE,
    CONF_ZONES,
    DOMAIN,
    MODE_CENTRAL,
    TRV_CONTROL_MODE_DEMAND_DRIVEN,
    make_zone_entity_id,
)
from custom_components.multizone_thermostat.zone_controller import ZoneController


class _FakeServices:
    def __init__(self) -> None:
        self.handlers = {}

    def async_register(self, domain, service, handler, schema=None) -> None:
        self.handlers[(domain, service)] = (handler, schema)

    async def async_call(self, domain, service, data=None, blocking=False) -> None:
        entry = self.handlers.get((domain, service))
        if entry is not None:
            handler, schema = entry
            payload = schema(data or {}) if schema is not None else (data or {})
            await handler(SimpleNamespace(data=payload))


class _FakeStates:
    def __init__(self, initial=None) -> None:
        self._states = dict(initial or {})

    def get(self, entity_id):
        return self._states.get(entity_id)


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


def _make_zone_controller(zone_name: str = "Soggiorno") -> tuple[ZoneController, str]:
    hass = MagicMock()
    coord = MagicMock()
    coord.zones = [{CONF_ZONE_NAME: zone_name}]
    coord.storage = MagicMock()
    coord.storage.async_save_autotuner_states = AsyncMock()
    coord.master_hvac_mode = "heat"
    coord.resolve_zone_id = lambda x: x
    zc = ZoneController(hass, coord)
    return zc, make_zone_entity_id(zone_name)


def test_seed_pi_only_preserves_zero_kd_across_weekly_ema_and_persistence():
    """Seeding Kd=0.0 preserves pure PI mode across weekly EMA updates and state save/load."""
    tuner = PassiveAutotuneObserver("Soggiorno", required_cycles=3)
    tuner.seed_learned_pid(100.0, 0.1, 0.0)
    assert tuner._seeded_pi_only is True
    assert tuner.kd == 0.0

    tuner.last_weekly_update = 1000.0
    tuner.weekly_candidates = [
        {"Kp": 120.0, "Ki": 0.15, "Kd": 350.0},
        {"Kp": 110.0, "Ki": 0.14, "Kd": 400.0},
        {"Kp": 130.0, "Ki": 0.16, "Kd": 300.0},
    ]
    tuner._update_weekly_learning(
        current_temp=20.0,
        is_active=False,
        now_mono=500.0,
        wall_time=1000.0 + tuner.WEEKLY_INTERVAL_SECONDS + 10.0,
        demand=0.0,
        cooling_rate=0.0,
    )
    assert tuner.weekly_updated_last_tick is True
    assert tuner._learned_kd == 0.0
    assert tuner.kd == 0.0
    assert tuner._learned_kp > 100.0

    dumped = tuner.dump_state()
    assert dumped["seeded_pi_only"] is True
    restored = PassiveAutotuneObserver("Soggiorno", required_cycles=3)
    restored.load_state(dumped)
    assert restored._seeded_pi_only is True
    assert restored.kd == 0.0

    restored.weekly_candidates = [
        {"Kp": 110.0, "Ki": 0.12, "Kd": 500.0},
        {"Kp": 115.0, "Ki": 0.13, "Kd": 520.0},
        {"Kp": 120.0, "Ki": 0.14, "Kd": 480.0},
    ]
    restored._update_weekly_learning(
        current_temp=20.0,
        is_active=False,
        now_mono=600.0,
        wall_time=restored.last_weekly_update + restored.WEEKLY_INTERVAL_SECONDS + 10.0,
        demand=0.0,
        cooling_rate=0.0,
    )
    assert restored.weekly_updated_last_tick is True
    assert restored._learned_kd == 0.0
    assert restored.kd == 0.0


def test_seed_low_kp_respects_weekly_step_cap():
    """Low seeded Kp (< 10.0) steps gradually via +-10% EMA without snapping up to 10.0 or 2x baseline."""
    tuner = PassiveAutotuneObserver("Soggiorno", required_cycles=3)
    tuner.seed_learned_pid(4.0, 0.02, 10.0)
    tuner.last_weekly_update = 1000.0
    tuner.weekly_candidates = [
        {"Kp": 80.0, "Ki": 0.05, "Kd": 20.0},
        {"Kp": 90.0, "Ki": 0.05, "Kd": 25.0},
        {"Kp": 70.0, "Ki": 0.04, "Kd": 15.0},
    ]
    tuner._update_weekly_learning(
        current_temp=20.0,
        is_active=False,
        now_mono=500.0,
        wall_time=1000.0 + tuner.WEEKLY_INTERVAL_SECONDS + 10.0,
        demand=0.0,
        cooling_rate=0.0,
    )
    assert tuner._learned_kp == pytest.approx(4.4)

    tuner.weekly_candidates = [
        {"Kp": 1.5, "Ki": 0.02, "Kd": 10.0},
        {"Kp": 1.5, "Ki": 0.02, "Kd": 10.0},
        {"Kp": 1.5, "Ki": 0.02, "Kd": 10.0},
    ]
    tuner._update_weekly_learning(
        current_temp=20.0,
        is_active=False,
        now_mono=600.0,
        wall_time=tuner.last_weekly_update + tuner.WEEKLY_INTERVAL_SECONDS + 10.0,
        demand=0.0,
        cooling_rate=0.0,
    )
    assert 3.9 <= tuner._learned_kp <= 4.0


@pytest.mark.asyncio
async def test_partial_seed_protection_and_unlock_ordering():
    """Partial seed rejects empty Kp before learning, preserves untouched overrides, and service locks only when cleared."""
    zc, cid = _make_zone_controller("Soggiorno")
    tuner = zc.get_autotuner(cid)
    tuner.set_manual_pid(ki=0.25)

    assert await zc.async_set_zone_pid(cid, ki=0.05, seed_autotuner=True) is False
    assert tuner.state == PassiveAutotuneObserver.STATE_IDLE
    assert tuner.manual_overrides == {"Ki": 0.25}

    assert await zc.async_set_zone_pid(cid, kp=80.0, seed_autotuner=True) is True
    assert tuner.state == PassiveAutotuneObserver.STATE_COMPLETED
    assert tuner._learned_kp == pytest.approx(80.0)
    assert tuner.kp == pytest.approx(80.0)
    assert tuner.manual_overrides == {"Ki": 0.25}
    assert tuner.ki == pytest.approx(0.25)

    assert await zc.async_set_zone_pid(cid, kp=100.0, ki=0.1, kd=0.0, seed_autotuner=True) is True
    assert tuner.manual_overrides == {}
    assert tuner._seeded_pi_only is True

    hass = _make_fake_hass()
    hass.data[DOMAIN] = {"_static_path_registered": True}
    entry = MagicMock()
    entry.entry_id = "seed_order_test"
    entry.data = {
        CONF_BOILER_MODE: MODE_CENTRAL,
        CONF_ZONES: [{CONF_ZONE_NAME: "Soggiorno", CONF_ZONE_TEMP_SENSOR: "sensor.temp"}],
    }
    entry.options = {}
    await async_setup_entry(hass, entry)

    coord = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    canon_id = make_zone_entity_id("Soggiorno")

    await hass.services.async_call(
        DOMAIN,
        "set_pid_parameters",
        {"climate_entity": canon_id, "ki": 0.2, "unlock": True},
    )
    assert coord.get_pid_manual_unlock("Soggiorno") is True

    await hass.services.async_call(
        DOMAIN,
        "set_pid_parameters",
        {"climate_entity": canon_id, "kd": 10.0, "seed_autotuner": True},
    )
    assert coord.get_pid_manual_unlock("Soggiorno") is True

    await hass.services.async_call(
        DOMAIN,
        "set_pid_parameters",
        {"climate_entity": canon_id, "kp": 90.0, "seed_autotuner": True},
    )
    assert coord.get_pid_manual_unlock("Soggiorno") is True

    await hass.services.async_call(
        DOMAIN,
        "set_pid_parameters",
        {"climate_entity": canon_id, "kp": 100.0, "ki": 0.1, "kd": 0.0, "seed_autotuner": True},
    )
    assert coord.get_pid_manual_unlock("Soggiorno") is False
    assert coord.get_autotuner(canon_id)._seeded_pi_only is True


@pytest.mark.asyncio
async def test_climate_demand_driven_sensor_dropout_and_staleness_tick():
    """Demand-driven zone immediately triggers TRV sync on sensor unavailable and runs staleness check on 10s tick."""
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    scheduled = []
    hass.async_create_task = MagicMock(side_effect=lambda coro: scheduled.append(coro))
    hass.states.get.return_value = State("climate.trv_1", HVACMode.HEAT, {"current_temperature": 19.5})

    coord = MagicMock()
    coord.master_device_id = "master"
    coord.boiler_switch = "switch.boiler"
    coord.get_master_state.return_value = True
    coord.get_zone_mode.return_value = "primary"
    coord.get_zone_demand.return_value = 50.0
    coord.get_persistent_data.return_value = True
    coord.demand_aggregator.get_zone_weight.return_value = 1.0
    coord.zone_manager.is_passive_heat_allowed.return_value = False
    hass.data = {DOMAIN: {"e1": {"coordinator": coord}}}

    zone_data = {
        CONF_ZONE_NAME: "Salotto",
        CONF_ZONE_CLIMATES: ["climate.trv_1"],
        CONF_ZONE_TEMP_SENSOR: "sensor.room",
        CONF_ZONE_TRV_CONTROL_MODE: TRV_CONTROL_MODE_DEMAND_DRIVEN,
    }
    clim = MultizoneVirtualThermostat(hass, "e1", zone_data)
    clim._hvac_mode = HVACMode.HEAT
    clim._current_temperature = 19.5
    clim.async_write_ha_state = MagicMock()
    clim._trigger_trv_sync = AsyncMock(return_value=None)

    ev = Event("state_changed", {"entity_id": "sensor.room", "new_state": State("sensor.room", STATE_UNAVAILABLE)})
    clim._on_temp_changed(ev)
    assert clim._safety_fallback_active is True
    assert clim._trigger_trv_sync.called
    for c in scheduled:
        c.close()

    with (
        patch.object(clim, "check_sensor_staleness") as mock_stale,
        patch.object(clim._sync_manager, "async_demand_driven_tick", AsyncMock()) as mock_tick,
    ):
        await clim._async_trv_demand_tick(None)
        mock_stale.assert_called_once()
        mock_tick.assert_awaited_once()


def test_frontend_bundle_contains_pid_seed_ui_and_cancel_retranslation():
    """Production bundle matches source and includes PID Auto EMA Seed modal UI and cancel button retranslation."""
    root = Path(__file__).resolve().parents[1]
    build_path = root / "frontend" / "build.py"
    spec = importlib.util.spec_from_file_location("build", build_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.build(check_only=True) is True

    bundle_path = root / "custom_components" / "multizone_thermostat" / "www" / "multizone-thermostat-card.js"
    content = bundle_path.read_text(encoding="utf-8")
    for marker in (
        "pid-modal-mode-tabs",
        "pid-modal-seed-wrap",
        "pid_mode_seed",
        "pid_modal_scale_note",
        "seed_autotuner",
        "_setPidEditAction",
        "cancelBtn.innerText = t('pid_modal_cancel')",
    ):
        assert marker in content, f"Missing {marker} in bundle"
