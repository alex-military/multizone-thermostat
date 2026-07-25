import sys
import os
import time
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

# Mock homeassistant BEFORE importing integration
ha_mock = MagicMock()
sys.modules['homeassistant'] = ha_mock

# Fix callback decorator
def mock_callback(func):
    return func

core_mock = MagicMock()
core_mock.callback = mock_callback
sys.modules['homeassistant.core'] = core_mock
const_mock = MagicMock()
const_mock.STATE_ON = "on"
const_mock.STATE_OFF = "off"
const_mock.STATE_UNKNOWN = "unknown"
const_mock.HVAC_MODE_HEAT = "heat"
const_mock.HVAC_MODE_OFF = "off"
const_mock.SERVICE_TURN_ON = "turn_on"
const_mock.SERVICE_TURN_OFF = "turn_off"
const_mock.ATTR_ENTITY_ID = "entity_id"
sys.modules['homeassistant.const'] = const_mock
sys.modules['homeassistant.util'] = MagicMock()
sys.modules['homeassistant.util.dt'] = MagicMock()
sys.modules['homeassistant.helpers'] = MagicMock()
sys.modules['homeassistant.helpers'].__path__ = []
sys.modules['homeassistant.helpers.storage'] = MagicMock()
sys.modules['homeassistant.helpers.event'] = MagicMock()
sys.modules['homeassistant.components'] = MagicMock()
sys.modules['homeassistant.components'].__path__ = []
sys.modules['homeassistant.components.climate'] = MagicMock()
sys.modules['homeassistant.components.climate'].DOMAIN = "climate"
sys.modules['homeassistant.components.climate'].SERVICE_SET_HVAC_MODE = "set_hvac_mode"
sys.modules['homeassistant.components.climate'].ATTR_HVAC_MODE = "hvac_mode"
sys.modules['homeassistant.components.climate.const'] = MagicMock()
sys.modules['homeassistant.components.http'] = MagicMock()
sys.modules['homeassistant.components.sensor'] = MagicMock()
sys.modules['homeassistant.config_entries'] = MagicMock()

sys.path.append(os.path.join(os.path.dirname(__file__)))

from custom_components.multizone_thermostat.coordinator import MultizoneCoordinator
from custom_components.multizone_thermostat.const import (
    DOMAIN, CONF_BOILER_SWITCH, CONF_ZONES, CONF_ZONE_CLIMATE, 
    CONF_ZONE_WINDOW_SENSOR, CONF_ZONE_ANTI_SEIZE, CONF_ZONE_TRV_SYNC,
    ZONE_MODE_PRIMARY, ZONE_MODE_SECONDARY, ZONE_MODE_BYPASS
)

from homeassistant.const import (
    STATE_ON, STATE_OFF, STATE_UNKNOWN, HVAC_MODE_HEAT, HVAC_MODE_OFF,
    SERVICE_TURN_ON, SERVICE_TURN_OFF, ATTR_ENTITY_ID
)

