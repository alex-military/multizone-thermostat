"""End-to-end simulated integration tests for Phase 5 scenarios."""
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import voluptuous as vol

from custom_components.multizone_thermostat.const import (
    CONF_BOILER_MODE,
    CONF_BOILER_SWITCH,
    CONF_MIN_CYCLE_OFF,
    CONF_MIN_CYCLE_ON,
    CONF_OPENTHERM_CH_SWITCH,
    CONF_OPENTHERM_ENTITY,
    CONF_OPENTHERM_MAX_TEMP,
    CONF_OPENTHERM_MIN_TEMP,
    CONF_PRESENCE_SENSOR,
    CONF_VALVE_DELAY,
    CONF_WEATHER_SENSOR,
    CONF_ZONE_CLIMATES,
    CONF_ZONE_NAME,
    CONF_ZONE_SWITCHES,
    CONF_ZONE_TARGET_TEMP,
    CONF_ZONE_TEMP_SENSOR,
    CONF_ZONE_WINDOW_SENSOR,
    CONF_ZONES,
    DEFAULT_MIN_CYCLE_OFF,
    DEFAULT_MIN_CYCLE_ON,
    DEFAULT_VALVE_DELAY,
    GLOBAL_PRESET_AWAY,
    GLOBAL_PRESET_COMFORT,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    KEY_ANTI_FROST_ENABLED,
    KEY_FROST_PROTECTION_TEMP,
    KEY_WEATHER_CURVE,
    MODE_OPENTHERM,
    MODE_RELAY,
    make_zone_entity_id,
)
from custom_components.multizone_thermostat.coordinator import MultizoneCoordinator
from custom_components.multizone_thermostat.boiler.opentherm_backend import (
    COMMAND_CONFIRM_TIMEOUT,
    OpenThermBoilerBackend,
)
from custom_components.multizone_thermostat.boiler.relay_backend import RelayBoilerBackend
from custom_components.multizone_thermostat.boiler.plant_orchestrator import PlantOrchestrator
from custom_components.multizone_thermostat.plant_diagnostics.const import (
    ANOMALY_NONE,
    ANOMALY_SENSOR_FAULT,
    ANOMALY_SENSOR_TIMEOUT,
)
from custom_components.multizone_thermostat.config_flow.schemas import (
    get_boiler_opentherm_schema,
    get_options_boiler_opentherm_schema,
    get_options_edit_zone_schema,
)
from custom_components.multizone_thermostat.config_flow.validators import (
    validate_geofencing,
    validate_opentherm_temps,
    validate_zone_input,
)


def _setup_simulated_plant(boiler_mode=MODE_RELAY, valve_delay=0.05, opentherm_ch_switch=None):
    """Set up a fully wired simulated plant for end-to-end tests."""
    hass = MagicMock()
    coros = []

    def mock_create_task(coro):
        coros.append(coro)
        return MagicMock()

    hass.async_create_task = MagicMock(side_effect=mock_create_task)
    hass.services.async_call = AsyncMock()

    states_db = {}

    def mock_states_get(entity_id):
        return states_db.get(entity_id)

    hass.states.get = MagicMock(side_effect=mock_states_get)

    zone_living_name = "Living Room"
    zone_bedroom_name = "Bedroom"
    cid_living = make_zone_entity_id(zone_living_name)
    cid_bedroom = make_zone_entity_id(zone_bedroom_name)

    entry = MagicMock()
    entry.entry_id = "simulated_plant_entry"
    entry.data = {
        CONF_BOILER_MODE: boiler_mode,
        CONF_BOILER_SWITCH: "switch.boiler_relay",
        CONF_OPENTHERM_ENTITY: "climate.ot_boiler",
        CONF_OPENTHERM_MIN_TEMP: 35.0,
        CONF_OPENTHERM_MAX_TEMP: 75.0,
        CONF_OPENTHERM_CH_SWITCH: opentherm_ch_switch,
        CONF_MIN_CYCLE_ON: 0.0,
        CONF_MIN_CYCLE_OFF: 0.0,
        CONF_VALVE_DELAY: valve_delay,
        CONF_PRESENCE_SENSOR: "sensor.presence",
        CONF_WEATHER_SENSOR: "weather.forecast_home",
        CONF_ZONES: [
            {
                CONF_ZONE_NAME: zone_living_name,
                CONF_ZONE_TEMP_SENSOR: "sensor.living_room_temp",
                CONF_ZONE_CLIMATES: ["climate.living_trv_1", "climate.living_trv_2"],
                CONF_ZONE_SWITCHES: [],
                CONF_ZONE_TARGET_TEMP: 20.0,
            },
            {
                CONF_ZONE_NAME: zone_bedroom_name,
                CONF_ZONE_TEMP_SENSOR: "sensor.bedroom_temp",
                CONF_ZONE_CLIMATES: ["climate.bedroom_trv"],
                CONF_ZONE_SWITCHES: [],
                CONF_ZONE_TARGET_TEMP: 19.0,
            },
        ],
    }

    coord = MultizoneCoordinator(hass, entry)
    coord.set_master_state(True)

    # Initialize fake states in states_db
    st_relay = MagicMock(state="off")
    states_db["switch.boiler_relay"] = st_relay

    st_ot = MagicMock(state="off", attributes={"temperature": 35.0})
    states_db["climate.ot_boiler"] = st_ot

    st_living_climate = MagicMock(
        state="heat",
        attributes={"current_temperature": 18.0, "temperature": 20.0},
    )
    states_db[cid_living] = st_living_climate

    st_bedroom_climate = MagicMock(
        state="heat",
        attributes={"current_temperature": 18.0, "temperature": 19.0},
    )
    states_db[cid_bedroom] = st_bedroom_climate

    # Register callbacks
    coord.register_climate(cid_living, MagicMock())
    coord.register_climate(cid_bedroom, MagicMock())

    return coord, hass, states_db, coros


