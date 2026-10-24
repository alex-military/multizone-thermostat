"""Unit tests for Phase 8, 9, and 10 features:
- Phase 10: Configurable Demand Aggregator Strategy Select & persistence
- Phase 10: Dynamic Feed-Forward Weather Curve on OpenThermBoilerBackend
- Phase 8: OpenTherm Climate Telemetry (`hvac_action` -> `flame_active`)
- Phase 9: Authoritative Hardware Climate Sync & frost-setpoint / idle / reconnect filtering
"""
from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure dummy_ha modules are used rather than any leftover HomeAssistantMockFinder from earlier test files
sys.meta_path[:] = [
    f for f in sys.meta_path if f.__class__.__name__ != "HomeAssistantMockFinder"
]
for _mod_name in (
    "homeassistant.components.select",
    "homeassistant.helpers.restore_state",
    "homeassistant.helpers.entity",
):
    if _mod_name in sys.modules and isinstance(sys.modules[_mod_name], MagicMock):
        del sys.modules[_mod_name]

from homeassistant.components.climate import HVACMode
from homeassistant.const import ATTR_TEMPERATURE, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Context, Event, State

from custom_components.multizone_thermostat.boiler.opentherm_backend import (
    OpenThermBoilerBackend,
)
from custom_components.multizone_thermostat.climate import MultizoneVirtualThermostat
from custom_components.multizone_thermostat.const import (
    CONF_ZONE_AUTHORITATIVE_SYNC,
    CONF_ZONE_CLIMATES,
    CONF_ZONE_NAME,
    CONF_ZONE_SWITCHES,
    CONF_ZONE_TARGET_TEMP,
    CONF_ZONE_VALVES,
    CONF_ZONE_WEIGHT,
    DOMAIN,
    KEY_DEMAND_STRATEGY,
    ZONE_MODE_PRIMARY,
    make_zone_entity_id,
)
from custom_components.multizone_thermostat.demand_aggregator import (
    DEMAND_STRATEGY_MAX,
    DEMAND_STRATEGY_SUM_CAPPED,
    DEMAND_STRATEGY_WEIGHTED_AVERAGE,
    DemandAggregator,
)
from custom_components.multizone_thermostat.plant_diagnostics.anomalies import (
    get_opentherm_diagnostics,
)
from custom_components.multizone_thermostat.select import (
    MultizoneDemandStrategySelect,
    async_setup_entry as async_setup_select_entry,
)
from custom_components.multizone_thermostat.sync_manager import ZoneSyncManager


# =====================================================================
# 1. Phase 10 — Configurable Demand Strategy Select
# =====================================================================


