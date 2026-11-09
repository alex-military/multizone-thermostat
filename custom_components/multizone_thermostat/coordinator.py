"""Coordinator for Multizone Thermostat: handles all heating logic."""
from __future__ import annotations

import asyncio
import inspect
from collections import deque
from datetime import datetime, timedelta, time as dt_time
import logging
import time
from typing import Any

import homeassistant.util.dt as dt_util

from homeassistant.components.climate import (
    ClimateEntityFeature,
    HVACMode,
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
    CONF_ZONE_SWITCHES,
    CONF_ZONE_VALVES,
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
    KEY_DEMAND_STRATEGY,
    CONF_ENABLE_GAS_HEATER,
    CONF_ENABLE_HEAT_PUMP,
    CONF_HEAT_PUMP_TYPE,
    HP_TYPE_CLIMATE,
    CONF_HEAT_PUMP_ENTITY,
    CONF_HEAT_PUMP_MIN_TEMP,
    CONF_HEAT_PUMP_MAX_TEMP,
    CONF_HEAT_PUMP_CH_SWITCH,
    CONF_ENERGY_MANAGEMENT_ENABLED,
    CONF_SOLAR_POWER_SENSOR,
    CONF_GRID_EXPORT_SENSOR,
    CONF_BATTERY_SOC_SENSOR,
    CONF_EXTERNAL_SOLAR_OVERRIDE_ENTITY,
    CONF_SOLAR_EXPORT_THRESHOLD,
    DEFAULT_SOLAR_EXPORT_THRESHOLD,
    CONF_BATTERY_MIN_RESERVE_SOC,
    DEFAULT_BATTERY_MIN_RESERVE_SOC,
    KEY_ALLOW_SPLIT_HEATING,
    KEY_ALLOW_SPLIT_COOLING,
    KEY_HEAT_SOURCE_PRIORITY,
    DEFAULT_HEAT_SOURCE_PRIORITY,
    HVAC_MODE_COOL,
    CONF_MASTER_HVAC_MODE,
    CONF_HEAT_PUMP_COOLING,
    DEFAULT_HEAT_PUMP_COOLING,
    DEFAULT_MASTER_OPERATION_MODE,
    CONF_ZONE_SPLIT_CLIMATE,
    CONF_ZONE_SPLIT_ROLE,
    SPLIT_ROLE_HEAT_COOL,
    SPLIT_ROLE_COOLING_ONLY,
    DEFAULT_SPLIT_ROLE,
)
from .demand_aggregator import VALID_DEMAND_STRATEGIES
from .pwm_engine import PWMEngine
from .thermal_model import ThermalObserver
from .calendar_parser import parse_calendar_event, CalendarOverride
try:
    from .custom_types import PreWindowState
