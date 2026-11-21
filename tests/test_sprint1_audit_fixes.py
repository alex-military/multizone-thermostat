"""Regression tests for Sprint 1 audit fixes (crashes and plant/generator safety)."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.climate import HVACMode
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE

from custom_components.multizone_thermostat import _async_register_services
from custom_components.multizone_thermostat.boiler.flow_curve import (
    EMITTER_UNDERFLOOR,
    UNDERFLOOR_MAX_FLOW_TEMP,
)
from custom_components.multizone_thermostat.boiler.heat_pump_backend import CentralHeatPumpBackend
from custom_components.multizone_thermostat.boiler.opentherm_backend import OpenThermBoilerBackend
from custom_components.multizone_thermostat.boiler.plant_orchestrator import PlantOrchestrator
from custom_components.multizone_thermostat.boiler.relay_backend import RelayBoilerBackend
from custom_components.multizone_thermostat.config_flow.schemas import (
    get_boiler_relay_schema,
    get_options_boiler_relay_schema,
)
from custom_components.multizone_thermostat.const import (
    CONF_HAS_MIXING_VALVE,
    CONF_ZONE_EMITTER_TYPE,
    CONF_ZONE_HUMIDITY_SENSOR,
    CONF_ZONE_NAME,
    CONF_ZONE_SPLIT_CLIMATE,
    CONF_ZONE_SPLIT_ROLE,
    CONF_ZONE_SPLIT_SOLAR_PRIORITY,
    CONF_ZONE_TEMP_SENSOR,
    CONF_ZONES,
    DOMAIN,
    EMITTER_TYPE_RADIATOR,
    HP_TYPE_CLIMATE,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    MODE_RELAY,
    SPLIT_ROLE_HEAT_COOL,
    ZONE_MODE_PRIMARY,
    make_zone_entity_id,
)
from custom_components.multizone_thermostat.coordinator import MultizoneCoordinator
from custom_components.multizone_thermostat.demand_aggregator import DemandAggregator
from custom_components.multizone_thermostat.diagnostics import async_get_config_entry_diagnostics
from custom_components.multizone_thermostat.master_controller import MasterController
from custom_components.multizone_thermostat.plant_config import PlantConfig
from custom_components.multizone_thermostat.safety.anti_seize import AntiSeizeManager
from custom_components.multizone_thermostat.split.split_controller import SplitZoneManager
from custom_components.multizone_thermostat.sync_manager import ZoneSyncManager
from custom_components.multizone_thermostat.zone_controller import ZoneController


# ---------------------------------------------------------------------------
# 1. Crash fixes (CRIT-01 .. CRIT-04)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_crit01_diagnostics_real_zone_controller_pids_cool_property():
    """CRIT-01: async_get_config_entry_diagnostics must read ZoneController.pids_cool without calling dict()."""
    hass = MagicMock()
    hass.states.get.return_value = None
    entry = MagicMock()
    entry.entry_id = "entry_diag_1"
    entry.version = 1
    entry.domain = DOMAIN
    entry.title = "Test"
    entry.data = {
        CONF_ZONES: [{CONF_ZONE_NAME: "Salotto", CONF_ZONE_TEMP_SENSOR: "sensor.t_salotto"}],
    }
    entry.options = {}

    coord = MultizoneCoordinator(hass, entry)
    coord.zone_controller = ZoneController(hass, coord)
    assert isinstance(coord.zone_controller.pids_cool, dict)
    hass.data = {DOMAIN: {entry.entry_id: {"coordinator": coord}}}

    result = await async_get_config_entry_diagnostics(hass, entry)
    cid = make_zone_entity_id("Salotto")
    assert cid in result["zones"]
    assert "pid_parameters_cool" in result["zones"][cid]


def test_crit02_boiler_relay_schemas_define_has_mixing_valve():
    """CRIT-02: Relay schemas must accept and expose CONF_HAS_MIXING_VALVE without NameError."""
    s1 = get_boiler_relay_schema()
    keys1 = {getattr(k, "schema", k) for k in s1.schema}
    assert CONF_HAS_MIXING_VALVE in keys1

    s2 = get_options_boiler_relay_schema("switch.boiler", None, has_mixing_valve=True)
    keys2 = {getattr(k, "schema", k) for k in s2.schema}
    assert CONF_HAS_MIXING_VALVE in keys2
    validated = s2({"boiler_switch": "switch.boiler"})
    assert validated[CONF_HAS_MIXING_VALVE] is True


@pytest.mark.asyncio
async def test_crit03_service_set_master_operation_mode_works():
    """CRIT-03: set_master_operation_mode handler must import HVAC_MODE_HEAT/COOL and execute cleanly."""
    registered = {}

    def _capture(domain, service, handler, schema=None):
        registered[service] = handler

    hass = MagicMock()
    hass.services.async_register = MagicMock(side_effect=_capture)
    coord = MagicMock()
    coord.async_set_master_hvac_mode = AsyncMock()
    hass.data = {DOMAIN: {"entry_1": {"coordinator": coord}}}

    await _async_register_services(hass)
    handler = registered["set_master_operation_mode"]

    await handler(SimpleNamespace(data={"operation_mode": HVAC_MODE_COOL}))
    coord.async_set_master_hvac_mode.assert_awaited_once_with(HVAC_MODE_COOL)


def test_crit04_coordinator_pid_unlock_storage_key_with_climate_entity_id():
    """CRIT-04: _pid_unlock_storage_key must work when passed a climate.* entity ID."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "entry_pid_key"
    entry.data = {CONF_ZONES: [{CONF_ZONE_NAME: "Salotto"}]}
    entry.options = {}

    coord = MultizoneCoordinator(hass, entry)
    cid = make_zone_entity_id("Salotto")
    assert coord._pid_unlock_storage_key(cid) == "pid_manual_unlock_salotto"