@pytest.mark.asyncio
async def test_demand_strategy_select_switching_and_persistence():
    """Test switching strategies via MultizoneDemandStrategySelect and live effect on calculate()."""
    zones = [
        {CONF_ZONE_NAME: "Living", CONF_ZONE_WEIGHT: 2.0},
        {CONF_ZONE_NAME: "Studio", CONF_ZONE_WEIGHT: 8.0},
    ]
    aggregator = DemandAggregator(zones=zones)
    living_id = make_zone_entity_id("Living")
    studio_id = make_zone_entity_id("Studio")
    aggregator.set_zone_demand(living_id, 40.0)
    aggregator.set_zone_demand(studio_id, 80.0)

    settings: dict[str, str] = {}

    async def fake_set_persistent(key: str, val: str) -> None:
        settings[key] = val

    coordinator = MagicMock()
    coordinator.zones = zones
    coordinator.demand_aggregator = aggregator
    coordinator._settings = settings
    coordinator._select_entities = {}
    coordinator.get_persistent_data = lambda k, default=None: settings.get(k, default)
    coordinator.async_set_persistent_data = AsyncMock(side_effect=fake_set_persistent)
    coordinator.register_select = lambda k, ent: coordinator._select_entities.__setitem__(k, ent)
    coordinator.plant_orchestrator = MagicMock()
    coordinator.plant_orchestrator._async_update_boiler = AsyncMock()

    select_ent = MultizoneDemandStrategySelect(coordinator, "entry_123")
    select_ent.async_write_ha_state = MagicMock()

    assert select_ent.current_option == DEMAND_STRATEGY_MAX
    assert aggregator.calculate().demand == 80.0

    # Switch to weighted_average: (40*2 + 80*8) / 10 = 72.0%
    await select_ent.async_select_option(DEMAND_STRATEGY_WEIGHTED_AVERAGE)
    assert select_ent.current_option == DEMAND_STRATEGY_WEIGHTED_AVERAGE
    assert aggregator.strategy == DEMAND_STRATEGY_WEIGHTED_AVERAGE
    assert settings[KEY_DEMAND_STRATEGY] == DEMAND_STRATEGY_WEIGHTED_AVERAGE
    assert aggregator.calculate().demand == 72.0
    coordinator.plant_orchestrator._async_update_boiler.assert_awaited_once()
    select_ent.async_write_ha_state.assert_called_once()

    # Switch to sum_capped: min(100, 40 + 80) = 100.0%
    await select_ent.async_select_option(DEMAND_STRATEGY_SUM_CAPPED)
    assert select_ent.current_option == DEMAND_STRATEGY_SUM_CAPPED
    assert settings[KEY_DEMAND_STRATEGY] == DEMAND_STRATEGY_SUM_CAPPED
    assert aggregator.calculate().demand == 100.0

    # Invalid strategy should be ignored
    await select_ent.async_select_option("invalid_strategy_name")
    assert select_ent.current_option == DEMAND_STRATEGY_SUM_CAPPED


@pytest.mark.asyncio
async def test_demand_strategy_select_restore_and_removal():
    """Test restoration from persistent storage or last HA state on startup, plus removal."""
    aggregator = DemandAggregator()
    settings = {KEY_DEMAND_STRATEGY: DEMAND_STRATEGY_WEIGHTED_AVERAGE}

    coordinator = MagicMock()
    coordinator.zones = []
    coordinator.demand_aggregator = aggregator
    coordinator._settings = settings
    coordinator._select_entities = {}
    coordinator.get_persistent_data = lambda k, default=None: settings.get(k, default)
    coordinator.register_select = lambda k, ent: coordinator._select_entities.__setitem__(k, ent)

    select_ent = MultizoneDemandStrategySelect(coordinator, "entry_123")
    await select_ent.async_added_to_hass()
    assert aggregator.strategy == DEMAND_STRATEGY_WEIGHTED_AVERAGE
    assert coordinator._select_entities.get("demand_strategy") is select_ent

    await select_ent.async_will_remove_from_hass()
    assert "demand_strategy" not in coordinator._select_entities

    # Fallback to RestoreEntity.async_get_last_state when persistent storage has no key
    settings.clear()
    aggregator.strategy = DEMAND_STRATEGY_MAX
    select_ent2 = MultizoneDemandStrategySelect(coordinator, "entry_123")
    select_ent2.async_get_last_state = AsyncMock(
        return_value=SimpleNamespace(state=DEMAND_STRATEGY_SUM_CAPPED)
    )
    await select_ent2.async_added_to_hass()
    assert aggregator.strategy == DEMAND_STRATEGY_SUM_CAPPED


# =====================================================================
# 2. Phase 10 & Phase 8 — Dynamic Weather Curve & OpenTherm Telemetry
# =====================================================================


