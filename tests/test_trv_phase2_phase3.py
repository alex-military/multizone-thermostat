"""Tests for TRV Phase 2 (Demand-Driven Valve Mode) and Phase 3 (Hydraulic Guard & Diagnostics)."""
from __future__ import annotations

import json
import pathlib
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from homeassistant.components.climate import HVACMode
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import Event

from custom_components.multizone_thermostat.boiler.opentherm_backend import OpenThermBoilerBackend
from custom_components.multizone_thermostat.boiler.relay_backend import RelayBoilerBackend
from custom_components.multizone_thermostat.boiler.valve_readiness import is_trv_reported_closed
from custom_components.multizone_thermostat.config_flow.schemas import (
    get_add_zone_schema,
    get_options_edit_zone_schema,
)
from custom_components.multizone_thermostat.const import (
    CONF_ZONE_CLIMATES,
    CONF_ZONE_NAME,
    CONF_ZONE_TRV_CLOSE_OFFSET,
    CONF_ZONE_TRV_CONTROL_MODE,
    CONF_ZONE_TRV_OPEN_BOOST,
    TRV_CONTROL_MODE_DEMAND_DRIVEN,
    TRV_CONTROL_MODE_STANDARD,
    ZONE_MODE_PRIMARY,
    make_zone_entity_id,
)
from custom_components.multizone_thermostat.plant_diagnostics.anomalies import evaluate_zone_anomalies
from custom_components.multizone_thermostat.plant_diagnostics.const import (
    ANOMALY_LABELS,
    ANOMALY_NONE,
    ANOMALY_TRV_NOT_OPENING,
)
from custom_components.multizone_thermostat.plant_diagnostics.engine import PlantDiagnosticsEngine
from custom_components.multizone_thermostat.sync_manager import ZoneSyncManager


def _make_sync_manager(
    *,
    trv_control_mode: str = TRV_CONTROL_MODE_DEMAND_DRIVEN,
    trv_open_boost: float = 1.5,
    trv_close_offset: float = 1.0,
    calibrations: dict[str, str] | None = None,
) -> ZoneSyncManager:
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    coordinator = MagicMock()
    coordinator.get_persistent_data.return_value = True
    coordinator.get_master_state.return_value = True
    coordinator.get_zone_mode.return_value = ZONE_MODE_PRIMARY
    coordinator.get_zone_demand.return_value = 0.0
    return ZoneSyncManager(
        hass=hass,
        coordinator=coordinator,
        zone_name="Soggiorno",
        entity_id="climate.multizone_thermostat_soggiorno",
        climates=["climate.trv_1"],
        switches=[],
        calibrations=calibrations if calibrations is not None else {},
        trv_control_mode=trv_control_mode,
        trv_open_boost=trv_open_boost,
        trv_close_offset=trv_close_offset,
    )


@pytest.mark.asyncio
async def test_demand_driven_bounded_overdrive_open_and_close():
    """Demand-driven mode sends bounded open boost when demanding and bounded close offset when idle."""
    mgr = _make_sync_manager(trv_open_boost=1.5, trv_close_offset=1.0)
    trv_state = MagicMock(
        state=HVACMode.HEAT,
        attributes={
            ATTR_TEMPERATURE: 20.0,
            "current_temperature": 19.5,
            "min_temp": 5.0,
            "max_temp": 35.0,
            "target_temp_step": 0.5,
        },
    )
    mgr.hass.states.get.return_value = trv_state

    clock = {"now": 100.0}
    with patch("custom_components.multizone_thermostat.sync_manager.time.monotonic", side_effect=lambda: clock["now"]):
        mgr._coordinator.get_zone_demand.return_value = 50.0
        await mgr.async_sync_trvs(
            master_hvac_mode=HVACMode.HEAT,
            master_target_temp=20.0,
            master_current_temp=19.5,
            safety_fallback_active=False,
            has_external_sensor=True,
        )
        assert mgr.demand_valve_open is True
        mgr.hass.services.async_call.assert_awaited_once()
        assert mgr.hass.services.async_call.await_args_list[-1].args[2]["temperature"] == 21.0

        mgr.hass.services.async_call.reset_mock()
        trv_state.attributes["max_temp"] = 20.5
        trv_state.attributes[ATTR_TEMPERATURE] = 21.0
        await mgr.async_sync_trvs(
            master_hvac_mode=HVACMode.HEAT,
            master_target_temp=20.0,
            master_current_temp=19.5,
            safety_fallback_active=False,
            has_external_sensor=True,
        )
        assert mgr.hass.services.async_call.await_args_list[-1].args[2]["temperature"] == 20.5

        mgr.hass.services.async_call.reset_mock()
        trv_state.attributes["max_temp"] = 35.0
        clock["now"] = 170.0
        mgr._coordinator.get_zone_demand.return_value = 0.0
        await mgr.async_sync_trvs(
            master_hvac_mode=HVACMode.HEAT,
            master_target_temp=20.0,
            master_current_temp=19.5,
            safety_fallback_active=False,
            has_external_sensor=True,
        )
        assert mgr.demand_valve_open is False
        assert mgr.hass.services.async_call.await_args_list[-1].args[2]["temperature"] == 18.5