# ---------------------------------------------------------------------------
# 2. Split Controller fixes (CRIT-05, #12.5, #12.10)
# ---------------------------------------------------------------------------


def test_crit05_split_frost_emergency_via_real_frost_manager_and_coordinator():
    """CRIT-05: Split hydronic suppression must stop when coordinator.frost_manager reports frost emergency."""
    cid = make_zone_entity_id("Salotto")
    states = {"climate.split_salotto": SimpleNamespace(state=HVAC_MODE_HEAT, attributes={})}
    hass = MagicMock()
    hass.states.get = MagicMock(side_effect=lambda eid: states.get(eid))

    coord = MagicMock(spec=["zones", "get_master_state", "get_persistent_data", "frost_manager"])
    coord.zones = [
        {
            CONF_ZONE_NAME: "Salotto",
            CONF_ZONE_SPLIT_CLIMATE: "climate.split_salotto",
            CONF_ZONE_SPLIT_ROLE: SPLIT_ROLE_HEAT_COOL,
        }
    ]
    coord.get_master_state.return_value = False  # Vacation / Master OFF
    coord.get_persistent_data.side_effect = lambda k, d=None: d
    coord.frost_manager = MagicMock()
    coord.frost_manager.is_zone_in_frost_emergency = MagicMock(return_value=True)

    mgr = SplitZoneManager(hass, coord)
    mgr._split_active_states[cid] = True

    assert mgr.should_suppress_hydronic_demand(cid) is False


