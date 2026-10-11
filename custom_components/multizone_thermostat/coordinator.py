"""Coordinator for Multizone Thermostat: handles all heating logic."""
from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime, timedelta, time as dt_time
import logging
import time
from typing import Any

import homeassistant.util.dt as dt_util

from homeassistant.components.climate import (
    ClimateEntityFeature,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_PRESET_MODE,
    SERVICE_SET_TEMPERATURE,
    DOMAIN as CLIMATE_DOMAIN,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
    STATE_OFF,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.storage import Store

from .const import (
    CONF_BOILER_SWITCH,
    CONF_BOILER_MODE,
    MODE_RELAY,
    MODE_OPENTHERM,
    CONF_OPENTHERM_ENTITY,
    CONF_OPENTHERM_MIN_TEMP,
    CONF_OPENTHERM_MAX_TEMP,
    CONF_OPENTHERM_CH_SWITCH,
    CONF_ZONES,
    CONF_PRESENCE_SENSOR,
    CONF_ANTI_SEIZE_ENABLED,
    CONF_ANTI_SEIZE_IDLE_DAYS,
    CONF_ANTI_SEIZE_DURATION,
    CONF_ANTI_SEIZE_BOILER,
    CONF_ZONE_NAME,
    make_zone_entity_id,
    CONF_ZONE_WINDOW_SENSOR,
    CONF_ZONE_TRV_SYNC,
    CONF_ZONE_ANTI_SEIZE,
    CONF_ZONE_CLIMATES,
    DOMAIN,
    GLOBAL_PRESET_MANUAL,
    HVAC_ACTION_HEATING,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    PRESET_MANUAL,
    PRESET_OFF,
    KEY_NIGHT_TIME,
    KEY_MORNING_TIME,
    KEY_AUTO_NIGHT_MODE,
    KEY_GEOFENCING_TOGGLE,
    KEY_PRE_AWAY_PRESET,
    KEY_PRE_NIGHT_PRESET,
    KEY_ANTI_SEIZE_ENABLED,
    KEY_ANTI_SEIZE_IDLE_DAYS,
    KEY_ANTI_SEIZE_DURATION,
    CONF_MIN_CYCLE_ON,
    CONF_MIN_CYCLE_OFF,
    CONF_VALVE_DELAY,
    DEFAULT_MIN_CYCLE_ON,
    DEFAULT_MIN_CYCLE_OFF,
    DEFAULT_VALVE_DELAY,
    GLOBAL_PRESET_SLEEP,
    GLOBAL_PRESET_AWAY,
    GLOBAL_PRESET_COMFORT,
    ZONE_MODE_PRIMARY,
    ZONE_MODE_SECONDARY,
    ZONE_MODE_BYPASS,
    CONF_GLOBAL_CALENDAR,
    KEY_ANTI_FROST_ENABLED,
    KEY_FROST_PROTECTION_TEMP,
    DEFAULT_FROST_PROTECTION_TEMP,
    DEFAULT_ANTI_FROST_ENABLED,
    KEY_PASSIVE_HEAT_PREFIX,
    CONF_ZONE_ALLOW_PASSIVE_HEAT,
    CONF_WEATHER_SENSOR,
    KEY_WEATHER_CURVE,
)
from .pwm_engine import PWMEngine
from .thermal_model import ThermalObserver
from .calendar_parser import parse_calendar_event, CalendarOverride

_LOGGER = logging.getLogger(__name__)

ATTR_HVAC_ACTION = "hvac_action"
ATTR_HVAC_MODE = "hvac_mode"
ATTR_PRESET_MODE = "preset_mode"

WINDOW_STORAGE_VERSION = 1
WINDOW_STORAGE_KEY = f"{DOMAIN}.window_states"
PRESET_STORAGE_KEY = f"{DOMAIN}.presets"
PRESET_STORAGE_VERSION = 1
SETTINGS_STORAGE_KEY = f"{DOMAIN}.settings"
SETTINGS_STORAGE_VERSION = 1


class MultizoneCoordinator:
    """Central coordinator that manages all heating logic."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: Any,
    ) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry_id = entry.entry_id
        self.boiler_mode = entry.data.get(CONF_BOILER_MODE, MODE_RELAY)
        self.boiler_switch = entry.data.get(CONF_BOILER_SWITCH)
        self.opentherm_entity = entry.data.get(CONF_OPENTHERM_ENTITY)
        self.opentherm_min_temp = entry.data.get(CONF_OPENTHERM_MIN_TEMP, 35.0)
        self.opentherm_max_temp = entry.data.get(CONF_OPENTHERM_MAX_TEMP, 75.0)
        self.opentherm_ch_switch = entry.data.get(CONF_OPENTHERM_CH_SWITCH)
        self.zones = entry.data.get(CONF_ZONES, [])
        self.presence_sensor = entry.data.get(CONF_PRESENCE_SENSOR)
        self.weather_sensor_id = entry.data.get(CONF_WEATHER_SENSOR)
        self.global_calendar_id = entry.data.get(CONF_GLOBAL_CALENDAR)
        self.master_device_id: str | None = None
        
        # Internal state tracking
        self._master_state: bool = False
        self._min_cycle_on = float(entry.data.get(CONF_MIN_CYCLE_ON, DEFAULT_MIN_CYCLE_ON))
        self._min_cycle_off = float(entry.data.get(CONF_MIN_CYCLE_OFF, DEFAULT_MIN_CYCLE_OFF))
        self._valve_delay = float(entry.data.get(CONF_VALVE_DELAY, DEFAULT_VALVE_DELAY))
        self._climate_callbacks = {}
        self._last_active_time = time.monotonic()

        from .zone_manager import ZoneManager
        self.zone_manager = ZoneManager(hass, self)

        from .demand_aggregator import DemandAggregator
        self.demand_aggregator = DemandAggregator(
            zones=self.zones,
            mode_getter=lambda cid: self.get_zone_mode(cid)
        )

        from .zone_controller import ZoneController
        self.zone_controller = ZoneController(hass, self)

        from .storage.storage_manager import StorageManager
        self.storage = StorageManager(hass, self.entry_id)

        self._store = Store(hass, WINDOW_STORAGE_VERSION, f"{DOMAIN}_{entry.entry_id}_window_states")
        self._legacy_window_store = Store(hass, WINDOW_STORAGE_VERSION, f"{DOMAIN}.window_states")
        self._preset_store = Store(hass, PRESET_STORAGE_VERSION, f"{DOMAIN}_{entry.entry_id}_presets")
        self._settings_store = Store(hass, SETTINGS_STORAGE_VERSION, f"{DOMAIN}_{entry.entry_id}_settings")

        from .calendar_manager import CalendarManager
        self.calendar_manager = CalendarManager(self)

        from .routine_manager import RoutineManager
        self.routine_manager = RoutineManager(
            hass,
            self.presence_sensor,
            self.get_persistent_data,
            self.async_set_persistent_data,
            self.get_global_preset,
            self.async_set_global_preset
        )

        from .safety.frost import FrostManager
        self.frost_manager = FrostManager(hass, self)

        from .safety.anti_seize import AntiSeizeManager
        self.anti_seize_manager = AntiSeizeManager(hass, self)

        from .plant_diagnostics.engine import PlantDiagnosticsEngine
        self.plant_diagnostics = PlantDiagnosticsEngine(self)

        from .boiler.opentherm_backend import OpenThermBoilerBackend
        from .boiler.relay_backend import RelayBoilerBackend
        if self.boiler_mode == "opentherm":
            self.boiler_backend = OpenThermBoilerBackend(
                hass, 
                self, 
                self.opentherm_entity, 
                self.opentherm_min_temp, 
                self.opentherm_max_temp,
                self.opentherm_ch_switch,
            )
        else:
            self.boiler_backend = RelayBoilerBackend(
                hass, 
                self, 
                self.boiler_switch, 
                self._min_cycle_on, 
                self._min_cycle_off, 
                self._valve_delay
            )


        self._anti_seize_task: asyncio.Task | None = None
        
        self._unsub_listeners: list = []
        self._select_entities: dict[str, Any] = {}  # key -> select object
        
        # PID / autotune / thermal models are owned by ZoneController; these are
        # aliases to the SAME dicts (no duplicate, stale objects).
        self._pids = self.zone_controller.pids
        self._autotuners = self.zone_controller.autotuners
        self._thermal_models = self.zone_controller.thermal_models

        self._presets: dict[str, dict[str, dict[str, Any]]] = {}
        self._current_global_preset: str = GLOBAL_PRESET_MANUAL
        
        self._settings: dict[str, Any] = {}
        
        self._last_night_trigger_date: datetime.date | None = None
        self._last_morning_trigger_date: datetime.date | None = None

        # Software Diagnostics: Ring Buffer and State Reason
        self._diagnostics_history: deque[dict[str, Any]] = deque(maxlen=100)
        self._climate_entities: dict[str, Any] = {}
        self._boiler_status_reason: str = "OFF - Initializing"

        from .boiler.plant_orchestrator import PlantOrchestrator
        self.plant_orchestrator = PlantOrchestrator(hass, self.demand_aggregator, self.boiler_backend, self)


    def register_master_switch(self, switch_entity) -> None:
        """Register the master switch entity."""
        self._master_switch = switch_entity

    def register_climate(self, entity_id: str, callback, entity_instance: Any = None) -> None:
        """Register a climate entity for state updates and diagnostics."""
        self._climate_callbacks[entity_id] = callback
        self.demand_aggregator.register_climate_callback(entity_id, callback)
        if entity_instance is not None:
            self._climate_entities[entity_id] = entity_instance

    def unregister_climate(self, entity_id: str) -> None:
        """Unregister a climate entity on removal."""
        self._climate_callbacks.pop(entity_id, None)
        self._climate_entities.pop(entity_id, None)
        if hasattr(self, "demand_aggregator"):
            self.demand_aggregator.unregister_climate_callback(entity_id)

    @property
    def _zone_modes(self) -> dict[str, str]:
        """Alias to zone modes owned by ZoneManager."""
        return self.zone_manager._zone_modes

    @property
    def _zone_demands(self) -> dict[str, float]:
        """Alias to zone demands owned by DemandAggregator."""
        return self.demand_aggregator._zone_demands

    @property
    def _pre_window_state(self) -> dict[str, str]:
        """Alias to pre-window states owned by ZoneManager."""
        return self.zone_manager._pre_window_state

    @_pre_window_state.setter
    def _pre_window_state(self, val: dict[str, str]) -> None:
        self.zone_manager._pre_window_state = val

    @property
    def last_active_time(self) -> float:
        """Return monotonic timestamp of when system was last active."""
        return self._last_active_time

    def reset_last_active_time(self) -> None:
        """Reset the last active time timestamp to now."""
        self._last_active_time = time.monotonic()

    @property
    def is_dhw_active(self) -> bool:
        """Return True if OpenTherm reports active Domestic Hot Water production."""
        if hasattr(self, "plant_diagnostics"):
            return self.plant_diagnostics.get_opentherm_diagnostics().get("dhw_active", False)
        return False
                    
    @property
    def boiler_status_reason(self) -> str:
        """Return human-readable explanation of why the boiler is currently in its state."""
        return getattr(self.boiler_backend, "status_reason", "unknown")
                    
    @property
    def diagnostics_history(self) -> list[dict[str, Any]]:
        """Return recent diagnostic trace history."""
        return list(self._diagnostics_history)
        
    def record_diagnostic_event(self, event_type: str, details: dict[str, Any] | None = None) -> None:
        """Record a diagnostic event in the circular trace buffer (fail-safe)."""
        try:
            entry: dict[str, Any] = {
                "timestamp": dt_util.now().isoformat(),
                "type": event_type,
            }
            if details:
                entry.update(details)
            self._diagnostics_history.append(entry)
        except Exception:
            pass


    @property
    def current_global_preset(self) -> str:
        return self.zone_manager.current_global_preset

    def get_global_preset(self) -> str:
        return self.zone_manager.get_global_preset()

    async def async_set_global_preset(self, preset: str) -> None:
        await self.zone_manager.async_set_global_preset(preset)

    def get_persistent_data(self, key: str, default: Any = None) -> Any:
        """Get a persistent setting."""
        return self._settings.get(key, default)
        
    async def async_set_persistent_data(self, key: str, value: Any) -> None:
        """Set a persistent setting."""
        self._settings[key] = value
        await self._settings_store.async_save(self._settings)



    def debounced_save_thermal_states(self, thermal_models) -> None:
        if hasattr(self, "storage") and self.storage:
            self.storage.debounced_save_thermal_states(thermal_models)

    async def async_load_storage(self) -> None:
        """Load stored window states and presets."""
        stored = await self._store.async_load()
        if stored is None and hasattr(self, "_legacy_window_store"):
            stored = await self._legacy_window_store.async_load()
            if stored and isinstance(stored, dict):
                _LOGGER.info("Migrating legacy window states to entry storage")
                await self._store.async_save(stored)
        if stored and isinstance(stored, dict):
            self.zone_manager._pre_window_state.clear()
            self.zone_manager._pre_window_state.update(stored)
            _LOGGER.debug("Loaded pre_window_state from storage: %s", self.zone_manager._pre_window_state)
            
        preset_stored = await self._preset_store.async_load()
        if preset_stored and isinstance(preset_stored, dict):
            self._presets = preset_stored
            _LOGGER.debug("Loaded presets from storage: %s", self._presets)
            
        settings_stored = await self._settings_store.async_load()
        if settings_stored and isinstance(settings_stored, dict):
            self._settings = settings_stored
            _LOGGER.debug("Loaded settings from storage: %s", self._settings)
            
            # Load stored zone modes
            saved_zone_modes = self._settings.get("zone_modes", {})
            self.zone_manager.load_state(
                self.zone_manager._pre_window_state,
                getattr(self, "_presets", {}),
                saved_zone_modes
            )
            for cid, mode in saved_zone_modes.items():
                if cid in self._climate_callbacks:
                    self._climate_callbacks[cid]()
            
            # Load autotuner states
            autotune_data = self._settings.get("autotuners", {})
            for climate_id, tuner in self._autotuners.items():
                if climate_id in autotune_data:
                    tuner.load_state(autotune_data[climate_id])
                    # If already completed, apply the calculated PID parameters!
                    if tuner.state == tuner.STATE_COMPLETED:
                        self._pids[climate_id].set_pid_param(kp=tuner.kp, ki=tuner.ki, kd=tuner.kd)
                        _LOGGER.info("Restored Smart PID for %s: Kp=%.1f, Ki=%.4f, Kd=%.1f", 
                                     climate_id, tuner.kp, tuner.ki, tuner.kd)

            # Load thermal models states
            thermal_data = self._settings.get("thermal_models", {})
            for climate_id, model in self._thermal_models.items():
                if climate_id in thermal_data:
                    model.load_state(thermal_data[climate_id])
                    _LOGGER.info("Restored Thermal Model for %s: Heating=%.2f, Cooling=%.2f, Inertia=%.2f", 
                                 climate_id, model.heating_rate, model.cooling_rate, model.thermal_inertia)

    async def async_save_storage(self) -> None:
        """Save window states to storage."""
        await self._store.async_save(self.zone_manager._pre_window_state)

    async def _async_save_autotuner_states(self) -> None:
        """Save autotuner learning progress to storage."""
        data = {climate_id: tuner.dump_state() for climate_id, tuner in self._autotuners.items()}
        await self.async_set_persistent_data("autotuners", data)

    async def _async_save_thermal_states(self) -> None:
        """Save thermal model learning progress to storage."""
        data = {climate_id: model.dump_state() for climate_id, model in self._thermal_models.items()}
        await self.async_set_persistent_data("thermal_models", data)

    async def _async_save_presets_storage(self) -> None:
        """Save presets to storage."""
        # Save the dictionary maintained by the zone manager
        await self._preset_store.async_save(self.zone_manager._presets)

    def register_select(self, key: str, select_entity: Any) -> None:
        """Register a select entity."""
        self._select_entities[key] = select_entity


    def set_min_cycle_on(self, value: float) -> None:
        self._min_cycle_on = value
        if hasattr(self, "boiler_backend") and hasattr(self.boiler_backend, "set_min_cycle_on"):
            self.boiler_backend.set_min_cycle_on(int(value))
        
    def set_min_cycle_off(self, value: float) -> None:
        self._min_cycle_off = value
        if hasattr(self, "boiler_backend") and hasattr(self.boiler_backend, "set_min_cycle_off"):
            self.boiler_backend.set_min_cycle_off(int(value))
        
    def set_valve_delay(self, value: float) -> None:
        self._valve_delay = value
        if hasattr(self, "boiler_backend") and hasattr(self.boiler_backend, "set_valve_delay"):
            self.boiler_backend.set_valve_delay(int(value))

    def set_master_state(self, state: bool) -> None:
        """Set master state (called by master switch entity)."""
        self._master_state = state

    def get_master_state(self) -> bool:
        """Get current master state."""
        return self._master_state

    def async_setup_listeners(self) -> None:
        """Set up state change listeners for all climate entities."""
        climate_entities = [make_zone_entity_id(z[CONF_ZONE_NAME]) for z in self.zones]

        if climate_entities:
            self._unsub_listeners.append(
                async_track_state_change_event(
                    self.hass,
                    climate_entities,
                    self._async_on_climate_state_changed,
                )
            )
            _LOGGER.debug(
                "Listening to climate state changes for: %s", climate_entities
            )
            
        # Listen for window sensors
        window_sensors = [
            z[CONF_ZONE_WINDOW_SENSOR] for z in self.zones 
            if z.get(CONF_ZONE_WINDOW_SENSOR) and z[CONF_ZONE_WINDOW_SENSOR] != "none"
        ]
        
        if window_sensors:
            self._unsub_listeners.append(
                async_track_state_change_event(
                    self.hass,
                    window_sensors,
                    self.zone_manager.async_on_window_state_changed,
                )
            )
            _LOGGER.debug(
                "Listening to window state changes for: %s", window_sensors
            )

        # Start periodic PWM evaluation (every 10 seconds)
        self._unsub_listeners.append(
            async_track_time_interval(
                self.hass,
                self.plant_orchestrator.async_tick,
                timedelta(seconds=10)
            )
        )

        self.routine_manager.async_setup_listeners()


        
        # Listen every hour for Anti-Seize check
        self._unsub_listeners.append(
            async_track_time_interval(
                self.hass,
                self.anti_seize_manager.check_anti_seize,
                timedelta(hours=1),
            )
        )
        
        # Listen every 5 minutes for Calendar API checks
        if self.global_calendar_id:
            self._unsub_listeners.append(
                async_track_time_interval(
                    self.hass,
                    self.calendar_manager.async_check_global_calendar,
                    timedelta(minutes=5),
                )
            )
            # Check immediately on startup
            self.hass.async_create_task(self.calendar_manager.async_check_global_calendar(dt_util.now()))


    def async_teardown_listeners(self) -> None:
        """Remove all state change listeners."""
        if self._anti_seize_task and not self._anti_seize_task.done():
            self._anti_seize_task.cancel()
            self._anti_seize_task = None
        backend_task = getattr(self.boiler_backend, "_pending_boiler_task", None)
        if backend_task and not backend_task.done():
            backend_task.cancel()
            self.boiler_backend._pending_boiler_task = None
        if getattr(self, "_debounce_save_task", None) and not self._debounce_save_task.done():
            self._debounce_save_task.cancel()
            self._debounce_save_task = None

        for unsub in self._unsub_listeners:
            unsub()
        self._unsub_listeners.clear()


    async def _async_on_climate_state_changed(self, event) -> None:
        entity_id = event.data.get("entity_id")
        new_state = event.data.get("new_state")
        if not new_state:
            return
        demand = await self.zone_controller.async_update_zone(entity_id, new_state)
        self.demand_aggregator.set_zone_demand(entity_id, demand)
        # Immediatly trigger boiler update to improve UI responsiveness when lowering target
        if hasattr(self, "plant_orchestrator"):
            await self.plant_orchestrator._async_update_boiler()


    def get_zone_mode(self, climate_id: str) -> str:
        return self.zone_manager.get_zone_mode(climate_id)

    def set_zone_mode(self, climate_id: str, mode: str) -> None:
        self.zone_manager.set_zone_mode(climate_id, mode)
        
    def get_zone_demand(self, climate_id: str) -> float:
        return self.demand_aggregator.get_zone_demand(climate_id)

    def get_autotuner(self, climate_id: str):
        return self.zone_controller.get_autotuner(climate_id)
    def is_zone_in_frost_emergency(self, climate_id: str) -> bool:
        """Return True if anti-frost is enabled and zone temperature is below the safety threshold."""
        if not self.get_persistent_data(KEY_ANTI_FROST_ENABLED, DEFAULT_ANTI_FROST_ENABLED):
            return False
        # Try virtual thermostat temperature first
        st = self.hass.states.get(climate_id)
        current_temp = None
        is_faulty = self.plant_diagnostics.has_critical_sensor_fault(climate_id) if hasattr(self, "plant_diagnostics") else False
        if st and not is_faulty:
            current_temp = st.attributes.get("current_temperature")

        # WARN-02: Fallback — average TRV sensor readings if virtual thermostat has no temperature yet
        # (e.g., right after boot before TRVs have reported back)
        if current_temp is None:
            zone = self.zone_manager.get_zone(climate_id)
            if zone:
                trv_temps = []
                for trv in zone.get(CONF_ZONE_CLIMATES, []):
                    trv_st = self.hass.states.get(trv)
                    if trv_st:
                        t = trv_st.attributes.get("current_temperature")
                        if t is not None:
                            trv_temps.append(float(t))
                if trv_temps:
                    current_temp = sum(trv_temps) / len(trv_temps)
                    _LOGGER.debug("Frost check for %s: using avg TRV temp %.1f°C (virtual has no reading)", climate_id, current_temp)

        if current_temp is None:
            return False
        frost_temp = float(self.get_persistent_data(KEY_FROST_PROTECTION_TEMP, DEFAULT_FROST_PROTECTION_TEMP))
        return current_temp < frost_temp
        
    async def async_apply_master_on(self) -> None:
        """Master turned ON: set heat mode for enabled zones, off for disabled."""
        _LOGGER.debug("Master ON → applying to all zones")
        for zone in self.zones:
            climate_id = make_zone_entity_id(zone[CONF_ZONE_NAME])
            mode = self.zone_manager.get_zone_mode(climate_id)
            zone_enabled = (mode != ZONE_MODE_BYPASS)
            if zone_enabled:
                await self._async_set_hvac_mode(climate_id, HVAC_MODE_HEAT)
            else:
                await self._async_set_hvac_mode(climate_id, HVAC_MODE_OFF)

    async def async_apply_master_off(self) -> None:
        """Master turned OFF: turn off all zones and boiler."""
        _LOGGER.debug("Master OFF → turning off all zones")
        for zone in self.zones:
            climate_id = make_zone_entity_id(zone[CONF_ZONE_NAME])
            await self._async_set_hvac_mode(climate_id, HVAC_MODE_OFF)
        # Boiler will auto-turn off via state change listener,
        # but we also force it off here for safety ignoring locks
        await self.plant_orchestrator.boiler_backend.async_emergency_off()



    async def _async_set_hvac_mode(self, climate_entity: str, mode: str) -> None:
        """Set HVAC mode on a climate entity."""
        state = self.hass.states.get(climate_entity)
        if state is None:
            _LOGGER.warning("Climate entity %s not found, skipping", climate_entity)
            return
            
        current_mode = state.state
        if current_mode == mode:
            return
        _LOGGER.debug("Setting %s → hvac_mode: %s", climate_entity, mode)
        await self.hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            {ATTR_ENTITY_ID: climate_entity, ATTR_HVAC_MODE: mode},
            blocking=False,
        )