@pytest.mark.asyncio
async def test_demand_driven_hysteresis_debounce_and_idle_no_chatter():
    """Hysteresis + 60s debounce prevent flip-flop, and idle guard avoids upward RF chatter."""
    mgr = _make_sync_manager(trv_open_boost=1.5, trv_close_offset=1.0)
    trv_state = MagicMock(
        state=HVACMode.HEAT,
        attributes={
            ATTR_TEMPERATURE: 20.0,
            "current_temperature": 20.0,
            "min_temp": 5.0,
            "max_temp": 35.0,
            "target_temp_step": 0.5,
        },
    )
    mgr.hass.states.get.return_value = trv_state

    clock = {"now": 100.0}
    with patch("custom_components.multizone_thermostat.sync_manager.time.monotonic", side_effect=lambda: clock["now"]):
        await mgr.async_sync_trvs(HVACMode.HEAT, 20.0, 20.0, False, True, zone_demand=40.0)
        assert mgr.demand_valve_open is True
        trv_state.attributes[ATTR_TEMPERATURE] = 21.5

        clock["now"] = 120.0
        mgr.hass.services.async_call.reset_mock()
        await mgr.async_sync_trvs(HVACMode.HEAT, 20.0, 20.0, False, True, zone_demand=0.0)
        assert mgr.demand_valve_open is True
        mgr.hass.services.async_call.assert_not_awaited()

        clock["now"] = 170.0
        await mgr.async_sync_trvs(HVACMode.HEAT, 20.0, 20.0, False, True, zone_demand=0.0)
        assert mgr.demand_valve_open is False
        assert mgr.hass.services.async_call.await_args_list[-1].args[2]["temperature"] == 19.0
        trv_state.attributes[ATTR_TEMPERATURE] = 19.0

        clock["now"] = 240.0
        mgr.hass.services.async_call.reset_mock()
        await mgr.async_sync_trvs(HVACMode.HEAT, 20.0, 20.0, False, True, zone_demand=4.0)
        assert mgr.demand_valve_open is False

        await mgr.async_sync_trvs(HVACMode.HEAT, 20.0, 21.5, False, True, zone_demand=0.0)
        mgr.hass.services.async_call.assert_not_awaited()
        trv_state.attributes["current_temperature"] = 21.5
        await mgr.async_sync_trvs(HVACMode.HEAT, 20.0, 21.5, False, True, zone_demand=0.0)
        mgr.hass.services.async_call.assert_not_awaited()


@pytest.mark.asyncio
async def test_demand_driven_safety_fallback_reverts_to_standard():
    """When room sensor safety fallback is active, demand_driven reverts to standard target setpoint."""
    mgr = _make_sync_manager(trv_open_boost=2.0, trv_close_offset=1.0)
    trv_state = MagicMock(
        state=HVACMode.HEAT,
        attributes={
            ATTR_TEMPERATURE: 18.0,
            "current_temperature": 19.0,
            "min_temp": 5.0,
            "max_temp": 35.0,
            "target_temp_step": 0.5,
        },
    )
    mgr.hass.states.get.return_value = trv_state

    await mgr.async_sync_trvs(
        master_hvac_mode=HVACMode.HEAT,
        master_target_temp=20.0,
        master_current_temp=19.0,
        safety_fallback_active=True,
        has_external_sensor=True,
        zone_demand=90.0,
    )
    assert mgr.demand_valve_open is None
    assert mgr.trv_health["climate.trv_1"]["trv_control_mode"] == f"{TRV_CONTROL_MODE_STANDARD}_fallback"
    assert mgr.hass.services.async_call.await_args_list[-1].args[2]["temperature"] == 20.0