@pytest.mark.asyncio
async def test_split_off_zone_and_failsafe_no_loop_and_manual_off_cache():
    """Verify split stays OFF on OFF zone (#12.5), doesn't loop fail-safe (#12.10), and updates cache."""
    cid = make_zone_entity_id("Salotto")
    split_state = SimpleNamespace(state=HVAC_MODE_OFF, attributes={})
    hass = MagicMock()
    hass.states.get = MagicMock(return_value=split_state)
    hass.services.async_call = AsyncMock()
    hass.async_create_task = MagicMock(side_effect=lambda coro: coro.close())

    coord = MagicMock()
    coord.zones = [
        {
            CONF_ZONE_NAME: "Salotto",
            CONF_ZONE_SPLIT_CLIMATE: "climate.split_salotto",
            CONF_ZONE_SPLIT_ROLE: SPLIT_ROLE_HEAT_COOL,
            CONF_ZONE_SPLIT_SOLAR_PRIORITY: True,
        }
    ]
    coord.get_master_state.return_value = True
    coord.frost_manager = None
    coord.is_zone_in_frost_emergency.return_value = False
    coord.get_persistent_data.side_effect = lambda k, d=None: d

    mgr = SplitZoneManager(hass, coord)

    # #12.5: Zone HVACMode.OFF must NOT turn split ON in HEAT even during solar surplus
    mode, target, is_heat = mgr.evaluate_split_state(
        climate_id=cid,
        current_temp=17.0,
        target_temp=21.0,
        zone_hvac_mode=HVAC_MODE_OFF,
        solar_surplus=True,
    )
    assert mode == HVAC_MODE_OFF
    assert is_heat is False

    # #12.10a: Fail-safe latches past 30s and does NOT re-suppress after retry while split stays OFF
    mgr._split_active_states[cid] = True
    mgr._last_split_commands[cid] = {"mode": HVAC_MODE_HEAT, "target": 21.0}
    mgr._last_command_timestamps[cid] = 100.0
    with patch("time.monotonic", return_value=135.0):
        assert mgr.should_suppress_hydronic_demand(cid) is False

    # Retry sends HEAT at t=136 and updates _last_command_timestamps, while split remains OFF
    with patch("time.monotonic", return_value=136.0):
        await mgr.async_sync_split(cid, HVAC_MODE_HEAT, 21.0)
    with patch("time.monotonic", return_value=137.0):
        assert mgr.should_suppress_hydronic_demand(cid) is False

    # Once split actually confirms HEAT, fail-safe clears
    split_state.state = HVAC_MODE_HEAT
    with patch("time.monotonic", return_value=138.0):
        assert mgr.should_suppress_hydronic_demand(cid) is True

    # #12.10b: set_local_manual_on(False) updates command cache to OFF so next HEAT call sends service
    mgr.set_local_manual_on(cid, False)
    assert mgr._last_split_commands[cid] == {"mode": HVAC_MODE_OFF, "target": None}
    hass.services.async_call.reset_mock()
    await mgr.async_sync_split(cid, HVAC_MODE_HEAT, 21.0)
    assert hass.services.async_call.await_count >= 1