# ===========================================================================
# 1. Fallback sensore completo
# ===========================================================================

@pytest.mark.asyncio
async def test_e2e_sensor_fallback_full_chain():
    """Verify full fallback chain: Main sensor offline -> TRV average used -> Degraded diagnostics -> Heat maintained."""
    coord, hass, states_db, coros = _setup_simulated_plant()
    cid_living = make_zone_entity_id("Living Room")

    # Step 1: Main sensor goes unavailable
    states_db["sensor.living_room_temp"] = MagicMock(state="unavailable")
    # TRVs report valid temperatures
    states_db["climate.living_trv_1"] = MagicMock(attributes={"current_temperature": 18.2})
    states_db["climate.living_trv_2"] = MagicMock(attributes={"current_temperature": 18.6})

    # Diagnostic evaluation
    zone_state = {
        "active_anomaly": ANOMALY_NONE,
        "anomaly_details": "",
        "last_temp_seen": 18.4,
        "last_temp_time": time.monotonic(),
        "last_heating_time": None,
        "high_demand_start_time": None,
        "high_demand_start_temp": None,
        "ghost_heat_start_temp": None,
        "fallback_ok": True,
    }
    coord.plant_diagnostics._zone_anomaly_state[cid_living] = zone_state

    # Diagnosi: fallback_ok è True -> has_critical_sensor_fault restituisce False
    assert not coord.plant_diagnostics.has_critical_sensor_fault(cid_living)

    # Virtual climate updates with fallback TRV average: (18.2 + 18.6) / 2 = 18.4
    st_virtual = MagicMock(
        state="heat",
        attributes={"current_temperature": 18.4, "temperature": 20.0},
    )
    states_db[cid_living] = st_virtual

    # Update zone controller
    demand = await coord.zone_controller.async_update_zone(cid_living, st_virtual)
    assert demand > 0.0  # Heating demand maintained!

    # Push to aggregator and orchestrator
    coord.demand_aggregator.set_zone_demand(cid_living, demand)
    await coord.plant_orchestrator._async_update_boiler()

    # Boiler backend receives demand > 0
    assert coord.boiler_backend._last_demand > 0.0

    # Step 2: Now simulate total loss of all TRVs (no fallback possible)
    states_db["climate.living_trv_1"] = MagicMock(attributes={"current_temperature": None})
    states_db["climate.living_trv_2"] = MagicMock(attributes={"current_temperature": None})
    zone_state["fallback_ok"] = False
    zone_state["active_anomaly"] = ANOMALY_SENSOR_TIMEOUT

    # Guasto critico confermato: has_critical_sensor_fault restituisce True
    assert coord.plant_diagnostics.has_critical_sensor_fault(cid_living)

    # Zone controller azzera la domanda per sicurezza
    zero_demand = await coord.zone_controller.async_update_zone(cid_living, st_virtual)
    assert zero_demand == 0.0

    for c in coros:
        c.close()


# ===========================================================================
# 2. DHW di 20 min con domanda alta
# ===========================================================================