except ImportError:
    from .zone_manager import PreWindowState

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
        options = getattr(entry, "options", None) or {}
        config = {**(entry.data or {}), **(options if isinstance(options, dict) else {})}
        self.boiler_mode = config.get(CONF_BOILER_MODE, MODE_RELAY)
        self.boiler_switch = config.get(CONF_BOILER_SWITCH)
        self.opentherm_entity = config.get(CONF_OPENTHERM_ENTITY)
        self.opentherm_min_temp = config.get(CONF_OPENTHERM_MIN_TEMP, 35.0)
        self.opentherm_max_temp = config.get(CONF_OPENTHERM_MAX_TEMP, 75.0)
        self.opentherm_ch_switch = config.get(CONF_OPENTHERM_CH_SWITCH)
        self.zones = config.get(CONF_ZONES, [])
        self.presence_sensor = config.get(CONF_PRESENCE_SENSOR)
        self.weather_sensor_id = config.get(CONF_WEATHER_SENSOR)
        self.global_calendar_id = config.get(CONF_GLOBAL_CALENDAR)
        
        # Phase 11 — Heating Plants & Multi-Generator
        self.enable_gas_heater = config.get(CONF_ENABLE_GAS_HEATER, True)
        self.enable_heat_pump = config.get(CONF_ENABLE_HEAT_PUMP, False)
        self.heat_pump_type = config.get(CONF_HEAT_PUMP_TYPE, HP_TYPE_CLIMATE)
        self.heat_pump_entity = config.get(CONF_HEAT_PUMP_ENTITY)
        self.heat_pump_min_temp = config.get(CONF_HEAT_PUMP_MIN_TEMP, 25.0)
        self.heat_pump_max_temp = config.get(CONF_HEAT_PUMP_MAX_TEMP, 55.0)
        self.heat_pump_ch_switch = config.get(CONF_HEAT_PUMP_CH_SWITCH)
        self.heat_pump_cooling = config.get(CONF_HEAT_PUMP_COOLING, DEFAULT_HEAT_PUMP_COOLING)
        self.master_hvac_mode: str = DEFAULT_MASTER_OPERATION_MODE

        # Phase 11 — Solar Self-Consumption & Energy Management
        self.energy_management_enabled = config.get(CONF_ENERGY_MANAGEMENT_ENABLED, False)
        self.solar_power_sensor = config.get(CONF_SOLAR_POWER_SENSOR)
        self.grid_export_sensor = config.get(CONF_GRID_EXPORT_SENSOR)
        self.battery_soc_sensor = config.get(CONF_BATTERY_SOC_SENSOR)
        self.external_solar_override_entity = config.get(CONF_EXTERNAL_SOLAR_OVERRIDE_ENTITY)
        self.solar_export_threshold = float(config.get(CONF_SOLAR_EXPORT_THRESHOLD, DEFAULT_SOLAR_EXPORT_THRESHOLD))
        self.battery_min_reserve_soc = float(config.get(CONF_BATTERY_MIN_RESERVE_SOC, DEFAULT_BATTERY_MIN_RESERVE_SOC))
        self.master_device_id: str | None = None
        
        # Internal state tracking
        self._master_state: bool = False
        self._master_switch: Any = None
        self._min_cycle_on = float(config.get(CONF_MIN_CYCLE_ON, DEFAULT_MIN_CYCLE_ON))
        self._min_cycle_off = float(config.get(CONF_MIN_CYCLE_OFF, DEFAULT_MIN_CYCLE_OFF))
        self._valve_delay = float(config.get(CONF_VALVE_DELAY, DEFAULT_VALVE_DELAY))
        self._climate_callbacks = {}
        self._last_active_time = time.monotonic()

        from .zone_manager import ZoneManager
        self.zone_manager = ZoneManager(hass, self)

        from .demand_aggregator import DemandAggregator
        self.demand_aggregator = DemandAggregator(
            zones=self.zones,
            mode_getter=lambda cid: self.get_zone_mode(cid)
        )
        self.demand_aggregator.coordinator = self

        from .zone_controller import ZoneController
        self.zone_controller = ZoneController(hass, self)

        from .split.split_controller import SplitZoneManager
        self.split_manager = SplitZoneManager(hass, self)

        from .energy.energy_manager import EnergyManager
        self.energy_manager = EnergyManager(hass, self, config)

        from .storage.storage_manager import StorageManager
        self.storage = StorageManager(hass, self.entry_id)

        # Share Store instances and backing dicts with StorageManager to prevent split-brain overwrites
        self._store = self.storage._window_store
        self._legacy_window_store = self.storage._legacy_window_store
        self._preset_store = self.storage._preset_store
        self._settings_store = self.storage._settings_store

        from .calendar_manager import CalendarManager
        self.calendar_manager = CalendarManager(self)

        from .schedule_manager import ScheduleProfileManager
        self.schedule_manager = ScheduleProfileManager(self)

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

        self._unsub_listeners: list = []
        self._select_entities: dict[str, Any] = {}  # key -> select object
        
        # PID / autotune / thermal models are owned by ZoneController; these are
        # aliases to the SAME dicts (no duplicate, stale objects).
        self._pids = self.zone_controller.pids
        self._autotuners = self.zone_controller.autotuners
        self._thermal_models = self.zone_controller.thermal_models

        self._presets: dict[str, dict[str, dict[str, Any]]] = self.storage._presets
        self._current_global_preset: str = GLOBAL_PRESET_MANUAL
        
        self._settings: dict[str, Any] = self.storage._settings

        # Software Diagnostics: Ring Buffer and State Reason
        self._diagnostics_history: deque[dict[str, Any]] = deque(maxlen=100)
        self._climate_entities: dict[str, Any] = {}
        self._boiler_status_reason: str = "OFF - Initializing"

        from .boiler.heat_pump_backend import CentralHeatPumpBackend
        self.heat_pump_backend = (
            CentralHeatPumpBackend(
                hass,
                self,
                self.heat_pump_type,
                self.heat_pump_entity,
                self.heat_pump_min_temp,
                self.heat_pump_max_temp,
                self.heat_pump_ch_switch,
                self.heat_pump_cooling,
                config.get("hp_cool_min_temp", config.get("heat_pump_cool_min_temp", 7.0)),
                config.get("hp_cool_max_temp", config.get("heat_pump_cool_max_temp", 18.0)),
                int(self._valve_delay),
            )
            if self.enable_heat_pump and self.heat_pump_entity
            else None
        )

        from .boiler.plant_orchestrator import PlantOrchestrator
        self.plant_orchestrator = PlantOrchestrator(
            hass, self.demand_aggregator, self.boiler_backend, self, self.heat_pump_backend
        )


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
        if hasattr(self, "_settings") and isinstance(self._settings, dict):
            self._settings["last_active_wall_time"] = time.time()
        if hasattr(self, "storage") and hasattr(self.storage, "debounced_save_settings"):
            self.storage.debounced_save_settings()

    @property
    def is_dhw_active(self) -> bool:
        """Return True if OpenTherm reports active Domestic Hot Water production."""
        if hasattr(self, "plant_diagnostics"):
            return self.plant_diagnostics.get_opentherm_diagnostics().get("dhw_active", False)
        return False

                    
    @property
    def boiler_status_reason(self) -> str:
        """Return human-readable explanation of why the boiler is currently in its state."""
        if not getattr(self, "enable_gas_heater", True) and getattr(self, "enable_heat_pump", False) and getattr(self, "heat_pump_backend", None):
            return getattr(self.heat_pump_backend, "status_reason", "unknown")
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
            parsed_stored = {
                k: PreWindowState(v) if isinstance(v, dict) else v
                for k, v in stored.items()
            }
            self.zone_manager._pre_window_state.clear()
            self.zone_manager._pre_window_state.update(parsed_stored)
            self.storage._pre_window_state.clear()
            self.storage._pre_window_state.update(parsed_stored)
            _LOGGER.debug("Loaded pre_window_state from storage: %s", self.zone_manager._pre_window_state)
            
        settings_stored = await self._settings_store.async_load()
        if settings_stored and isinstance(settings_stored, dict):
            self._settings.clear()
            self._settings.update(settings_stored)
            _LOGGER.debug("Loaded settings from storage: %s", self._settings)

        saved_hvac_mode = self._settings.get(CONF_MASTER_HVAC_MODE)
        if saved_hvac_mode in (HVAC_MODE_HEAT, HVAC_MODE_COOL):
            self.master_hvac_mode = saved_hvac_mode

        preset_stored = await self._preset_store.async_load()
        if preset_stored and isinstance(preset_stored, dict):
            if "presets_heat" in preset_stored or "presets_cool" in preset_stored:
                self.storage._presets_heat.clear()
                self.storage._presets_heat.update(preset_stored.get("presets_heat", {}))
                self.storage._presets_cool.clear()
                self.storage._presets_cool.update(preset_stored.get("presets_cool", {}))
            else:
                self.storage._presets_heat.clear()
                self.storage._presets_heat.update(preset_stored)
                self.storage._presets_cool.clear()
            _LOGGER.debug("Loaded presets from storage: heat=%s, cool=%s", self.storage.presets_heat, self.storage.presets_cool)

        if self._settings.get(KEY_DEMAND_STRATEGY) in VALID_DEMAND_STRATEGIES:
            self.demand_aggregator.strategy = self._settings[KEY_DEMAND_STRATEGY]
            
        # Always load stored state into ZoneManager (even if settings_stored is empty)
        saved_zone_modes = self._settings.get("zone_modes", {})
        self.zone_manager.load_state(
            self.zone_manager._pre_window_state,
            self.storage.presets_heat,
            saved_zone_modes,
            self.storage.presets_cool
        )
        for cid, mode in saved_zone_modes.items():
            if cid in self._climate_callbacks:
                self._climate_callbacks[cid]()
        
        # Load autotuner and thermal models states via ZoneController
        autotune_data = self._settings.get("autotuners", {})
        thermal_data = self._settings.get("thermal_models", {})
        if hasattr(self, "zone_controller"):
            self.zone_controller.load_state(autotune_data, thermal_data)
        else:
            for climate_id, tuner in self._autotuners.items():
                if climate_id in autotune_data:
                    tuner.load_state(autotune_data[climate_id])
                    if tuner.state == tuner.STATE_COMPLETED:
                        self._pids[climate_id].set_pid_param(kp=tuner.kp, ki=tuner.ki, kd=tuner.kd)
            for climate_id, model in self._thermal_models.items():
                if climate_id in thermal_data:
                    model.load_state(thermal_data[climate_id])

        saved_wall_time = self._settings.get("last_active_wall_time")
        if saved_wall_time is not None:
            try:
                self._last_active_time = time.monotonic() - max(0.0, time.time() - float(saved_wall_time))
            except (ValueError, TypeError):
                pass

        if hasattr(self, "schedule_manager"):
            self.schedule_manager.load_from_storage()
            if self.schedule_manager.scheduler_enabled or self.schedule_manager.profile_expires_at:
                await self.schedule_manager.async_evaluate_schedule(dt_util.now())

    async def async_save_storage(self) -> None:
        """Save window states, presets and settings to storage."""
        await self._store.async_save(self.zone_manager._pre_window_state)
        if self.storage._presets_heat is not self.zone_manager._presets_heat:
            self.storage._presets_heat.clear()
            self.storage._presets_heat.update(self.zone_manager._presets_heat)
        if self.storage._presets_cool is not self.zone_manager._presets_cool:
            self.storage._presets_cool.clear()
            self.storage._presets_cool.update(self.zone_manager._presets_cool)
        await self._preset_store.async_save(self.storage._get_preset_data())
        await self._settings_store.async_save(self._settings)

    async def _async_save_autotuner_states(self) -> None:
        """Save autotuner learning progress to storage."""
        if hasattr(self, "zone_controller"):
            await self.zone_controller.async_save_autotuner_states()
        else:
            data = {climate_id: tuner.dump_state() for climate_id, tuner in self._autotuners.items()}
            await self.async_set_persistent_data("autotuners", data)

    async def _async_save_thermal_states(self) -> None:
        """Save thermal model learning progress to storage."""
        data = {climate_id: model.dump_state() for climate_id, model in self._thermal_models.items()}
        await self.async_set_persistent_data("thermal_models", data)

    async def _async_save_presets_storage(self) -> None:
        """Save presets to storage."""
        if self.storage._presets_heat is not self.zone_manager._presets_heat:
            self.storage._presets_heat.clear()
            self.storage._presets_heat.update(self.zone_manager._presets_heat)
        if self.storage._presets_cool is not self.zone_manager._presets_cool:
            self.storage._presets_cool.clear()
            self.storage._presets_cool.update(self.zone_manager._presets_cool)
        await self._preset_store.async_save(self.storage._get_preset_data())

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
        if hasattr(self, "heat_pump_backend") and hasattr(self.heat_pump_backend, "set_valve_delay"):
            self.heat_pump_backend.set_valve_delay(int(value))

    @property
    def master_enabled(self) -> bool:
        """Return master switch state."""
        return self._master_state

    @master_enabled.setter
    def master_enabled(self, state: bool) -> None:
        """Set master switch state."""
        self._master_state = bool(state)

    def set_master_state(self, state: bool) -> None:
        """Set master state (called by master switch entity)."""
        self._master_state = state
        if state and hasattr(self, "split_manager") and self.split_manager:
            self.split_manager.reset_all_local_manual_overrides()

    async def async_set_master_enable(self, state: bool) -> None:
        """Set master enable state asynchronously and apply actions."""
        self.set_master_state(state)
        if state:
            await self.async_apply_master_on()
        else:
            await self.async_apply_master_off()

    def get_master_state(self) -> bool:
        """Get current master state."""
        return self._master_state

    def async_setup_listeners(self) -> None:
        """Set up state change listeners for all climate entities."""
        climate_entities = [make_zone_entity_id(z[CONF_ZONE_NAME]) for z in self.zones if z.get(CONF_ZONE_NAME)]

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

        # Listen every minute for Schedule Profile evaluation
        if hasattr(self, "schedule_manager"):
            self._unsub_listeners.append(
                async_track_time_interval(
                    self.hass,
                    self.schedule_manager.async_evaluate_schedule,
                    timedelta(minutes=1),
                )
            )

        # Listen every hour for Anti-Seize check
        self._unsub_listeners.append(
            async_track_time_interval(
                self.hass,
                self.anti_seize_manager.check_anti_seize,
                timedelta(hours=1),
            )
        )
        
        # Phase 11: Start EnergyManager tracking
        if hasattr(self, "energy_manager") and self.energy_manager:
            self.hass.async_create_task(self.energy_manager.async_start())

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
        if hasattr(self, "routine_manager") and self.routine_manager:
            self.routine_manager.cleanup()
        if hasattr(self, "anti_seize_manager") and self.anti_seize_manager:
            anti_seize_task = getattr(self.anti_seize_manager, "_task", None)
            if anti_seize_task and not anti_seize_task.done():
                anti_seize_task.cancel()
        backend_task = getattr(self.boiler_backend, "_pending_boiler_task", None)
        if backend_task and not backend_task.done():
            backend_task.cancel()
            self.boiler_backend._pending_boiler_task = None

        if hasattr(self, "energy_manager") and self.energy_manager:
            self.energy_manager.async_stop()

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
        # Immediately trigger boiler update to improve UI responsiveness when lowering target
        if hasattr(self, "plant_orchestrator"):
            await self.plant_orchestrator._async_update_boiler()


    def get_zone_mode(self, climate_id: str) -> str:
        return self.zone_manager.get_zone_mode(climate_id)

    def set_zone_mode(self, climate_id: str, mode: str, save_to_preset: bool = True) -> None:
        self.zone_manager.set_zone_mode(climate_id, mode, save_to_preset=save_to_preset)
        
    def get_zone_demand(self, climate_id: str) -> float:
        return self.demand_aggregator.get_zone_demand(climate_id)

    def set_zone_demand(self, climate_id: str, demand: float) -> None:
        self.demand_aggregator.set_zone_demand(climate_id, demand)

    def get_autotuner(self, climate_id: str):
        return self.zone_controller.get_autotuner(climate_id)

    def is_zone_in_frost_emergency(self, climate_id: str) -> bool:
        """Return True if anti-frost is enabled and zone temperature is below the safety threshold."""
        if hasattr(self, "frost_manager") and self.frost_manager:
            return self.frost_manager.is_zone_in_frost_emergency(climate_id)
        return False

    def is_split_heating_allowed(self) -> bool:
        """Return True if split heating is allowed by master switch."""
        return bool(self.get_persistent_data(KEY_ALLOW_SPLIT_HEATING, True))

    def is_split_cooling_allowed(self) -> bool:
        """Return True if split cooling is allowed by master switch."""
        return bool(self.get_persistent_data(KEY_ALLOW_SPLIT_COOLING, True))

    def get_heat_source_priority(self) -> str:
        """Return current heat source priority (Gas Priority, Electric Priority, etc.)."""
        return str(self.get_persistent_data(KEY_HEAT_SOURCE_PRIORITY, DEFAULT_HEAT_SOURCE_PRIORITY))
        
    def can_central_cool(self) -> bool:
        """Return True if central plant supports cooling (Heat pump with cooling enabled)."""
        hp_enabled = bool(getattr(self, "enable_heat_pump", False))
        hp_cooling = bool(getattr(self, "heat_pump_cooling", True))
        return hp_enabled and hp_cooling

    def can_zone_cool(self, climate_id: str) -> bool:
        """Return True if zone has cooling capabilities (Split AC or Central Heat Pump Cooling)."""
        if hasattr(self, "split_manager") and self.split_manager.has_split(climate_id):
            split_info = self.split_manager.get_split_info(climate_id)
            if split_info:
                role = split_info.get("split_role", DEFAULT_SPLIT_ROLE)
                if role in (SPLIT_ROLE_HEAT_COOL, SPLIT_ROLE_COOLING_ONLY):
                    return True

        if not self.can_central_cool():
            return False

        # Central cooling is active: verify that the zone has hydronic actuators suitable for cooling
        zone_conf = None
        for z in getattr(self, "zones", []):
            if make_zone_entity_id(z.get(CONF_ZONE_NAME, "")) == climate_id:
                zone_conf = z
                break

        if zone_conf:
            if zone_conf.get("allow_cooling") is True:
                return True
            if zone_conf.get("allow_cooling") is False or zone_conf.get("emitter_type") == "radiator":
                return False

            is_fancoil = bool(
                zone_conf.get("fancoil")
                or zone_conf.get("is_fancoil")
                or zone_conf.get("emitter_type") == "fancoil"
            )
            if is_fancoil:
                return True

            climates = zone_conf.get(CONF_ZONE_CLIMATES, []) or zone_conf.get("climate_entities", []) or zone_conf.get("climates", [])
            switches = zone_conf.get(CONF_ZONE_SWITCHES, []) or zone_conf.get("switch_entities", []) or zone_conf.get("switches", [])
            valves = zone_conf.get(CONF_ZONE_VALVES, []) or zone_conf.get("valve_entities", []) or zone_conf.get("valves", [])
            has_trv_sync = bool(zone_conf.get(CONF_ZONE_TRV_SYNC, zone_conf.get("trv_preset_sync", False)))

            if switches or valves:
                return True

            if climates and has_trv_sync:
                return False

        return True

    def get_zone_cooling_rate(self, climate_id: str) -> float:
        """Return cooling rate for a zone from schedule_manager or thermal observer."""
        if hasattr(self, "schedule_manager") and hasattr(self.schedule_manager, "_get_zone_cooling_rate"):
            return float(self.schedule_manager._get_zone_cooling_rate(climate_id) or 0.0)
        if hasattr(self, "thermal_model_mgr") and hasattr(self.thermal_model_mgr, "get_observer"):
            obs = self.thermal_model_mgr.get_observer(climate_id)
            if obs:
                return float(getattr(obs, "cooling_rate", 0.0))
        return 0.0

    async def async_set_master_hvac_mode(self, mode: str) -> None:
        """Set master operation mode ('heat' or 'cool') and coordinate whole-house operation."""
        if mode not in (HVAC_MODE_HEAT, HVAC_MODE_COOL):
            _LOGGER.warning("Invalid master HVAC mode: %s", mode)
            return

        self.master_hvac_mode = mode
        await self.async_set_persistent_data(CONF_MASTER_HVAC_MODE, mode)
        _LOGGER.info("Master HVAC mode set to '%s'", mode)

        if "master_operation_mode" in self._select_entities:
            self._select_entities["master_operation_mode"].async_write_ha_state()

        if "global_preset" in self._select_entities:
            self._select_entities["global_preset"].async_write_ha_state()

        for zone in self.zones:
            name = zone.get(CONF_ZONE_NAME)
            if not name:
                continue
            cid = make_zone_entity_id(name)
            t = self.zone_manager.get_preset_temperature(self.zone_manager.current_global_preset, cid, mode)
            if t is not None and (mode != HVAC_MODE_COOL or self.can_zone_cool(cid)):
                t_val = float(t)
                climate_ent = getattr(self, "_climate_entities", {}).get(cid)
                if climate_ent is not None and hasattr(climate_ent, "_target_temperature"):
                    climate_ent._target_temperature = t_val
                sched_mgr = getattr(self, "schedule_manager", None)
                if sched_mgr and getattr(sched_mgr, "scheduler_enabled", False) is True:
                    if self.zone_manager.current_global_preset == "manual":
                        sched_mgr.record_manual_override(cid, t_val)

        if self.get_master_state():
            if mode == HVAC_MODE_COOL:
                for zone in self.zones:
                    name = zone.get(CONF_ZONE_NAME)
                    if not name:
                        continue
                    cid = make_zone_entity_id(name)
                    z_mode = self.zone_manager.get_zone_mode(cid)
                    if self.can_zone_cool(cid) and z_mode != ZONE_MODE_BYPASS:
                        await self._async_set_hvac_mode(cid, HVAC_MODE_COOL)
                        t = self.zone_manager.get_preset_temperature(self.zone_manager.current_global_preset, cid, HVAC_MODE_COOL)
                        if t is not None:
                            await self.hass.services.async_call(
                                CLIMATE_DOMAIN,
                                SERVICE_SET_TEMPERATURE,
                                {ATTR_ENTITY_ID: cid, ATTR_TEMPERATURE: float(t)},
                                blocking=True,
                            )
                    else:
                        await self._async_set_hvac_mode(cid, HVAC_MODE_OFF)
            else:
                for zone in self.zones:
                    name = zone.get(CONF_ZONE_NAME)
                    if not name:
                        continue
                    cid = make_zone_entity_id(name)
                    z_mode = self.zone_manager.get_zone_mode(cid)
                    if z_mode != ZONE_MODE_BYPASS:
                        await self._async_set_hvac_mode(cid, HVAC_MODE_HEAT)
                        t = self.zone_manager.get_preset_temperature(self.zone_manager.current_global_preset, cid, HVAC_MODE_HEAT)
                        if t is not None:
                            await self.hass.services.async_call(
                                CLIMATE_DOMAIN,
                                SERVICE_SET_TEMPERATURE,
                                {ATTR_ENTITY_ID: cid, ATTR_TEMPERATURE: float(t)},
                                blocking=True,
                            )
                    else:
                        await self._async_set_hvac_mode(cid, HVAC_MODE_OFF)

        if hasattr(self, "_master_switch") and self._master_switch:
            self._master_switch.async_write_ha_state()

        await self.async_update_all_climates()

    async def async_apply_master_on(self) -> None:
        """Master turned ON: set current master HVAC mode (heat or cool) for capable enabled zones."""
        _LOGGER.debug("Master ON (mode: %s) → applying to all zones", self.master_hvac_mode)
        if self.master_hvac_mode == HVAC_MODE_COOL:
            for zone in self.zones:
                cid = make_zone_entity_id(zone[CONF_ZONE_NAME])
                mode = self.zone_manager.get_zone_mode(cid)
                if self.can_zone_cool(cid) and mode != ZONE_MODE_BYPASS:
                    await self._async_set_hvac_mode(cid, HVAC_MODE_COOL)
                    t = self.zone_manager.get_preset_temperature(self.zone_manager.current_global_preset, cid, HVAC_MODE_COOL)
                    if t is not None:
                        await self.hass.services.async_call(
                            CLIMATE_DOMAIN,
                            SERVICE_SET_TEMPERATURE,
                            {ATTR_ENTITY_ID: cid, ATTR_TEMPERATURE: float(t)},
                            blocking=True,
                        )
                else:
                    await self._async_set_hvac_mode(cid, HVAC_MODE_OFF)
        else:
            for zone in self.zones:
                cid = make_zone_entity_id(zone[CONF_ZONE_NAME])
                mode = self.zone_manager.get_zone_mode(cid)
                if mode != ZONE_MODE_BYPASS:
                    await self._async_set_hvac_mode(cid, HVAC_MODE_HEAT)
                    t = self.zone_manager.get_preset_temperature(self.zone_manager.current_global_preset, cid, HVAC_MODE_HEAT)
                    if t is not None:
                        await self.hass.services.async_call(
                            CLIMATE_DOMAIN,
                            SERVICE_SET_TEMPERATURE,
                            {ATTR_ENTITY_ID: cid, ATTR_TEMPERATURE: float(t)},
                            blocking=True,
                        )
                else:
                    await self._async_set_hvac_mode(cid, HVAC_MODE_OFF)

    async def async_apply_master_off(self) -> None:
        """Master turned OFF: turn off all zones and boiler."""
        _LOGGER.debug("Master OFF → turning off all zones")
        for zone in self.zones:
            climate_id = make_zone_entity_id(zone[CONF_ZONE_NAME])
            await self._async_set_hvac_mode(climate_id, HVAC_MODE_OFF)
        # Boiler will auto-turn off via state change listener,
        # but we also force it off here for safety ignoring locks
        await self.plant_orchestrator.boiler_backend.async_emergency_off()
        hp_backend = getattr(self, "heat_pump_backend", None) or getattr(self.plant_orchestrator, "heat_pump_backend", None)
        if hp_backend is not None and hasattr(hp_backend, "async_emergency_off"):
            await hp_backend.async_emergency_off()



    async def _async_set_hvac_mode(self, climate_entity: str, mode: str) -> None:
        """Set HVAC mode on a climate entity."""
        climate_ent = getattr(self, "_climate_entities", {}).get(climate_entity)
        if climate_ent is not None:
            if hasattr(HVACMode, mode.upper()):
                climate_ent._hvac_mode = HVACMode(mode)
            else:
                climate_ent._hvac_mode = mode

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
            blocking=True,
        )



    async def async_update_all_climates(self) -> None:
        """Trigger zone controller re-evaluation and state write on all registered zones."""
        for entity_id, cb in list(self._climate_callbacks.items()):
            if hasattr(self, "zone_controller") and self.zone_controller and hasattr(self, "hass") and self.hass:
                st = self.hass.states.get(entity_id) if hasattr(self.hass, "states") else None
                if st is not None:
                    coro = self.zone_controller.async_update_zone(entity_id, st)
                    if inspect.iscoroutine(coro):
                        await coro
            cb()