# ---------------------------------------------------------------------------
# 3. Heat Pump Backend fixes (CRIT-06, CRIT-08 part 1, #12.13, #12.15)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_crit06_heat_pump_underfloor_clamp_without_outdoor_temp_and_lifecycle():
    """CRIT-06/#12.13/#12.15: Clamps <= 40°C with no weather sensor, clears HOLD_*, tracks activity."""
    hass = MagicMock()
    hass.states.get.return_value = SimpleNamespace(state=STATE_OFF, attributes={})
    hass.services.async_call = AsyncMock()
    hass.config.units.temperature_unit = "°C"

    coord = MagicMock()
    coord.weather_sensor_id = None
    coord.has_mixing_valve = False
    coord.zones = [{CONF_ZONE_NAME: "Living Room", CONF_ZONE_EMITTER_TYPE: EMITTER_UNDERFLOOR}]
    coord.get_persistent_data.side_effect = lambda k, d=None: d
    coord._min_cycle_on = 5.0
    coord._min_cycle_off = 5.0

    hp = CentralHeatPumpBackend(
        hass=hass,
        coordinator=coord,
        hp_type=HP_TYPE_CLIMATE,
        hp_entity="climate.hp",
        min_temp=25.0,
        max_temp=55.0,
        valve_delay=0.0,
    )

    # Without outdoor sensor, 100% demand on underfloor direct MUST stay <= 40.0°C and reset activity
    await hp.async_update(100.0, make_zone_entity_id("Living Room"), False, hvac_mode=HVAC_MODE_HEAT)
    set_temp_calls = [
        c for c in hass.services.async_call.call_args_list if c[0][1] == "set_temperature"
    ]
    assert set_temp_calls
    assert set_temp_calls[-1][0][2]["temperature"] <= UNDERFLOOR_MAX_FLOW_TEMP
    coord.reset_last_active_time.assert_called()

    # #12.13: Entering HOLD_ON then clearing after min_cycle_on must update status_reason away from HOLD_ON
    with patch("time.monotonic", return_value=1000.0):
        hp._last_switch_time = 950.0
        hp._current_running_state = True
        await hp.async_update(0.0, None, False, hvac_mode=HVAC_MODE_HEAT)
        assert hp.status_reason.startswith("HOLD_ON")

    with patch("time.monotonic", return_value=1400.0):
        await hp.async_update(0.0, None, False, hvac_mode=HVAC_MODE_HEAT)
        assert hp.status_reason == "OFF - No Demand"

    # async_emergency_off preserves non-zero _last_switch_time when shutting down an active HP
    hp._current_running_state = True
    with patch("time.monotonic", return_value=2000.0):
        await hp.async_emergency_off()
    assert hp._last_switch_time == 2000.0
    assert hp.status_reason == "OFF - Emergency/Master OFF"

    # #12.15: Dew point climate fallback matches "Living Room" via make_zone_entity_id
    c_ent = SimpleNamespace(current_temperature=24.0, current_humidity=60.0)
    coord._climate_entities = {make_zone_entity_id("Living Room"): c_ent}
    coord.zones = [{CONF_ZONE_NAME: "Living Room", CONF_ZONE_HUMIDITY_SENSOR: None}]
    safe_min = hp._calculate_safe_cooling_min_temp()
    assert safe_min > hp.cool_min_temp


# ---------------------------------------------------------------------------
# 4. Plant Orchestrator + Relay + Anti-Seize + DemandAggregator (CRIT-07/08/09)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_crit07_heat_to_cool_releases_relay_hold_on_and_blocks_hp_while_boiler_on():
    """CRIT-07: Transition HEAT->COOL must ignore relay HOLD_ON and block HP cooling while gas is ON."""
    boiler_state = SimpleNamespace(state=STATE_ON, attributes={})
    hass = MagicMock()
    hass.states.get = MagicMock(side_effect=lambda eid: boiler_state if eid == "switch.boiler" else None)
    hass.services.async_call = AsyncMock()

    coord = MagicMock()
    coord.zones = []
    coord.get_master_state.return_value = True
    coord.enable_gas_heater = True
    coord.enable_heat_pump = True
    coord.heat_pump_cooling = True
    coord.is_dhw_active = False
    coord.frost_manager = None
    coord.energy_manager = None
    coord.plant_diagnostics = None
    coord._climate_callbacks = {}
    coord.master_hvac_mode = HVAC_MODE_COOL

    relay = RelayBoilerBackend(hass, coord, "switch.boiler", min_cycle_on=10.0, min_cycle_off=5.0, valve_delay=0.0)
    relay._last_boiler_change = 990.0
    relay._last_known_boiler_on = True

    hp = MagicMock()
    hp.async_update = AsyncMock()
    hp.async_emergency_off = AsyncMock()

    zone_ent = MagicMock(hvac_mode=HVAC_MODE_COOL, current_temperature=27.0, target_temperature=24.0)
    coord._climate_entities = {"climate.salotto": zone_ent}
    coord.get_zone_mode.return_value = ZONE_MODE_PRIMARY
    coord.split_manager = None

    agg = MagicMock()
    orch = PlantOrchestrator(hass, agg, relay, coord, heat_pump_backend=hp)

    with patch("time.monotonic", return_value=1000.0):
        await orch._async_update_boiler()

    # Relay boiler receives turn_off despite min_cycle_on not elapsed; HP cooling blocked while switch still ON
    turn_off_calls = [c for c in hass.services.async_call.call_args_list if c[0][1] == "turn_off"]
    assert turn_off_calls
    hp.async_update.assert_awaited_once_with(0.0, None, False, hvac_mode=HVAC_MODE_COOL)