@pytest.mark.asyncio
async def test_demand_driven_physical_sync_relative_delta():
    """Turning physical TRV knob after a boosted target emits exact relative delta without spurious jump."""
    mgr = _make_sync_manager(trv_open_boost=1.5)
    trv_state = MagicMock(
        state=HVACMode.HEAT,
        attributes={ATTR_TEMPERATURE: 20.0, "current_temperature": 20.0, "target_temp_step": 0.5},
    )
    mgr.hass.states.get.return_value = trv_state

    await mgr.async_sync_trvs(HVACMode.HEAT, 20.0, 20.0, False, True, zone_demand=60.0)
    assert mgr._last_known_trv_targets["climate.trv_1"] == 21.5

    echo_event = Event(
        "state_changed",
        {
            "entity_id": "climate.trv_1",
            "old_state": MagicMock(state=HVACMode.HEAT, attributes={ATTR_TEMPERATURE: 20.0}),
            "new_state": MagicMock(state=HVACMode.HEAT, attributes={ATTR_TEMPERATURE: 21.5}),
        },
    )
    assert await mgr.process_trv_change(echo_event, None, HVACMode.HEAT, 5.0, 35.0) == (None, None)

    knob_event = Event(
        "state_changed",
        {
            "entity_id": "climate.trv_1",
            "old_state": MagicMock(state=HVACMode.HEAT, attributes={ATTR_TEMPERATURE: 21.5}),
            "new_state": MagicMock(state=HVACMode.HEAT, attributes={ATTR_TEMPERATURE: 22.5}),
        },
    )
    assert await mgr.process_trv_change(knob_event, None, HVACMode.HEAT, 5.0, 35.0) == (None, 1.0)


def test_trv_phase2_schemas_and_translation_parity():
    """New Phase 2 options exist in config/options schemas and across strings + all 6 translations."""
    add_schema = get_add_zone_schema()
    edit_schema = get_options_edit_zone_schema({"name": "Soggiorno"}, {}, {})
    for s in (add_schema, edit_schema):
        trv_sec = None
        for k, v in s.schema.items():
            if getattr(k, "schema", None) == "trv_settings":
                inner = getattr(v, "schema", v)
                trv_sec = getattr(inner, "schema", inner)
                break
        assert trv_sec is not None
        sec_keys = {getattr(k, "schema", k) for k in trv_sec}
        assert CONF_ZONE_TRV_CONTROL_MODE in sec_keys
        assert CONF_ZONE_TRV_OPEN_BOOST in sec_keys
        assert CONF_ZONE_TRV_CLOSE_OFFSET in sec_keys

    base = pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "multizone_thermostat"
    files = [base / "strings.json"] + list((base / "translations").glob("*.json"))
    assert len(files) == 7
    for p in files:
        d = json.loads(p.read_text(encoding="utf-8"))
        for flow_k in ("config", "options"):
            for step_k, step_v in d[flow_k]["step"].items():
                secs = step_v.get("sections", {})
                if "trv_settings" in secs:
                    keys = secs["trv_settings"]["data"]
                    for req in ("trv_control_mode", "trv_open_boost", "trv_close_offset"):
                        assert req in keys, f"{p.name} missing {req} in {flow_k}.{step_k}"


def test_is_trv_reported_closed_and_hvac_action_fallback():
    """Verify valve telemetry helper covers numeric position attributes and hvac_action fallback."""
    assert is_trv_reported_closed(MagicMock(state="heat", attributes={"position": 5})) is True
    assert is_trv_reported_closed(MagicMock(state="heat", attributes={"position": 25})) is False
    assert is_trv_reported_closed(MagicMock(state="heat", attributes={"hvac_action": "idle"})) is True
    assert is_trv_reported_closed(MagicMock(state="off", attributes={"hvac_action": "off"})) is True
    assert is_trv_reported_closed(MagicMock(state="heat", attributes={"hvac_action": "heating"})) is False
    assert is_trv_reported_closed(MagicMock(state="heat", attributes={})) is None
    assert is_trv_reported_closed(MagicMock(state="unavailable", attributes={"hvac_action": "idle"})) is None