@pytest.mark.asyncio
async def test_opentherm_dynamic_weather_curve():
    """Test OpenThermBoilerBackend flow temperature with and without dynamic weather curve."""
    hass = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()

    states_map = {
        "climate.ot_boiler": State("climate.ot_boiler", "heat", {"temperature": 35.0}),
        "weather.home": State("weather.home", "sunny", {"temperature": 0.0}),
    }
    hass.states.get = lambda eid: states_map.get(eid)

    settings = {"weather_curve": 0.0}
    coordinator = MagicMock()
    coordinator.weather_sensor_id = "weather.home"
    coordinator.get_persistent_data = lambda k, default=0.0: settings.get(k, default)
    coordinator._thermal_models = {}
    coordinator.plant_diagnostics = None

    backend = OpenThermBoilerBackend(
        hass=hass,
        coordinator=coordinator,
        opentherm_entity="climate.ot_boiler",
        min_temp=35.0,
        max_temp=75.0,
    )

    # 1. With weather_curve = 0.0, 50% demand -> 35 + 0.5 * 40 = 55.0°C (unchanged)
    await backend.async_update(demand=50.0, peak_zone="Living", frost_emergency=False)
    hass.services.async_call.assert_any_call(
        "climate",
        "set_temperature",
        {"entity_id": "climate.ot_boiler", "temperature": 55.0},
        blocking=False,
    )

    # 2. With weather_curve = 2.0 and outdoor_temp = 0.0°C (delta_ext = 15.0):
    # weather_flow_offset = min(15.0, 15.0 * 2.0 * 0.5 * 1.0) = 15.0°C
    # target_temp = 55.0 + 15.0 = 70.0°C (within [35.0, 75.0])
    hass.services.async_call.reset_mock()
    settings["weather_curve"] = 2.0
    await backend.async_update(demand=50.0, peak_zone="Living", frost_emergency=False)
    hass.services.async_call.assert_any_call(
        "climate",
        "set_temperature",
        {"entity_id": "climate.ot_boiler", "temperature": 70.0},
        blocking=False,
    )

    # 3. Clamping to max_temp (75.0°C) when demand is 80% (base 67.0°C + 15.0°C -> 75.0°C)
    hass.services.async_call.reset_mock()
    await backend.async_update(demand=80.0, peak_zone="Living", frost_emergency=False)
    hass.services.async_call.assert_any_call(
        "climate",
        "set_temperature",
        {"entity_id": "climate.ot_boiler", "temperature": 75.0},
        blocking=False,
    )


def test_opentherm_diagnostics_hvac_action_flame_fallback():
    """Verify flame_active extraction from hvac_action on a climate OpenTherm entity."""
    hass = MagicMock()
    hass.data = {}
    coordinator = SimpleNamespace(opentherm_entity="climate.ot_gateway")

    # 1. hvac_action == "heating" -> flame_active is True
    hass.states.get = lambda eid: State(
        "climate.ot_gateway",
        "heat",
        {"current_temperature": 52.0, "hvac_action": "heating"},
    )
    diag = get_opentherm_diagnostics(coordinator, hass)
    assert diag["enabled"] is True
    assert diag["flow_temperature"] == 52.0
    assert diag["flame_active"] is True

    # 2. hvac_action == "idle" -> flame_active is False
    hass.states.get = lambda eid: State(
        "climate.ot_gateway",
        "heat",
        {"current_temperature": 40.0, "hvac_action": "idle"},
    )
    diag_idle = get_opentherm_diagnostics(coordinator, hass)
    assert diag_idle["flame_active"] is False


# =====================================================================
# 3. Phase 9 — Authoritative Hardware Climate Sync
# =====================================================================


def _make_event(entity_id: str, old_state: State, new_state: State, ctx_id: str) -> Event:
    ev = Event(
        "state_changed",
        data={"entity_id": entity_id, "old_state": old_state, "new_state": new_state},
    )
    ev.context = Context(id=ctx_id)
    return ev