@pytest.mark.asyncio
async def test_plant_orchestrator_disabling_hp_turns_off_running_hp_and_interrupts_antiseize():
    """#12.8 & CRIT-08: Disabling enable_heat_pump turns off running HP; frost interrupts anti-seize."""
    hass = MagicMock()
    coord = MagicMock()
    coord.get_master_state.return_value = True
    coord.master_hvac_mode = HVAC_MODE_HEAT
    coord.enable_gas_heater = True
    coord.enable_heat_pump = False  # Disabled at runtime while HP is running
    coord.frost_manager = None
    coord.energy_manager = None
    coord._climate_callbacks = {}

    agg_res = MagicMock(demand=50.0, peak_zone="Salotto")
    agg = MagicMock()
    agg.calculate.return_value = agg_res

    boiler = MagicMock()
    boiler.async_update = AsyncMock()
    hp = MagicMock()
    hp._current_running_state = True
    hp.async_update = AsyncMock()
    hp.async_emergency_off = AsyncMock()

    orch = PlantOrchestrator(hass, agg, boiler, coord, heat_pump_backend=hp)
    await orch._async_update_boiler()
    hp.async_emergency_off.assert_awaited_once()

    # Frost emergency interrupts active anti-seize during async_tick
    anti_seize = MagicMock()
    anti_seize.is_running = True
    anti_seize.stop = MagicMock()
    coord.anti_seize_manager = anti_seize
    coord.frost_manager = MagicMock()
    coord.frost_manager.async_handle_frost_emergencies = AsyncMock(return_value=True)
    orch._async_update_boiler = AsyncMock()

    await orch.async_tick(MagicMock())
    anti_seize.stop.assert_called_once()
    orch._async_update_boiler.assert_awaited_once()


def test_crit08_anti_seize_defers_for_dhw_frost_and_cooling():
    """CRIT-08: AntiSeizeManager must defer during DHW, frost emergency, or active cooling."""
    hass = MagicMock()
    hass.async_create_task = MagicMock()

    coord = MagicMock()
    coord.zones = [{CONF_ZONE_NAME: "Salotto"}]
    coord.get_persistent_data.side_effect = lambda k, d=None: True if k == "anti_seize_enabled" else d
    coord.last_active_time = 0.0
    coord.is_zone_in_frost_emergency.return_value = False
    coord.frost_manager = None

    mgr = AntiSeizeManager(hass, coord)

    with patch("time.monotonic", return_value=20 * 86400.0):
        # 1. DHW active -> defer
        coord.is_dhw_active = True
        coord.master_hvac_mode = HVAC_MODE_HEAT
        mgr.check_anti_seize()
        hass.async_create_task.assert_not_called()

        # 2. Frost emergency active -> defer
        coord.is_dhw_active = False
        coord.is_zone_in_frost_emergency.return_value = True
        mgr.check_anti_seize()
        hass.async_create_task.assert_not_called()

        # 3. Cooling active -> defer
        coord.is_zone_in_frost_emergency.return_value = False
        coord.master_hvac_mode = HVAC_MODE_COOL
        coord.get_master_state.return_value = True
        mgr.check_anti_seize()
        hass.async_create_task.assert_not_called()