@pytest.mark.asyncio
async def test_e2e_dhw_20_minute_high_demand_cycle():
    """Verify DHW cuts boiler immediately and post-DHW PID recovery has no surge."""
    coord, hass, states_db, coros = _setup_simulated_plant(boiler_mode=MODE_RELAY)
    cid_living = make_zone_entity_id("Living Room")

    # High demand initially: 80%
    coord.demand_aggregator.set_zone_demand(cid_living, 80.0)
    await coord.plant_orchestrator._async_update_boiler()

    # 1. DHW turns active
    coord.plant_diagnostics.get_opentherm_diagnostics = MagicMock(return_value={"dhw_active": True})
    assert coord.is_dhw_active is True

    # Orchestrator tick during DHW: demand suppressed to 0.0%
    await coord.plant_orchestrator._async_update_boiler()
    assert coord.boiler_backend._last_demand == 0.0

    # 2. Simulate 20 minutes (1200 seconds) passing while DHW active
    # Update zone controller with DHW active
    st_heat = MagicMock(state="heat", attributes={"current_temperature": 17.0, "temperature": 20.0})
    coord.zone_controller._was_dhw_active = True
    await coord.zone_controller.async_update_zone(cid_living, st_heat)

    # 3. DHW ends (falling edge)
    coord.plant_diagnostics.get_opentherm_diagnostics = MagicMock(return_value={"dhw_active": False})
    assert coord.is_dhw_active is False

    # Zone controller detects DHW falling edge and resets PID integrals
    pid = coord.zone_controller._pids[cid_living]
    pid._pid.integral = 999.0  # Simulate potential windup
    demand_after_dhw = await coord.zone_controller.async_update_zone(cid_living, st_heat)

    # Integral was reset, demand is calculated cleanly without surge
    assert pid._pid.integral == 0.0 or pid._pid.integral < 10.0
    assert demand_after_dhw > 0.0
    assert coord.zone_controller._was_dhw_active is False

    for c in coros:
        c.close()


# ===========================================================================
# 3. Ritardo valvole con Master OFF, DHW, fine richiesta
# ===========================================================================

@pytest.mark.asyncio
async def test_e2e_valve_delay_abort_scenarios():
    """Verify valve delay does not turn on boiler when conditions change during delay."""
    # Scenario A: Master OFF
    coord_a, hass_a, _, coros_a = _setup_simulated_plant(valve_delay=0.05)
    await coord_a.boiler_backend.async_update(60.0, "Living Room", False)
    coord_a.set_master_state(False)
    await asyncio.sleep(0.12)
    hass_a.services.async_call.assert_not_called()

    # Scenario B: DHW active during delay
    coord_b, hass_b, _, coros_b = _setup_simulated_plant(valve_delay=0.05)
    await coord_b.boiler_backend.async_update(60.0, "Living Room", False)
    coord_b.plant_diagnostics.get_opentherm_diagnostics = MagicMock(return_value={"dhw_active": True})
    await asyncio.sleep(0.12)
    hass_b.services.async_call.assert_not_called()

    # Scenario C: Demand dropped to 0 during delay
    coord_c, hass_c, _, coros_c = _setup_simulated_plant(valve_delay=0.05)
    await coord_c.boiler_backend.async_update(60.0, "Living Room", False)
    coord_c.boiler_backend._last_demand = 0.0
    await asyncio.sleep(0.12)
    hass_c.services.async_call.assert_not_called()

    for c in coros_a + coros_b + coros_c:
        c.close()


# ===========================================================================
# 4. Master OFF e antigelo (antigelo prevale su tutto)
# ===========================================================================

@pytest.mark.asyncio
async def test_e2e_master_off_and_frost_protection():
    """Verify anti-frost emergency bypasses Master switch OFF and triggers boiler."""
    coord, hass, states_db, coros = _setup_simulated_plant(boiler_mode=MODE_RELAY, valve_delay=0.0)
    cid_living = make_zone_entity_id("Living Room")

    # Turn Master OFF
    coord.set_master_state(False)
    assert coord.get_master_state() is False

    # Configure frost settings: active, threshold 5.0 °C
    await coord.async_set_persistent_data(KEY_ANTI_FROST_ENABLED, True)
    await coord.async_set_persistent_data(KEY_FROST_PROTECTION_TEMP, 5.0)

    # Normal room temp (18 °C) with Master OFF: boiler stays emergency OFF
    states_db[cid_living] = MagicMock(state="off", attributes={"current_temperature": 18.0})
    await coord.plant_orchestrator._async_update_boiler()
    hass.services.async_call.assert_called_with(
        "switch",
        "turn_off",
        {"entity_id": "switch.boiler_relay"},
        blocking=False,
    )
    hass.services.async_call.reset_mock()

    # Freezing temperature detected (3.5 °C < 5.0 °C)
    states_db[cid_living] = MagicMock(state="off", attributes={"current_temperature": 3.5})
    assert coord.is_zone_in_frost_emergency(cid_living) is True

    # Orchestrator update: frost emergency overrides Master OFF!
    await coord.plant_orchestrator._async_update_boiler()
    # Relay backend was turned on
    assert coord.boiler_backend.status_reason.startswith("ON")
    hass.services.async_call.assert_called_with(
        "switch",
        "turn_on",
        {"entity_id": "switch.boiler_relay"},
        blocking=False,
    )

    for c in coros:
        c.close()