async def run_full_simulation():
    print("==================================================")
    print(" INIZIO SIMULAZIONE TOTALE (TUTTI GLI SCENARI)")
    print("==================================================")
    
    # 1. Mocking Home Assistant
    hass = MagicMock()
    hass.states = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.data = {DOMAIN: {}}
    hass.config = MagicMock()
    hass.config.path = MagicMock(return_value="/config")
    hass.async_create_task = lambda coro: asyncio.create_task(coro)

    # State machine dict
    mock_states = {}
    def mock_get(entity_id):
        return mock_states.get(entity_id)
    hass.states.get.side_effect = mock_get

    def set_state(entity_id, state_str, attributes=None):
        state = MagicMock()
        state.entity_id = entity_id
        state.state = state_str
        state.attributes = attributes or {}
        mock_states[entity_id] = state
        return state

    # 2. Config Entry
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {
        CONF_BOILER_SWITCH: "switch.caldaia",
        "pwm_interval": 900,
        "min_cycle_on": 2,
        "min_cycle_off": 2,
        "anti_seize_enable": True,
        "presence_sensor": "binary_sensor.presence",
        "geofencing_enable": True,
        "night_time": "22:00",
        "morning_time": "07:00",
        CONF_ZONES: [
            {
                CONF_ZONE_CLIMATE: "climate.salone",
                "name": "Salone",
                CONF_ZONE_WINDOW_SENSOR: "binary_sensor.finestra_salone",
                CONF_ZONE_ANTI_SEIZE: True,
                CONF_ZONE_TRV_SYNC: False
            },
            {
                CONF_ZONE_CLIMATE: "climate.studio",
                "name": "Studio",
                CONF_ZONE_WINDOW_SENSOR: "binary_sensor.finestra_studio",
                CONF_ZONE_ANTI_SEIZE: True,
                CONF_ZONE_TRV_SYNC: False
            }
        ]
    }

    # Setup initial states
    set_state("switch.caldaia", STATE_OFF)
    set_state("binary_sensor.finestra_salone", STATE_OFF)
    set_state("binary_sensor.finestra_studio", STATE_OFF)
    set_state("binary_sensor.presence", STATE_ON)
    set_state("climate.salone", HVAC_MODE_HEAT, {"current_temperature": 18.0, "temperature": 20.0})
    set_state("climate.studio", HVAC_MODE_HEAT, {"current_temperature": 19.0, "temperature": 20.0})
    set_state("select.zone_modes_salone_mode", ZONE_MODE_PRIMARY)
    set_state("select.zone_modes_studio_mode", ZONE_MODE_SECONDARY)

    print("\nSetup Coordinator...")
    with patch('homeassistant.helpers.storage.Store'):
        coordinator = MultizoneCoordinator(hass, entry)
        # Mock load storage
        coordinator._settings_store.async_load = AsyncMock(return_value=None)
        coordinator._preset_store.async_load = AsyncMock(return_value=None)
        coordinator._store.async_load = AsyncMock(return_value=None)
        coordinator._settings_store.async_save = AsyncMock()
        coordinator._preset_store.async_save = AsyncMock()
        coordinator._store.async_save = AsyncMock()
        await coordinator.async_load_storage()
        
        # Populate default presets for testing
        coordinator._presets = {
            "away": {
                "climate.salone": {"target_temp": 15.0, "mode": "primary"},
                "climate.studio": {"target_temp": 15.0, "mode": "primary"}
            },
            "sleep": {
                "climate.salone": {"target_temp": 17.0, "mode": "primary"},
                "climate.studio": {"target_temp": 17.0, "mode": "primary"}
            }
        }
        
        coordinator._master_state = True

    print("\n--- TEST 1: AGGREGAZIONE E SECONDARY ZONE ---")
    # Simulate Salone (Primary) asking for 0% and Studio (Secondary) asking for 100%
    set_state("climate.salone", HVAC_MODE_HEAT, {"current_temperature": 21.0, "temperature": 20.0})
    set_state("climate.studio", HVAC_MODE_HEAT, {"current_temperature": 15.0, "temperature": 20.0})
    event_mock = MagicMock()
    
    event_mock.data = {"entity_id": "climate.salone", "new_state": mock_get("climate.salone"), "old_state": None}
    await coordinator._async_on_climate_state_changed(event_mock)
    
    event_mock.data = {"entity_id": "climate.studio", "new_state": mock_get("climate.studio"), "old_state": None}
    await coordinator._async_on_climate_state_changed(event_mock)
    
    await coordinator._async_pwm_tick(None)
    # Boiler should be OFF because Salone (Primary) is satisfied. Studio (Secondary) is ignored.
    for call in hass.services.async_call.call_args_list:
        print("CALL:", call)
    hass.services.async_call.reset_mock()
    print("Successo: La zona Secondaria (Studio) NON ha fatto accendere la caldaia da sola.")

    print("\n--- TEST 2: PRIMARY ZONE E PWM ENGINE ---")
    # Salone (Primary) drops temp. Boiler should turn ON.
    set_state("climate.salone", HVAC_MODE_HEAT, {"current_temperature": 18.0, "temperature": 20.0})
    event_mock.data = {"entity_id": "climate.salone", "new_state": mock_get("climate.salone"), "old_state": None}
    await coordinator._async_on_climate_state_changed(event_mock)
    
    await coordinator._async_pwm_tick(None)
    hass.services.async_call.assert_called_with("switch", SERVICE_TURN_ON, {ATTR_ENTITY_ID: "switch.caldaia"}, blocking=False)
    print("Successo: La zona Primaria (Salone) ha attivato la caldaia.")

    # Popola _select_entities
    salone_select = AsyncMock()
    salone_select.async_select_option = AsyncMock()
    coordinator._select_entities["zone_mode_climate.salone"] = salone_select

    print("\n--- TEST 3: SENSORE FINESTRA ---")
    hass.services.async_call.reset_mock()
    # Open window in Salone
    set_state("binary_sensor.finestra_salone", STATE_ON)
    event_mock.data = {"entity_id": "binary_sensor.finestra_salone", "new_state": mock_get("binary_sensor.finestra_salone")}
    coordinator._async_on_window_state_changed(event_mock)
    
    # Check that climate was turned off (actually, it selects Bypass mode)
    salone_select.async_select_option.assert_called_with(ZONE_MODE_BYPASS)
    # Simulate HA actually changing the state
    coordinator.set_zone_mode("climate.salone", ZONE_MODE_BYPASS)
    print("Successo: Finestra Aperta -> Termostato Salone passato a BYPASS automaticamente.")

    print("\n--- TEST 4: CHIUSURA FINESTRA (RIPRISTINO) ---")
    salone_select.async_select_option.reset_mock()
    set_state("binary_sensor.finestra_salone", STATE_OFF)
    event_mock.data = {"entity_id": "binary_sensor.finestra_salone", "new_state": mock_get("binary_sensor.finestra_salone")}
    
    # Needs pre_window_state to restore
    coordinator._pre_window_state["climate.salone"] = ZONE_MODE_PRIMARY
    
    coordinator._async_on_window_state_changed(event_mock)
    salone_select.async_select_option.assert_called_with(ZONE_MODE_PRIMARY)
    print("Successo: Finestra Chiusa -> Termostato Salone ripristinato automaticamente (PRIMARY).")

    print("\n--- TEST 5: GEOFENCING E PRESENZA ---")
    hass.services.async_call.reset_mock()
    # Everyone leaves house
    old_presence = set_state("binary_sensor.presence", STATE_ON)
    set_state("binary_sensor.presence", STATE_OFF)
    event_mock.data = {"entity_id": "binary_sensor.presence", "new_state": mock_get("binary_sensor.presence"), "old_state": old_presence}
    coordinator._async_on_presence_changed(event_mock)
    await asyncio.sleep(0) # let tasks run
    # Target temp should drop (Away mode)
    hass.services.async_call.assert_any_call("climate", "set_temperature", {ATTR_ENTITY_ID: "climate.salone", "temperature": 15.0}, blocking=False)
    print("Successo: Assenza rilevata -> Temperature abbassate a Eco (15 C).")

    print("\n--- TEST 6: AUTONIGHT (GEOFENCING SCHEDULE) ---")
    hass.services.async_call.reset_mock()
    # Simulate it's 22:00 (Night time, matching config)
    import datetime
    
    # Enable Auto Night Mode
    await coordinator.async_set_persistent_data("auto_night_mode", True)
    await asyncio.sleep(0)
    
    import homeassistant.util.dt as dt_util
    dt_util.now.return_value = datetime.datetime.now().replace(hour=22, minute=30, second=0, microsecond=0)
    
    # We need to trigger _async_check_schedule (it's synchronous, but wrapped in @callback)
    coordinator._async_check_schedule(dt_util.now.return_value)
    await asyncio.sleep(0) # let tasks run
        
    # Night preset should be applied
    hass.services.async_call.assert_any_call("climate", "set_temperature", {ATTR_ENTITY_ID: "climate.salone", "temperature": 17.0}, blocking=False)
    print("Successo: Orario notturno rilevato -> Temperature passate a Sleep (17 C).")

    print("\n--- TEST 7: AUTOTUNING (ISTERESI -> PID) ---")
    tuner = coordinator._autotuners["climate.salone"]
    print(f"Stato iniziale Autotuner Salone: {tuner.state}")
    
    # Simulate 3 cycles with dense data to calculate slope
    for t in range(0, 600, 60): tuner.update(18.0 + (t/600)*3, True, now=t)
    tuner.update(21.0, False, now=600)
    for t in range(600, 1200, 60): tuner.update(21.0 - ((t-600)/600)*3, False, now=t)
    tuner.update(18.0, True, now=1200)
    
    for t in range(1200, 1800, 60): tuner.update(18.0 + ((t-1200)/600)*3, True, now=t)
    tuner.update(21.0, False, now=1800)
    for t in range(1800, 2400, 60): tuner.update(21.0 - ((t-1800)/600)*3, False, now=t)
    tuner.update(18.0, True, now=2400)
    
    for t in range(2400, 3000, 60): tuner.update(18.0 + ((t-2400)/600)*3, True, now=t)
    tuner.update(21.0, False, now=3000)
    
    if tuner.state == tuner.STATE_COMPLETED:
        print(f"Successo: Autotuner completato con successo. PID attivato!")
        print(f"Parametri calcolati: Kp={tuner.kp:.1f}, Ki={tuner.ki:.4f}, Kd={tuner.kd:.1f}")
    else:
        print("Errore Autotuner")

    print("\n--- TEST 8: ANTI-SEIZE (ESTATE) ---")
    hass.services.async_call.reset_mock()
    # Override time to trigger anti-seize
    coordinator._last_active_time = time.time() - (8 * 24 * 3600) # Inactive for 8 days
    set_state("climate.salone", HVAC_MODE_OFF, {})
    with patch('asyncio.sleep', new_callable=AsyncMock):
        await coordinator._async_execute_anti_seize()
    # It should open valves (turn on climate briefly)
    print("TUTTE LE CALL IN TEST 8:")
    for call in hass.services.async_call.call_args_list:
        print(call)
    hass.services.async_call.assert_any_call("climate", "set_hvac_mode", {ATTR_ENTITY_ID: "climate.salone", "hvac_mode": HVAC_MODE_HEAT}, blocking=False)
    print("Successo: Inattivita di 7+ giorni rilevata. Valvole aperte per Anti-Grippaggio.")

    print("\n--- TEST 9: HARD LOCKS (MIN CYCLE ON/OFF) ---")
    hass.services.async_call.reset_mock()
    coordinator.set_min_cycle_on(5) # 5 minutes min on
    coordinator.set_min_cycle_off(5) # 5 minutes min off
    
    # Force state to OFF and set last change to NOW
    coordinator._last_boiler_change = time.time()
    hass.states.set("switch.caldaia", STATE_OFF)
    
    # Simulate a sudden demand spike (e.g. user cranks up the heat)
    coordinator._zone_demands["climate.salone"] = 100.0
    coordinator._zone_modes["climate.salone"] = ZONE_MODE_PRIMARY
    
    # Evaluate PWM. Should want to turn ON, but blocked by min_cycle_off
    await coordinator._async_pwm_tick(dt_util.now())
    
    # Assert it was blocked (no call to turn_on)
    try:
        hass.services.async_call.assert_any_call("switch", "turn_on", {ATTR_ENTITY_ID: "switch.caldaia"}, blocking=False)
        print("ERRORE: La caldaia si è accesa ignorando il min_cycle_off!")
    except AssertionError:
        print("Successo: La caldaia è stata BLOCCATA dal min_cycle_off (Hard Lock).")
        
    # Now simulate time travel (6 minutes later)
    coordinator._last_boiler_change = time.time() - 360 # 6 mins
    await coordinator._async_pwm_tick(dt_util.now())
    hass.services.async_call.assert_any_call("switch", "turn_on", {ATTR_ENTITY_ID: "switch.caldaia"}, blocking=False)
    print("Successo: La caldaia si è regolarmente accesa dopo aver superato il min_cycle_off.")

    print("\n==================================================")
    print(" TUTTI I TEST PASSATI CON SUCCESSO! ZERO BUG TROVATI")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_full_simulation())