def test_crit09_and_demand_aggregator_unregister():
    """CRIT-09/#9.3: Frost emergency overrides DHW priority, and unregister_on_demand_changed works cleanly."""
    agg = DemandAggregator()
    z1 = agg.register_zone("Living", mode=ZONE_MODE_PRIMARY)
    agg.set_zone_demand(z1, 0.0)

    cb = MagicMock()
    agg.register_on_demand_changed(cb)
    agg.set_zone_demand(z1, 40.0)
    cb.assert_called_once_with(z1, 40.0)

    cb.reset_mock()
    agg.unregister_on_demand_changed(cb)
    agg.set_zone_demand(z1, 80.0)
    cb.assert_not_called()

    # Frost + DHW simultaneous -> Frost wins!
    res = agg.calculate(is_dhw_active=True, frost_emergency=True)
    assert res.frost_emergency is True
    assert res.demand == 100.0
    assert res.peak_zone == "Frost Emergency"


# ---------------------------------------------------------------------------
# 5. Relay, OpenTherm, SyncManager, MasterController & PlantConfig fixes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_relay_backend_unavailable_blip_and_frost_bypasses_min_off():
    """#12.6/#12.7/#12.17: Unavailable blip won't reset change ts; frost bypasses min_cycle_off."""
    st = SimpleNamespace(state=STATE_ON)
    hass = MagicMock()
    hass.states.get = MagicMock(return_value=st)
    hass.services.async_call = AsyncMock()

    coord = MagicMock()
    coord.zones = [{"zone_name": "Legacy Room"}]  # legacy key, no CONF_ZONE_NAME
    relay = RelayBoilerBackend(hass, coord, "switch.boiler", min_cycle_on=5.0, min_cycle_off=5.0, valve_delay=0.0)
    relay._last_known_boiler_on = True
    relay._last_boiler_change = 100.0
    relay._pending_command = ("off", 105.0)

    # Blip to unavailable while pending off -> must NOT clear _pending_command or reset _last_boiler_change
    st.state = STATE_UNAVAILABLE
    with patch("time.monotonic", return_value=110.0):
        await relay.async_update(100.0, "Legacy Room", False)
    assert relay._last_known_boiler_on is True
    assert relay._last_boiler_change == 100.0
    assert relay._pending_command == ("off", 105.0)

    # Recovery back to STATE_ON after blip must NOT reset _last_boiler_change either
    st.state = STATE_ON
    with patch("time.monotonic", return_value=112.0):
        await relay.async_update(100.0, "Legacy Room", False)
    assert relay._last_known_boiler_on is True
    assert relay._last_boiler_change == 100.0

    # Return to STATE_OFF clears pending off cleanly; then frost_emergency bypasses min_cycle_off
    st.state = STATE_OFF
    with patch("time.monotonic", return_value=115.0):
        await relay.async_update(0.0, None, False)
    assert relay._pending_command is None
    assert relay._last_known_boiler_on is False
    assert relay._last_boiler_change == 100.0

    with patch("time.monotonic", return_value=120.0):  # Only 20s elapsed < 300s min_cycle_off
        await relay.async_update(100.0, "Frost Emergency", True)
    turn_on_calls = [c for c in hass.services.async_call.call_args_list if c[0][1] == "turn_on"]
    assert len(turn_on_calls) == 1