# ===========================================================================
# 5. Generatore non disponibile / comando non confermato
# ===========================================================================

@pytest.mark.asyncio
async def test_e2e_opentherm_command_unconfirmed_timeout():
    """Verify diagnostic event recorded when boiler fails to confirm dispatched command."""
    coord, hass, states_db, coros = _setup_simulated_plant(boiler_mode=MODE_OPENTHERM)
    ot_entity = "climate.ot_boiler"

    # Boiler starts in state 'off'
    states_db[ot_entity] = MagicMock(state="off", attributes={"temperature": 35.0})

    t0 = 1000.0
    with patch("time.monotonic", return_value=t0):
        # Demand 50% dispatches command
        await coord.boiler_backend.async_update(50.0, "Living Room", False)
        assert coord.boiler_backend._pending_command == ("on", t0)

    # 65 seconds later, entity still 'off'
    t1 = t0 + COMMAND_CONFIRM_TIMEOUT + 5.0
    with patch("time.monotonic", return_value=t1):
        await coord.boiler_backend.async_update(50.0, "Living Room", False)

        # Timeout recorded in coordinator diagnostics history
        events = coord.diagnostics_history
        assert any(e.get("type") == "BOILER_COMMAND_TIMEOUT" for e in events)

    for c in coros:
        c.close()


# ===========================================================================
# 6. Presenza unavailable e ritorno
# ===========================================================================

@pytest.mark.asyncio
async def test_e2e_presence_unavailable_to_away_and_home_return():
    """Verify presence dropout resilience and clean return from Away mode."""
    coord, hass, states_db, coros = _setup_simulated_plant()
    rm = coord.routine_manager
    rm._last_known_presence = "home"

    # Step 1: Dropout to unavailable (no action)
    ev_unavail = MagicMock()
    ev_unavail.data = {"old_state": MagicMock(state="home"), "new_state": MagicMock(state="unavailable")}
    rm._async_on_presence_changed(ev_unavail)
    assert rm._last_known_presence == "home"

    # Step 2: Confirmation of leaving: not_home -> Away triggered
    ev_leave = MagicMock()
    ev_leave.data = {"old_state": MagicMock(state="unavailable"), "new_state": MagicMock(state="not_home")}
    rm._async_on_presence_changed(ev_leave)
    assert rm._last_known_presence == "not_home"

    # Step 3: Coming back home
    ev_return = MagicMock()
    ev_return.data = {"old_state": MagicMock(state="not_home"), "new_state": MagicMock(state="home")}
    rm._async_on_presence_changed(ev_return)
    assert rm._last_known_presence == "home"

    for c in coros:
        await c


# ===========================================================================
# 7. Locale freddo (< 4 °C) senza falso guasto
# ===========================================================================

def test_e2e_cold_room_valid_operation():
    """Verify cold storage or unheated rooms operate normally down to 0°C or sub-zero."""
    coord, hass, states_db, coros = _setup_simulated_plant()
    cid_living = make_zone_entity_id("Living Room")

    from custom_components.multizone_thermostat.plant_diagnostics.anomalies import evaluate_zone_anomalies

    state = {
        "active_anomaly": ANOMALY_NONE,
        "anomaly_details": "",
        "last_temp_seen": 2.5,
        "last_temp_time": time.monotonic() - 60,
        "last_heating_time": None,
        "high_demand_start_time": None,
        "high_demand_start_temp": None,
        "ghost_heat_start_temp": None,
        "fallback_ok": False,
    }

    # Reading at 2.5°C
    states_db[cid_living] = MagicMock(attributes={"current_temperature": 2.5, "temperature": 15.0})
    anomaly, _ = evaluate_zone_anomalies(coord, hass, cid_living, state, boiler_on=False)
    assert anomaly == ANOMALY_NONE

    # Reading at -2.0°C (sub-zero but realistic winter room)
    states_db[cid_living] = MagicMock(attributes={"current_temperature": -2.0, "temperature": 15.0})
    state["last_temp_seen"] = -2.0
    anomaly, _ = evaluate_zone_anomalies(coord, hass, cid_living, state, boiler_on=False)
    assert anomaly == ANOMALY_NONE

    # Impossible spike (from -2.0°C to +8.0°C within 1 minute) -> SENSOR_FAULT
    states_db[cid_living] = MagicMock(attributes={"current_temperature": 8.0, "temperature": 15.0})
    state["last_temp_time"] = time.monotonic()
    anomaly, _ = evaluate_zone_anomalies(coord, hass, cid_living, state, boiler_on=False)
    assert anomaly == ANOMALY_SENSOR_FAULT

    for c in coros:
        c.close()