@pytest.mark.asyncio
async def test_authoritative_sync_off_with_frost_setpoint_preserves_target_temp():
    """Physical wall thermostat turns OFF and reports 5.0°C -> virtual zone turns OFF
    without corrupting target_temperature (21.0°C), and demand/switches/valves shut down.
    """
    hass = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()

    trv_id = "climate.vimar_living"
    sw_id = "switch.living_actuator"
    valve_id = "number.living_valve"

    states_map = {
        trv_id: State(trv_id, HVACMode.HEAT, {ATTR_TEMPERATURE: 21.0, "current_temperature": 20.0}),
        sw_id: State(sw_id, "on", {}),
        valve_id: State(valve_id, "50.0", {}),
    }
    hass.states.get = lambda eid: states_map.get(eid)

    zones = [
        {
            CONF_ZONE_NAME: "Living",
            CONF_ZONE_CLIMATES: [trv_id],
            CONF_ZONE_SWITCHES: [sw_id],
            CONF_ZONE_VALVES: [valve_id],
            CONF_ZONE_TARGET_TEMP: 21.0,
            CONF_ZONE_WEIGHT: 1.5,
            CONF_ZONE_AUTHORITATIVE_SYNC: True,
        }
    ]
    aggregator = DemandAggregator(zones=zones)
    living_entity_id = make_zone_entity_id("Living")
    aggregator.set_zone_demand(living_entity_id, 65.0)

    coordinator = MagicMock()
    coordinator.zones = zones
    coordinator.boiler_switch = "switch.boiler"
    coordinator.demand_aggregator = aggregator
    coordinator.get_zone_mode = lambda cid: ZONE_MODE_PRIMARY
    coordinator.get_zone_demand = aggregator.get_zone_demand
    coordinator.set_zone_demand = aggregator.set_zone_demand
    coordinator.get_persistent_data = lambda k, default=True: True
    coordinator.get_global_preset = lambda: "comfort"
    coordinator.zone_manager = MagicMock()
    coordinator.calendar_manager = SimpleNamespace(temp_overrides={})
    coordinator.plant_diagnostics = MagicMock()
    coordinator.plant_diagnostics.get_zone_battery_level = lambda cid: None

    hass.data = {DOMAIN: {"entry_1": {"coordinator": coordinator}}}

    vt = MultizoneVirtualThermostat(hass=hass, entry_id="entry_1", zone_data=zones[0])
    vt.async_write_ha_state = MagicMock()
    vt._hvac_mode = HVACMode.HEAT
    vt._target_temperature = 21.0
    vt._sync_manager._local_pwm_state = True
    vt._sync_manager.init_known_targets()

    assert vt.extra_state_attributes["zone_weight"] == 1.5
    assert vt.extra_state_attributes["authoritative_climate_sync"] is True
    assert vt._sync_manager._last_known_trv_targets[trv_id] == 21.0

    # Physical thermostat switches to OFF and drops its reported setpoint to 5.0°C (frost protection)
    old_st = State(trv_id, HVACMode.HEAT, {ATTR_TEMPERATURE: 21.0})
    new_st = State(trv_id, HVACMode.OFF, {ATTR_TEMPERATURE: 5.0})
    states_map[trv_id] = new_st

    ev = _make_event(trv_id, old_st, new_st, "physical_wall_event")
    await vt._async_on_trv_changed(ev)

    # Virtual zone must be OFF, demand 0.0, PWM false, and target_temperature still 21.0°C!
    assert vt.hvac_mode == HVACMode.OFF
    assert vt.target_temperature == 21.0
    assert aggregator.get_zone_demand(living_entity_id) == 0.0
    assert vt._sync_manager.local_pwm_state is False
    assert vt._sync_manager._last_known_trv_targets[trv_id] == 21.0
    coordinator.zone_manager.update_preset_temperature.assert_not_called()

    # Switch must have been turned off and proportional valve closed to 0.0
    hass.services.async_call.assert_any_call(
        "switch",
        "turn_off",
        {"entity_id": sw_id},
        context=vt._sync_manager.internal_context,
    )
    hass.services.async_call.assert_any_call(
        "number",
        "set_value",
        {"entity_id": valve_id, "value": 0.0},
        context=vt._sync_manager.internal_context,
    )

    # Now physical thermostat turns back to HEAT at 21.0°C -> virtual zone turns HEAT with 21.0°C (no +16°C jump)
    old_st2 = new_st
    new_st2 = State(trv_id, HVACMode.HEAT, {ATTR_TEMPERATURE: 21.0})
    states_map[trv_id] = new_st2
    ev2 = _make_event(trv_id, old_st2, new_st2, "physical_wall_event_2")
    await vt._async_on_trv_changed(ev2)
    assert vt.hvac_mode == HVACMode.HEAT
    assert vt.target_temperature == 21.0