@pytest.mark.asyncio
async def test_hydraulic_guard_opentherm_and_relay():
    """Verify HOLD_TRV_CLOSED + valve_delay on cold starts across OpenTherm and Relay backends."""
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    coord = MagicMock()
    coord.zones = [{CONF_ZONE_NAME: "Salotto", CONF_ZONE_CLIMATES: ["climate.trv_1"]}]
    coord.get_zone_mode.return_value = ZONE_MODE_PRIMARY
    coord.get_zone_demand.return_value = 60.0
    coord.weather_sensor_id = None
    coord.is_dhw_active = False
    coord.plant_diagnostics = MagicMock()
    coord.plant_diagnostics.get_opentherm_diagnostics.return_value = {}
    coord.plant_diagnostics._current_boiler_start = None
    coord.get_persistent_data.return_value = 0.0

    trv_state = MagicMock(state="heat", attributes={"hvac_action": "idle"})
    ot_state = MagicMock(state="off", attributes={"temperature": 35.0})
    states = {"climate.trv_1": trv_state, "climate.opentherm": ot_state, "switch.boiler": MagicMock(state="off")}
    hass.states.get.side_effect = lambda eid: states.get(eid)

    clock = {"now": 100.0}
    with patch("custom_components.multizone_thermostat.boiler.opentherm_backend.time.monotonic", side_effect=lambda: clock["now"]):
        ot = OpenThermBoilerBackend(hass, coord, "climate.opentherm", 35.0, 75.0, valve_delay=15)
        await ot.async_update(60.0, "Salotto", False)
        assert ot.status_reason.startswith("HOLD_TRV_CLOSED")
        hass.services.async_call.assert_not_awaited()

        trv_state.attributes["hvac_action"] = "heating"
        await ot.async_update(60.0, "Salotto", False)
        assert ot.status_reason.startswith("WAITING_VALVES")
        hass.services.async_call.assert_not_awaited()

        clock["now"] = 120.0
        await ot.async_update(60.0, "Salotto", False)
        assert ot.status_reason.startswith("MODULATING")
        hass.services.async_call.assert_awaited()

        hass.services.async_call.reset_mock()
        ot_state.state = "heat"
        trv_state.attributes["hvac_action"] = "idle"
        await ot.async_update(50.0, "Salotto", False)
        assert ot.status_reason.startswith("MODULATING")

    trv_state.attributes["hvac_action"] = "idle"
    with patch("custom_components.multizone_thermostat.boiler.relay_backend.time.monotonic", side_effect=lambda: clock["now"]):
        relay = RelayBoilerBackend(hass, coord, "switch.boiler", 0, 0, 0)
        await relay.async_update(60.0, "Salotto", False)
        assert relay.status_reason.startswith("HOLD_TRV_CLOSED")


def test_anomaly_trv_not_opening_non_blocking():
    """Active diagnostic triggers trv_not_opening after >5 min closed with boiler ON & demand >20%, without fault lockout."""
    hass = MagicMock()
    coord = MagicMock()
    zname = "Salotto"
    cid = make_zone_entity_id(zname)
    coord.zones = [
        {
            CONF_ZONE_NAME: zname,
            CONF_ZONE_CLIMATES: ["climate.trv_1"],
            "sensor_timeout_min": 240,
        }
    ]
    coord.get_zone_mode.return_value = ZONE_MODE_PRIMARY
    coord.get_zone_demand.return_value = 45.0
    coord.get_zone_current_temp.return_value = 18.5
    coord.get_zone_target_temp.return_value = 21.0
    coord.zone_manager.get_zone.return_value = coord.zones[0]
    coord.zone_manager.is_passive_heat_allowed.return_value = False
    coord.get_persistent_data.return_value = None

    zone_state = MagicMock(state="heat", attributes={"current_temperature": 18.5, "temperature": 21.0})
    trv_state = MagicMock(state="heat", attributes={"position": 5})
    hass.states.get.side_effect = lambda eid: zone_state if eid == cid else (trv_state if eid == "climate.trv_1" else None)

    state = {
        "active_anomaly": ANOMALY_NONE,
        "anomaly_details": "No anomaly detected",
        "high_demand_start_time": None,
        "high_demand_start_temp": None,
        "ghost_heat_start_temp": None,
        "last_temp_seen": None,
        "last_temp_time": None,
        "last_heating_time": None,
        "trv_closed_start_time": None,
    }

    clock = {"now": 1000.0}
    with patch("custom_components.multizone_thermostat.plant_diagnostics.anomalies.time.monotonic", side_effect=lambda: clock["now"]):
        assert evaluate_zone_anomalies(coord, hass, cid, state, boiler_on=True)[0] == ANOMALY_NONE
        clock["now"] = 1200.0
        assert evaluate_zone_anomalies(coord, hass, cid, state, boiler_on=True)[0] == ANOMALY_NONE
        clock["now"] = 1310.0
        anom, details = evaluate_zone_anomalies(coord, hass, cid, state, boiler_on=True)
        assert anom == ANOMALY_TRV_NOT_OPENING
        assert "closed/idle" in details
        assert ANOMALY_TRV_NOT_OPENING in ANOMALY_LABELS

        engine = PlantDiagnosticsEngine(coord)
        engine._zone_anomaly_state[cid] = dict(state)
        assert engine.has_critical_sensor_fault(cid) is False

        trv_state.attributes["position"] = 60
        assert evaluate_zone_anomalies(coord, hass, cid, state, boiler_on=True)[0] == ANOMALY_NONE
        assert state["trv_closed_start_time"] is None