@pytest.mark.asyncio
async def test_opentherm_unavailable_ch_switch_and_entity_confirmation():
    """#12.11/#12.16: Number mode drops setpoint when ch_switch unavailable; command confirms via entity."""
    states = {
        "number.ot_flow": SimpleNamespace(state="50.0", attributes={"min": 0.0}),
        "switch.ch_enable": SimpleNamespace(state=STATE_UNAVAILABLE, attributes={}),
    }
    hass = MagicMock()
    hass.states.get = MagicMock(side_effect=lambda eid: states.get(eid))
    hass.services.async_call = AsyncMock()

    coord = MagicMock()
    coord.plant_diagnostics = None
    ot = OpenThermBoilerBackend(hass, coord, "number.ot_flow", 35.0, 75.0, ch_switch="switch.ch_enable")

    await ot.async_update(0.0, None, False)
    set_vals = [c[0][2]["value"] for c in hass.services.async_call.call_args_list if c[0][1] == "set_value"]
    assert set_vals == [0.0]
    turn_offs = [c for c in hass.services.async_call.call_args_list if c[0][1] == "turn_off"]
    assert len(turn_offs) == 1

    # #12.16: Climate entity state "heat" clears _pending_command even when flame_active is False
    ot_climate = OpenThermBoilerBackend(hass, coord, "climate.ot", 35.0, 75.0)
    ot_climate._pending_command = ("on", 100.0)
    states["climate.ot"] = SimpleNamespace(state=HVAC_MODE_HEAT, attributes={"temperature": 55.0})
    diag = MagicMock()
    diag._current_boiler_start = None
    diag.get_opentherm_diagnostics.return_value = {"flame_active": False}
    coord.plant_diagnostics = diag

    with patch("time.monotonic", return_value=110.0):
        await ot_climate.async_update(50.0, "Living", False)
    assert ot_climate._pending_command is None
    diag.record_boiler_state.assert_not_called()  # burner flame still False


@pytest.mark.asyncio
async def test_sync_manager_blocks_radiator_hydronic_cooling():
    """#14.6: Radiator switches and proportional valves stay OFF / 0.0 during central cooling."""
    hass = MagicMock()
    hass.states.get.return_value = SimpleNamespace(state=STATE_ON, attributes={})
    hass.services.async_call = AsyncMock()

    coord = MagicMock()
    coord.get_master_state.return_value = True
    coord.get_zone_mode.return_value = ZONE_MODE_PRIMARY
    coord.get_zone_demand.return_value = 80.0
    coord.enable_heat_pump = True
    coord.heat_pump_cooling = True
    coord.weather_sensor_id = None
    coord._climate_entities = {}

    sync = ZoneSyncManager(
        hass=hass,
        coordinator=coord,
        entity_id="climate.multizone_thermostat_salotto",
        zone_name="Salotto",
        climates=[],
        switches=["switch.rad_salotto"],
        calibrations={},
        valves=["number.valve_salotto"],
        emitter_type=EMITTER_TYPE_RADIATOR,
    )
    sync._local_pwm_state = True
    await sync.async_pwm_tick(HVACMode.COOL)
    assert sync._local_pwm_state is False

    await sync.async_sync_proportional_valves(HVACMode.COOL)
    valve_calls = [c for c in hass.services.async_call.call_args_list if c[0][0] == "number"]
    assert valve_calls and valve_calls[-1][0][2]["value"] == 0.0


@pytest.mark.asyncio
async def test_master_controller_and_plant_config_null_guards():
    """#14.8/#12.17: MasterController handles plant_orchestrator=None; PlantConfig handles None floats."""
    hass = MagicMock()
    coord = MagicMock()
    coord.hass = hass
    coord.zones = [{"zone_name": "Legacy"}]
    coord.heat_pump_backend = None
    coord.plant_orchestrator = None

    mc = MasterController(coord)
    mc.async_set_hvac_mode = AsyncMock()
    await mc.async_apply_master_off()
    mc.async_set_hvac_mode.assert_awaited_once_with(make_zone_entity_id("Legacy"), HVAC_MODE_OFF)

    entry = SimpleNamespace(
        data={
            "boiler_mode": MODE_RELAY,
            "opentherm_min_temp": None,
            "opentherm_max_temp": "",
            "heat_pump_min_temp": None,
            "solar_export_threshold": None,
            "min_cycle_on": None,
        },
        options={},
    )
    cfg = PlantConfig.from_entry(entry)
    assert cfg.opentherm_min_temp == 35.0
    assert cfg.opentherm_max_temp == 75.0
    assert cfg.heat_pump_min_temp == 25.0
    assert cfg.solar_export_threshold == 500.0
    assert cfg.min_cycle_on == 5.0