@pytest.mark.asyncio
async def test_sync_manager_idle_transitions_and_unavailable_reconnect():
    """Physical thermostat transitioning heat <-> idle or reconnecting from unavailable
    must not cause false OFF transitions or spurious temperature delta jumps.
    """
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.get_persistent_data = lambda k, default=True: True

    trv_id = "climate.wall_stat"
    sync_mgr = ZoneSyncManager(
        hass=hass,
        coordinator=coordinator,
        zone_name="Bedroom",
        entity_id="climate.multizone_thermostat_bedroom",
        climates=[trv_id],
        switches=[],
        calibrations={},
        authoritative_sync=True,
    )
    sync_mgr._last_known_trv_targets[trv_id] = 20.0

    # 1. heat -> idle (with same temperature 20.0): no mode change, no delta
    ev_heat_to_idle = _make_event(
        trv_id,
        State(trv_id, HVACMode.HEAT, {ATTR_TEMPERATURE: 20.0}),
        State(trv_id, "idle", {ATTR_TEMPERATURE: 20.0}),
        "ext_1",
    )
    mode, delta = await sync_mgr.process_trv_change(
        ev_heat_to_idle, None, HVACMode.HEAT, 5.0, 35.0
    )
    assert mode is None
    assert delta is None

    # 2. idle -> heat: no mode change, no delta
    ev_idle_to_heat = _make_event(
        trv_id,
        State(trv_id, "idle", {ATTR_TEMPERATURE: 20.0}),
        State(trv_id, HVACMode.HEAT, {ATTR_TEMPERATURE: 20.0}),
        "ext_2",
    )
    mode, delta = await sync_mgr.process_trv_change(
        ev_idle_to_heat, None, HVACMode.HEAT, 5.0, 35.0
    )
    assert mode is None
    assert delta is None

    # 3. Transition to unavailable -> ignored
    ev_to_unavail = _make_event(
        trv_id,
        State(trv_id, HVACMode.HEAT, {ATTR_TEMPERATURE: 20.0}),
        State(trv_id, STATE_UNAVAILABLE, {}),
        "ext_3",
    )
    mode, delta = await sync_mgr.process_trv_change(
        ev_to_unavail, None, HVACMode.HEAT, 5.0, 35.0
    )
    assert mode is None
    assert delta is None

    # 4. Reconnect from unavailable -> heat (even if temperature differs): updates baseline without delta jump
    ev_from_unavail = _make_event(
        trv_id,
        State(trv_id, STATE_UNAVAILABLE, {}),
        State(trv_id, HVACMode.HEAT, {ATTR_TEMPERATURE: 22.0}),
        "ext_4",
    )
    mode, delta = await sync_mgr.process_trv_change(
        ev_from_unavail, None, HVACMode.HEAT, 5.0, 35.0
    )
    assert mode is None
    assert delta is None
    assert sync_mgr._last_known_trv_targets[trv_id] == 22.0

    # 5. Authoritative reconnect from unavailable -> off while master is HEAT -> reconciles master to OFF
    ev_unavail_to_off = _make_event(
        trv_id,
        State(trv_id, STATE_UNKNOWN, {}),
        State(trv_id, HVACMode.OFF, {ATTR_TEMPERATURE: 5.0}),
        "ext_5",
    )
    mode, delta = await sync_mgr.process_trv_change(
        ev_unavail_to_off, None, HVACMode.HEAT, 5.0, 35.0
    )
    assert mode == HVACMode.OFF
    assert delta is None
    # Pre-OFF baseline (22.0°C) is preserved despite 5.0°C frost setpoint
    assert sync_mgr._last_known_trv_targets[trv_id] == 22.0