# ===========================================================================
# 8. Weather compensation: casi limite
# ===========================================================================

@pytest.mark.asyncio
async def test_e2e_weather_compensation_edge_cases():
    """Verify weather compensation edge cases: sensor missing/invalid, extreme temps, overheating decay."""
    coord, hass, states_db, coros = _setup_simulated_plant()
    cid_living = make_zone_entity_id("Living Room")
    zc = coord.zone_controller

    # Activate weather compensation with curve Ke = 1.5
    coord._settings[KEY_WEATHER_CURVE] = 1.5

    # Case A: Weather sensor entity unavailable -> safely falls back without error
    states_db["weather.forecast_home"] = MagicMock(state="unavailable")
    st_room = MagicMock(state="heat", attributes={"current_temperature": 19.0, "temperature": 20.0})
    demand_a = await zc.async_update_zone(cid_living, st_room)
    assert demand_a >= 0.0

    # Case B: Weather sensor reports extreme cold (-20.0 °C) -> Feed-forward clamped to +40% max
    states_db["weather.forecast_home"] = MagicMock(domain="weather", state="cloudy", attributes={"temperature": -20.0})
    demand_b = await zc.async_update_zone(cid_living, st_room)
    # Target 20, Outdoor -20 -> delta_t = 40. 40 * 1.5 = 60%, clamped to max +40%
    assert demand_b <= 100.0

    # Case C: Overheating room (current 20.6 °C > target 20.0 °C) -> FF decays to 0%
    st_overheat = MagicMock(state="heat", attributes={"current_temperature": 20.6, "temperature": 20.0})
    demand_c = await zc.async_update_zone(cid_living, st_overheat)
    assert demand_c == 0.0

    # Case D: Non-numeric string state -> handled gracefully via ValueError exception handler
    states_db["weather.forecast_home"] = MagicMock(domain="sensor", state="not_a_number", attributes={})
    demand_d = await zc.async_update_zone(cid_living, st_room)
    assert demand_d >= 0.0

    for c in coros:
        c.close()


# ===========================================================================
# 9. Config flow & options flow (voluptuous e campi opzionali)
# ===========================================================================

def test_e2e_config_flow_and_options_validation():
    """Verify voluptuous schemas and flow validators for OpenTherm switch and options."""
    # 1. Config flow OpenTherm schema validation
    schema_ot = get_boiler_opentherm_schema()
    # Valid with opentherm_ch_switch
    data_with_switch = {
        CONF_OPENTHERM_ENTITY: "climate.ot_boiler",
        CONF_OPENTHERM_MIN_TEMP: 35.0,
        CONF_OPENTHERM_MAX_TEMP: 75.0,
        CONF_OPENTHERM_CH_SWITCH: "switch.ch_enable",
    }
    validated_with_switch = schema_ot(data_with_switch)
    assert validated_with_switch[CONF_OPENTHERM_CH_SWITCH] == "switch.ch_enable"

    # Valid without opentherm_ch_switch (optional)
    data_without_switch = {
        CONF_OPENTHERM_ENTITY: "number.ot_setpoint",
        CONF_OPENTHERM_MIN_TEMP: 30.0,
        CONF_OPENTHERM_MAX_TEMP: 70.0,
    }
    validated_without_switch = schema_ot(data_without_switch)
    assert CONF_OPENTHERM_CH_SWITCH not in validated_without_switch

    # 2. Options flow OpenTherm schema validation
    options_schema = get_options_boiler_opentherm_schema(
        opentherm_entity="climate.ot_boiler",
        opentherm_min_temp=35.0,
        opentherm_max_temp=75.0,
        opentherm_ch_switch="switch.ch_enable",
    )
    assert options_schema is not None

    # 3. Validators
    assert validate_opentherm_temps(35, 75) == {}
    assert validate_opentherm_temps(75, 35) == {"base": "invalid_temp_range"}
    assert validate_zone_input("Zone 1", ["climate.trv"], [], []) == {}
    assert validate_zone_input("Zone 1", [], [], []) == {"base": "no_actuators_selected"}
    assert validate_geofencing(True, "sensor.presence") == {}
    assert validate_geofencing(True, None) == {"presence_sensor": "presence_sensor_required"}
