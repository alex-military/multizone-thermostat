"""Coordinator for Multizone Thermostat: handles all heating logic."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, time as dt_time
import logging
import time
from typing import Any

import homeassistant.util.dt as dt_util

from homeassistant.components.climate import (
    ClimateEntityFeature,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_PRESET_MODE,
    DOMAIN as CLIMATE_DOMAIN,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
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
        self.boiler_switch = entry.data.get(CONF_BOILER_SWITCH)
        self.zones = entry.data.get(CONF_ZONES, [])
        self.presence_sensor = entry.data.get(CONF_PRESENCE_SENSOR)
        self.weather_sensor_id = entry.data.get("weather_sensor")
        self.global_calendar_id = entry.data.get(CONF_GLOBAL_CALENDAR)
        
        # Internal state tracking
        self._master_state: bool = False
        self._zone_modes: dict[str, str] = {
            make_zone_entity_id(z[CONF_ZONE_NAME]): ZONE_MODE_PRIMARY for z in self.zones
        }
        self._zone_demands: dict[str, float] = {
            make_zone_entity_id(z[CONF_ZONE_NAME]): 0.0 for z in self.zones
        }
        self._pre_window_state: dict[str, str] = {}
        self._pre_anti_seize_state: dict[str, str] = {}
        self._min_cycle_on = 0.0
        self._min_cycle_off = 0.0
        self._valve_delay = 0.0
        self._climate_callbacks = {}
        self._last_boiler_change = 0.0
        self._last_active_time = time.time() # Default to now until loaded
        self._anti_seize_running = False
        
        self._calendar_active_event_id: str | None = None
        self._calendar_temp_overrides: dict[str, float] = {}
        self._calendar_mode_overrides: dict[str, str] = {}
        self._pre_calendar_preset: str | None = None
        
        self._store = Store(hass, WINDOW_STORAGE_VERSION, WINDOW_STORAGE_KEY)
        self._preset_store = Store(hass, PRESET_STORAGE_VERSION, f"{DOMAIN}_{entry.entry_id}_presets")
        self._settings_store = Store(hass, SETTINGS_STORAGE_VERSION, f"{DOMAIN}_{entry.entry_id}_settings")

        self._pending_boiler_task: asyncio.Task | None = None
        self._boiler_pwm = PWMEngine(pwm_interval=900.0, min_on=self._min_cycle_on * 60, min_off=self._min_cycle_off * 60)
        
        self._unsub_listeners: list = []
        self._select_entities: dict[str, Any] = {}  # key -> select object
        
        # Centralized PIDs for all zones (TRVs and Virtual)
        from .pid_wrapper import MultizonePID
        from .autotune import PassiveAutotuneObserver
        self._pids: dict[str, MultizonePID] = {}
        self._autotuners: dict[str, PassiveAutotuneObserver] = {}
        self._thermal_models: dict[str, ThermalObserver] = {}
        for zone in self.zones:
            climate_id = make_zone_entity_id(zone[CONF_ZONE_NAME])
            # Default Kp=100, Ki=0, Kd=0 (will be overridden by Autolearning later)
            self._pids[climate_id] = MultizonePID(kp=100.0, ki=0.0, kd=0.0, out_min=0.0, out_max=100.0, sensor_timeout=7200.0)
            self._autotuners[climate_id] = PassiveAutotuneObserver(climate_id, required_cycles=3)
            self._thermal_models[climate_id] = ThermalObserver(climate_id)



        self._presets: dict[str, dict[str, dict[str, Any]]] = {}
        self._current_global_preset: str = GLOBAL_PRESET_MANUAL
        
        self._settings: dict[str, Any] = {}
        
        self._last_night_trigger_date: datetime.date | None = None
        self._last_morning_trigger_date: datetime.date | None = None

    def register_climate(self, entity_id: str, callback) -> None:
        """Register a climate entity for state updates."""
        self._climate_callbacks[entity_id] = callback

    def get_persistent_data(self, key: str, default: Any = None) -> Any:
        """Get a persistent setting."""
        return self._settings.get(key, default)

    async def async_set_persistent_data(self, key: str, value: Any) -> None:
        """Set a persistent setting."""
        self._settings[key] = value
        await self._settings_store.async_save(self._settings)

    async def async_load_storage(self) -> None:
        """Load stored window states and presets."""
        stored = await self._store.async_load()
        if stored and isinstance(stored, dict):
            self._pre_window_state = stored
            _LOGGER.debug("Loaded pre_window_state from storage: %s", self._pre_window_state)
            
        preset_stored = await self._preset_store.async_load()
        if preset_stored and isinstance(preset_stored, dict):
            self._presets = preset_stored
            _LOGGER.debug("Loaded presets from storage: %s", self._presets)
            
        settings_stored = await self._settings_store.async_load()
        if settings_stored and isinstance(settings_stored, dict):
            self._settings = settings_stored
            _LOGGER.debug("Loaded settings from storage: %s", self._settings)
            
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

    async def _async_save_storage(self) -> None:
        """Save window states to storage."""
        await self._store.async_save(self._pre_window_state)

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
        await self._preset_store.async_save(self._presets)

    def register_select(self, key: str, select_entity: Any) -> None:
        """Register a select entity."""
        self._select_entities[key] = select_entity

    def set_master_state(self, state: bool) -> None:
        """Set master state (called by master switch entity)."""
        self._master_state = state

    def get_zone_mode(self, climate_entity: str) -> str:
        """Get current zone mode, prioritizing calendar overrides."""
        if climate_entity in self._calendar_mode_overrides:
            return self._calendar_mode_overrides[climate_entity]
        return self._zone_modes.get(climate_entity, ZONE_MODE_PRIMARY)
        
    def get_zone_demand(self, climate_id: str) -> float:
        """Get the PID demand for a zone (0-100%)."""
        return self._zone_demands.get(climate_id, 0.0)

    def set_zone_demand(self, climate_id: str, demand: float) -> None:
        """Set the PID demand for a zone."""
        old_demand = self._zone_demands.get(climate_id)
        self._zone_demands[climate_id] = demand
        if old_demand != demand and climate_id in self._climate_callbacks:
            self._climate_callbacks[climate_id]()

    def get_pid(self, climate_id: str):
        """Get the PID controller for a zone."""
        return self._pids.get(climate_id)

    def set_zone_mode(self, climate_entity: str, mode: str) -> None:
        """Set zone mode (called by zone select entity)."""
        self._zone_modes[climate_entity] = mode

        # If a preset is active, save the mode state
        if self._current_global_preset:
            if self._current_global_preset not in self._presets:
                self._presets[self._current_global_preset] = {}
            if climate_entity not in self._presets[self._current_global_preset]:
                self._presets[self._current_global_preset][climate_entity] = {}

            self._presets[self._current_global_preset][climate_entity]["mode"] = mode
            self.hass.async_create_task(self._async_save_presets_storage())

    @property
    def current_global_preset(self) -> str:
        """Return the current global preset."""
        return self._current_global_preset

    def set_global_preset(self, preset: str) -> None:
        """Set the global preset (used on restore)."""
        self._current_global_preset = preset

    def get_global_preset(self) -> str:
        """Get the current global preset."""
        return self._current_global_preset

    async def async_set_global_preset(self, preset: str) -> None:
        """Set the global preset and apply it to all zones."""
        self._current_global_preset = preset
        _LOGGER.debug("Global preset changed to: %s", preset)
        
        # Notify the UI select entity if it's registered
        if "global_preset" in self._select_entities:
            self._select_entities["global_preset"].async_write_ha_state()

        if preset not in self._presets:
            return
            
        preset_data = self._presets[preset]
        for climate_entity, data in preset_data.items():
            if "target_temp" in data:
                try:
                    await self.hass.services.async_call(
                        "climate",
                        "set_temperature",
                        {"entity_id": climate_entity, "temperature": data["target_temp"]},
                        blocking=False,
                    )
                except Exception as ex:
                    _LOGGER.warning("Could not set temperature for %s: %s", climate_entity, ex)
            
            # Legacy preset support
            mode = ZONE_MODE_PRIMARY
            if "mode" in data:
                mode = data["mode"]
            elif "bypassed" in data:
                mode = ZONE_MODE_BYPASS if data["bypassed"] else ZONE_MODE_PRIMARY

            zone_select = self._select_entities.get(f"zone_mode_{climate_entity}")
            if zone_select:
                try:
                    await zone_select.async_select_option(mode)
                except Exception as ex:
                    _LOGGER.warning("Could not set zone mode for %s: %s", climate_entity, ex)

    def get_master_state(self) -> bool:
        """Get current master state."""
        return self._master_state

    @callback
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
                    self._async_on_window_state_changed,
                )
            )
            _LOGGER.debug(
                "Listening to window state changes for: %s", window_sensors
            )

        # Start periodic PWM evaluation (every 10 seconds)
        self._unsub_listeners.append(
            async_track_time_interval(
                self.hass,
                self._async_pwm_tick,
                timedelta(seconds=10)
            )
        )

        # Listen to presence sensor if configured
        if self.presence_sensor:
            self._unsub_listeners.append(
                async_track_state_change_event(
                    self.hass,
                    [self.presence_sensor],
                    self._async_on_presence_changed,
                )
            )
            _LOGGER.debug("Listening to presence sensor: %s", self.presence_sensor)

        # Listen every minute for Schedule check (Night / Morning)
        self._unsub_listeners.append(
            async_track_time_interval(
                self.hass,
                self._async_check_schedule,
                timedelta(minutes=1),
            )
        )
        
        # Listen every hour for Anti-Seize check
        self._unsub_listeners.append(
            async_track_time_interval(
                self.hass,
                self._async_check_anti_seize,
                timedelta(hours=1),
            )
        )
        
        # Listen every 5 minutes for Calendar API checks
        if self.global_calendar_id:
            self._unsub_listeners.append(
                async_track_time_interval(
                    self.hass,
                    self._async_check_global_calendar,
                    timedelta(minutes=5),
                )
            )
            # Check immediately on startup
            self.hass.async_create_task(self._async_check_global_calendar(dt_util.now()))

    @callback
    def async_teardown_listeners(self) -> None:
        """Remove all state change listeners."""
        for unsub in self._unsub_listeners:
            unsub()
        self._unsub_listeners.clear()

    async def _async_on_climate_state_changed(self, event: Event) -> None:
        """Handle state changes of any managed climate entity."""
        entity_id = event.data.get("entity_id")
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")

        if not new_state:
            return

        # Phase 4: Calculate PID demand for this zone
        current_temp = new_state.attributes.get("current_temperature")
        target_temp = new_state.attributes.get("temperature")
        
        if current_temp is not None and target_temp is not None:
            # Check mode (don't calculate if off/bypass)
            hvac_mode = new_state.state
            zone_mode = self.get_zone_mode(entity_id)
            if hvac_mode == HVAC_MODE_HEAT and zone_mode != ZONE_MODE_BYPASS:
                
                # Smart Stop: Calculate Effective Target based on learned Inertia
                thermal_model = self._thermal_models[entity_id]
                effective_target = target_temp
                if thermal_model.thermal_inertia > 0.05:
                    effective_target = target_temp - thermal_model.thermal_inertia
                    # Limit to avoid lowering it too much if inertia is crazy high
                    effective_target = max(target_temp - 1.0, effective_target)
                
                # Update Autotuner
                tuner = self._autotuners[entity_id]
                was_completed = (tuner.state == tuner.STATE_COMPLETED)
                is_completed = (tuner.state == tuner.STATE_COMPLETED)
                
                # Check if learning just finished!
                if is_completed and not was_completed:
                    self._pids[entity_id].set_pid_param(kp=tuner.kp, ki=tuner.ki, kd=tuner.kd)
                    _LOGGER.info("Autotuning just completed for %s! Smart PID activated.", entity_id)
                    # Save states
                    await self._async_save_autotuner_states()
                    
                if tuner.state != tuner.STATE_COMPLETED:
                    # Hysteresis Fallback Mode (Learning phase)
                    tolerance = 0.3
                    current_demand = self.get_zone_demand(entity_id)
                    if current_temp <= effective_target - tolerance:
                        demand = 100.0
                    elif current_temp >= effective_target + tolerance:
                        demand = 0.0
                    else:
                        demand = current_demand # Keep previous demand inside the hysteresis band
                else:
                    # Smart PID Mode
                    demand = self._pids[entity_id].calc(current_temp, effective_target)
                    
                    # Apply Weather Compensation (Feed Forward)
                    curve_val = self.get_persistent_data("weather_curve", 0.0)
                    if self.weather_sensor_id:
                        weather_state = self.hass.states.get(self.weather_sensor_id)
                        if weather_state and weather_state.state not in ("unavailable", "unknown"):
                            try:
                                outdoor_temp = None
                                if weather_state.domain == "weather":
                                    temp_attr = weather_state.attributes.get("temperature")
                                    if temp_attr is not None:
                                        outdoor_temp = float(temp_attr)
                                else:
                                    outdoor_temp = float(weather_state.state)
                                    
                                    if outdoor_temp is not None:
                                        # Adaptive Curve Calculation (SAT Math)
                                        curve_val = thermal_model.get_weather_multiplier(manual_base_curve=curve_val)
                                        
                                        # (Target - OutdoorTemp) * Ke
                                        delta_t = effective_target - outdoor_temp
                                        if delta_t > 0.0 and curve_val > 0.0:
                                            ff_demand = delta_t * curve_val
                                            # Clamp the weather bonus to a max of +40% to avoid it dominating the PID
                                            ff_demand = min(40.0, ff_demand)
                                            demand = min(100.0, max(0.0, demand + ff_demand))
                                            _LOGGER.debug("[%s] SAT Weather Comp: Target=%.1f, Outdoor=%.1f, Ke=%.2f, FF=+%.1f%%, Final=%.1f%%", 
                                                          entity_id, effective_target, outdoor_temp, curve_val, ff_demand, demand)
                            except ValueError:
                                pass
            else:
                demand = 0.0
                
            self.set_zone_demand(entity_id, demand)
            
            # Feed Autotuner again if we just changed demand
            tuner = self._autotuners[entity_id]
            if tuner.state != tuner.STATE_COMPLETED:
                tuner.update(current_temp, demand > 0)
                
            # Feed Thermal Observer
            self._thermal_models[entity_id].update(current_temp, demand > 0)
            self.hass.async_create_task(self._async_save_thermal_states())
                
            _LOGGER.debug("Zone '%s' Demand updated: %.1f%% (Temp: %s, Target: %s, Mode: %s)", 
                          entity_id, demand, current_temp, target_temp, "PID" if tuner.state == tuner.STATE_COMPLETED else "Hysteresis")

        else:
            demand = 0.0
            self.set_zone_demand(entity_id, 0.0)

        # Trigger boiler update if action changed (Legacy fallback check)
        _LOGGER.debug("Climate state changed: %s → %s", entity_id, new_state.state)

        # 0. Check for target temperature changes to save to preset memory
        old_state = event.data.get("old_state")
        if old_state is not None and self._current_global_preset:
            new_temp = new_state.attributes.get("temperature")
            old_temp = old_state.attributes.get("temperature")
            if new_temp is not None and new_temp != old_temp:
                if self._current_global_preset not in self._presets:
                    self._presets[self._current_global_preset] = {}
                if entity_id not in self._presets[self._current_global_preset]:
                    self._presets[self._current_global_preset][entity_id] = {}
                
                self._presets[self._current_global_preset][entity_id]["target_temp"] = new_temp
                self.hass.async_create_task(self._async_save_presets_storage())
                _LOGGER.debug("Saved new target temp %s for %s in preset %s", new_temp, entity_id, self._current_global_preset)

        # 1. Boiler demand is managed by the periodic PWM tick

        # 2. TRV preset sync (if enabled for this zone)
        zone = self._get_zone(entity_id)
        if zone and zone.get(CONF_ZONE_TRV_SYNC, False):
            self.hass.async_create_task(
                self._async_sync_trv_preset(entity_id, new_state.state)
            )

    async def _async_sync_trv_preset(self, zone_id: str, new_state: str) -> None:
        """Sync TRV activation/presets based on Zone state (heat/off)."""
        zone = self._get_zone(zone_id)
        if not zone:
            return
            
        climates = zone.get(CONF_ZONE_CLIMATES, [])
        for trv in climates:
            trv_state = self.hass.states.get(trv)
            if not trv_state:
                continue
                
            supported_presets = trv_state.attributes.get("preset_modes", [])
            target_preset = None
            
            if new_state == HVAC_MODE_HEAT:
                # Try to wake up the TRV
                if "manual" in supported_presets:
                    target_preset = "manual"
                elif "none" in supported_presets:
                    target_preset = "none"
                elif "boost" in supported_presets:
                    target_preset = "boost"
            elif new_state == HVAC_MODE_OFF:
                # Try to put the TRV to sleep
                if "off" in supported_presets:
                    target_preset = "off"
                elif "none" in supported_presets:
                    target_preset = "none"
                    
            if target_preset:
                _LOGGER.debug("Syncing TRV preset for %s to %s (Zone is %s)", trv, target_preset, new_state)
                await self.hass.services.async_call(
                    CLIMATE_DOMAIN,
                    SERVICE_SET_PRESET_MODE,
                    {ATTR_ENTITY_ID: trv, ATTR_PRESET_MODE: target_preset},
                    blocking=False,
                )

    @callback
    def _async_on_window_state_changed(self, event: Event) -> None:
        """Handle window sensor state changes → bypass/restore zone."""
        sensor_id = event.data.get("entity_id")
        new_state = event.data.get("new_state")
        
        _LOGGER.debug("Window listener fired: %s -> %s", sensor_id, new_state.state if new_state else "None")

        if new_state is None:
            return
            
        # Find ALL zones this sensor belongs to
        matching_zones = [z for z in self.zones if z.get(CONF_ZONE_WINDOW_SENSOR) == sensor_id]
        _LOGGER.debug("Window listener: matching zones: %s", matching_zones)
        if not matching_zones:
            return
            
        for zone in matching_zones:
            climate_id = make_zone_entity_id(zone[CONF_ZONE_NAME])
            zone_select = self._select_entities.get(f"zone_mode_{climate_id}")
            _LOGGER.debug("Window listener: zone_select for %s: %s", climate_id, zone_select)
            
            if new_state.state == "on":
                # Window OPENED
                _LOGGER.debug("Window opened (%s), bypassing zone %s", sensor_id, climate_id)
                # Save current state if not already saved
                if climate_id not in self._pre_window_state:
                    current_mode = self.get_zone_mode(climate_id)
                    self._pre_window_state[climate_id] = current_mode
                    self.hass.async_create_task(self._async_save_storage())
                
                # Change mode to Bypass
                if zone_select and self.get_zone_mode(climate_id) != ZONE_MODE_BYPASS:
                    self.hass.async_create_task(zone_select.async_select_option(ZONE_MODE_BYPASS))
                    
            elif new_state.state == "off":
                # Window CLOSED
                _LOGGER.debug("Window closed (%s), restoring zone %s", sensor_id, climate_id)
                if climate_id in self._pre_window_state:
                    was_mode = self._pre_window_state.pop(climate_id)
                    self.hass.async_create_task(self._async_save_storage())
                    
                    # Restore the mode
                    if zone_select and self.get_zone_mode(climate_id) != was_mode:
                        self.hass.async_create_task(zone_select.async_select_option(was_mode))

    @callback
    def _async_on_presence_changed(self, event: Event) -> None:
        """Handle presence sensor state changes (Geofencing logic)."""
        if not self.get_persistent_data(KEY_GEOFENCING_TOGGLE, True):
            return  # Geofencing is disabled dynamically

        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        if new_state is None or old_state is None:
            return
            
        old_val = old_state.state
        new_val = new_state.state
        if old_val == new_val:
            return
            
        _LOGGER.info("Presence changed: %s -> %s", old_val, new_val)
        
        # Consider 0, 'not_home', or 'off' as Away
        is_away = new_val in ("0", "not_home", "off")
        was_away = old_val in ("0", "not_home", "off")
        
        if is_away and not was_away:
            # Everyone left! Save current preset and set to Away
            _LOGGER.info("Geofencing: Everyone left. Setting to Away mode.")
            self.hass.async_create_task(self.async_set_persistent_data(KEY_PRE_AWAY_PRESET, self._current_global_preset))
            self.hass.async_create_task(self.async_set_global_preset(GLOBAL_PRESET_AWAY))
            
        elif not is_away and was_away:
            # Someone returned!
            _LOGGER.info("Geofencing: Someone returned.")
            
            night_time_str = self.get_persistent_data(KEY_NIGHT_TIME, "22:30")
            morning_time_str = self.get_persistent_data(KEY_MORNING_TIME, "07:00")
            is_night = False
            try:
                n_hour, n_minute = map(int, night_time_str.split(":"))
                m_hour, m_minute = map(int, morning_time_str.split(":"))
                now = dt_util.now().time()
                night_time = dt_time(n_hour, n_minute)
                morning_time = dt_time(m_hour, m_minute)
                
                if night_time > morning_time:
                    if now >= night_time or now <= morning_time:
                        is_night = True
                else:
                    if now >= night_time and now <= morning_time:
                        is_night = True
                        
                _LOGGER.debug("Geofencing schedule: night_time=%s, morning_time=%s, now=%s, is_night=%s", night_time, morning_time, now, is_night)
            except Exception as ex:
                _LOGGER.warning("Geofencing schedule exception: %s", ex)
                
            if is_night:
                _LOGGER.info("Geofencing: Returned at night. Setting Sleep mode.")
                pre_away = self.get_persistent_data(KEY_PRE_AWAY_PRESET, GLOBAL_PRESET_COMFORT)
                self.hass.async_create_task(self.async_set_persistent_data(KEY_PRE_NIGHT_PRESET, pre_away))
                self.hass.async_create_task(self.async_set_global_preset(GLOBAL_PRESET_SLEEP))
            else:
                pre_away = self.get_persistent_data(KEY_PRE_AWAY_PRESET, GLOBAL_PRESET_COMFORT)
                _LOGGER.info("Geofencing: Restoring previous mode: %s", pre_away)
                self.hass.async_create_task(self.async_set_global_preset(pre_away))

    @callback
    def _async_check_schedule(self, now: datetime) -> None:
        """Check if it's time to trigger Auto Night Mode or Morning Mode."""
        if not self.get_persistent_data(KEY_AUTO_NIGHT_MODE, False):
            return

        local_now = dt_util.now()
        current_date = local_now.date()

        # Check Night Time
        night_time_str = self.get_persistent_data(KEY_NIGHT_TIME, "22:30")
        try:
            hour, minute = map(int, night_time_str.split(":"))
            if local_now.hour == hour and local_now.minute == minute:
                if self._last_night_trigger_date != current_date:
                    self._last_night_trigger_date = current_date
                    if self._current_global_preset in (GLOBAL_PRESET_MANUAL, "none"):
                        _LOGGER.info("Auto Night Mode skipped because system is in Manual mode.")
                    elif self._current_global_preset != GLOBAL_PRESET_SLEEP:
                        _LOGGER.info("Auto Night Mode triggered. Setting Sleep mode.")
                        self.hass.async_create_task(self.async_set_persistent_data(KEY_PRE_NIGHT_PRESET, self._current_global_preset))
                        self.hass.async_create_task(self.async_set_global_preset(GLOBAL_PRESET_SLEEP))
        except Exception:
            pass

        # Check Morning Time
        morning_time_str = self.get_persistent_data(KEY_MORNING_TIME, "07:00")
        try:
            hour, minute = map(int, morning_time_str.split(":"))
            if local_now.hour == hour and local_now.minute == minute:
                if self._last_morning_trigger_date != current_date:
                    self._last_morning_trigger_date = current_date
                    if self._current_global_preset in (GLOBAL_PRESET_MANUAL, "none"):
                        _LOGGER.info("Auto Morning Mode skipped because system is in Manual mode.")
                    else:
                        pre_night = self.get_persistent_data(KEY_PRE_NIGHT_PRESET, GLOBAL_PRESET_COMFORT)
                        _LOGGER.info("Auto Morning Mode triggered. Restoring mode: %s", pre_night)
                        self.hass.async_create_task(self.async_set_global_preset(pre_night))
        except Exception:
            pass

    async def _async_check_global_calendar(self, now: datetime) -> None:
        """Fetch and parse calendar events for scheduling and Smart Start."""
        if not self.global_calendar_id:
            return
            
        # 1. Fetch events from now to +24 hours
        end_time = now + timedelta(hours=24)
        try:
            response = await self.hass.services.async_call(
                "calendar",
                "get_events",
                {
                    "entity_id": self.global_calendar_id,
                    "start_date_time": now.isoformat(),
                    "end_date_time": end_time.isoformat()
                },
                blocking=True,
                return_response=True
            )
            
            if not response or self.global_calendar_id not in response:
                return
                
            events = response[self.global_calendar_id].get("events", [])
            
            # Find current and next event
            current_event = None
            next_event = None
            
            for event in events:
                try:
                    # calendar.get_events returns ISO strings
                    start = dt_util.parse_datetime(event["start"])
                    end = dt_util.parse_datetime(event["end"])
                    
                    if start and end:
                        if start <= now < end:
                            if not current_event:
                                current_event = event
                        elif now < start:
                            if not next_event:
                                next_event = event
                                break # Found the immediate next
                except Exception as ex:
                    _LOGGER.warning("Error parsing calendar event dates: %s", ex)
                    
            await self._async_process_calendar_events(current_event, next_event, now)
                
        except Exception as ex:
            _LOGGER.error("Error fetching calendar events: %s", ex)

    async def _async_process_calendar_events(self, current_event: dict | None, next_event: dict | None, now: datetime) -> None:
        """Process current and future events."""
        # 1. Process Current Event
        if current_event:
            # We use a unique ID based on start time and title to avoid re-applying SET constantly
            event_uid = f"{current_event['start']}_{current_event['summary']}"
            
            if self._calendar_active_event_id != event_uid:
                _LOGGER.info("Calendar Event Started: %s", current_event["summary"])
                self._calendar_active_event_id = event_uid
                
                if self._pre_calendar_preset is None:
                    self._pre_calendar_preset = self._current_global_preset
                
                # Clear temporary overrides from previous events
                self._calendar_temp_overrides.clear()
                self._calendar_mode_overrides.clear()
                
                # Parse
                parsed = parse_calendar_event(current_event["summary"])
                
                # Apply Global Settings
                if parsed["global_preset"]:
                    await self.async_set_global_preset(parsed["global_preset"])
                    
                if parsed["global_temperature"]:
                    for zone in self.zones:
                        climate_id = make_zone_entity_id(zone[CONF_ZONE_NAME])
                        # Set temp temporarily
                        self._calendar_temp_overrides[climate_id] = parsed["global_temperature"]
                        
                # Apply Zone Overrides
                for zone_name, override in parsed["overrides"].items():
                    # Find real entity_id
                    climate_id = None
                    for z in self.zones:
                        if z[CONF_ZONE_NAME].lower() == zone_name:
                            climate_id = make_zone_entity_id(z[CONF_ZONE_NAME])
                            break
                            
                    if not climate_id:
                        continue
                        
                    # Modes
                    if override.mode:
                        if override.is_permanent:
                            zone_select = self._select_entities.get(f"zone_mode_{climate_id}")
                            if zone_select:
                                await zone_select.async_select_option(override.mode)
                        else:
                            self._calendar_mode_overrides[climate_id] = override.mode
                            
                    # Temperatures
                    if override.temperature is not None:
                        if override.is_permanent:
                            # Save permanently to current preset
                            if self._current_global_preset:
                                if self._current_global_preset not in self._presets:
                                    self._presets[self._current_global_preset] = {}
                                if climate_id not in self._presets[self._current_global_preset]:
                                    self._presets[self._current_global_preset][climate_id] = {}
                                self._presets[self._current_global_preset][climate_id]["target_temp"] = override.temperature
                                await self._async_save_presets_storage()
                        else:
                            # Save temporarily
                            self._calendar_temp_overrides[climate_id] = override.temperature
                            
                # Trigger a refresh of climate entities
                for cb in self._climate_callbacks.values():
                    cb()
        else:
            if self._calendar_active_event_id is not None:
                _LOGGER.info("Calendar Event Ended. Restoring base state.")
                self._calendar_active_event_id = None
                self._calendar_temp_overrides.clear()
                self._calendar_mode_overrides.clear()
                
                if self._pre_calendar_preset is not None:
                    await self.async_set_global_preset(self._pre_calendar_preset)
                    self._pre_calendar_preset = None
                    
                for cb in self._climate_callbacks.values():
                    cb()

        # 2. Process Smart Start (Next Event)
        # Check if next event requires pre-heating
        if next_event:
            start_time = dt_util.parse_datetime(next_event["start"])
            if start_time:
                parsed_next = parse_calendar_event(next_event["summary"])
                # We only preheat if there is a target temperature shift
                # For each zone, calculate if we need to start
                for zone in self.zones:
                    climate_id = make_zone_entity_id(zone[CONF_ZONE_NAME])
                    target = None
                    
                    # Does next event have specific temp override?
                    zone_name_lower = zone[CONF_ZONE_NAME].lower()
                    if zone_name_lower in parsed_next["overrides"]:
                        target = parsed_next["overrides"][zone_name_lower].temperature
                        
                    if target is None and parsed_next["global_temperature"]:
                        target = parsed_next["global_temperature"]
                        
                    if target is None and parsed_next["global_preset"]:
                        # Look up base preset temp for this zone
                        target = self._presets.get(parsed_next["global_preset"], {}).get(climate_id, {}).get("target_temp")
                        
                    if target is not None:
                        current_temp = None
                        state = self.hass.states.get(climate_id)
                        if state:
                            current_temp = state.attributes.get("current_temperature")
                            
                        if current_temp is not None and current_temp < target:
                            # We need to heat. Calculate time.
                            thermal_model = self._thermal_models.get(climate_id)
                            if thermal_model and thermal_model.heating_rate > 0.05: # At least 0.05 deg/hour
                                delta_t = target - current_temp
                                hours_needed = delta_t / thermal_model.heating_rate
                                time_needed = timedelta(hours=hours_needed)
                                
                                if now + time_needed >= start_time:
                                    _LOGGER.info("Smart Start Triggered for %s! Target: %.1f, Need: %s", climate_id, target, time_needed)
                                    # Override current target temp temporarily
                                    self._calendar_temp_overrides[climate_id] = target
                                    # Wake up zone if in Sleep/Eco
                                    if self._calendar_mode_overrides.get(climate_id) == "off":
                                        del self._calendar_mode_overrides[climate_id]
                                    if climate_id in self._climate_callbacks:
                                        self._climate_callbacks[climate_id]()

    def _get_zone(self, climate_entity: str) -> dict | None:
        """Get zone config by climate entity ID."""
        for zone in self.zones:
            if make_zone_entity_id(zone[CONF_ZONE_NAME]) == climate_entity:
                return zone
        return None

    def set_min_cycle_on(self, value: int) -> None:
        """Set the min cycle on time (minutes)."""
        self._min_cycle_on = value
        self._boiler_pwm.set_params(min_on=value * 60)
        
    def set_min_cycle_off(self, value: int) -> None:
        """Set the min cycle off time (minutes)."""
        self._min_cycle_off = value
        self._boiler_pwm.set_params(min_off=value * 60)
        
    def set_valve_delay(self, value: int) -> None:
        """Set the valve delay time (seconds)."""
        self._valve_delay = value

    async def _async_pwm_tick(self, now: datetime) -> None:
        """Periodic PWM tick for boiler (Peak Load)."""
        if not self._master_state or self._anti_seize_running:
            return
            
        # Phase 4: Calculate Peak Demand
        peak_demand = 0.0
        for zone in self.zones:
            climate_id = make_zone_entity_id(zone[CONF_ZONE_NAME])
            mode = self.get_zone_mode(climate_id)
            if mode != ZONE_MODE_PRIMARY:
                continue
            demand = self.get_zone_demand(climate_id)
            if demand > peak_demand:
                peak_demand = demand
                
        # Feed Peak Load to PWM Engine
        wanted_state = self._boiler_pwm.calculate(peak_demand)
        
        boiler_state = self.hass.states.get(self.boiler_switch)
        current_boiler_on = boiler_state is not None and boiler_state.state == STATE_ON
        
        # Track activity for anti-seize
        if current_boiler_on or peak_demand > 0:
            self._last_active_time = time.time()
            
        if wanted_state and not current_boiler_on:
            # Hard lock: prevent turning ON if min_cycle_off hasn't elapsed
            time_since_change = time.time() - self._last_boiler_change
            min_off_sec = self._min_cycle_off * 60
            if time_since_change < min_off_sec:
                _LOGGER.debug("PWM Tick: Boiler wants to turn ON, but min_cycle_off (%.0fs) hasn't elapsed. Waiting...", min_off_sec)
                return
                
            _LOGGER.debug("PWM Tick: Boiler → ON (Peak Demand: %.1f%%)", peak_demand)
            
            # BOILER SAFETY: Check if TRVs are physically open (>10%)
            trvs_ready = False
            for zone in self.zones:
                climate_id = make_zone_entity_id(zone[CONF_ZONE_NAME])
                mode = self.get_zone_mode(climate_id)
                if mode == ZONE_MODE_PRIMARY and self.get_zone_demand(climate_id) > 0:
                    trv_list = zone.get(CONF_ZONE_CLIMATES) or []
                    for trv in trv_list:
                        trv_state = self.hass.states.get(trv)
                        if trv_state:
                            position = None
                            for attr in ["position", "valve_position", "pi_heating_demand", "heating_demand", "valve_state"]:
                                if attr in trv_state.attributes:
                                    position = trv_state.attributes[attr]
                                    break
                            if position is not None:
                                try:
                                    if float(position) > 10.0:
                                        trvs_ready = True
                                        break
                                except ValueError:
                                    pass
                            else:
                                # Assume ready if TRV doesn't expose position
                                trvs_ready = True
                                break
                if trvs_ready:
                    break
                    
            if not trvs_ready and any((zone.get(CONF_ZONE_CLIMATES) or []) for zone in self.zones):
                _LOGGER.warning("PWM Tick: Boiler wants to turn ON, but no TRVs are open > 10%. Delaying boiler ignition.")
                return

            if self._valve_delay > 0:
                if not self._pending_boiler_task:
                    _LOGGER.debug("Waiting %s seconds for valves to open...", self._valve_delay)
                    self._schedule_boiler_check(self._valve_delay, True)
            else:
                await self._force_boiler_on()
        elif not wanted_state:
            # Hard lock: prevent turning OFF if min_cycle_on hasn't elapsed
            # (unless it's already off, then we just ensure pending tasks are cancelled)
            time_since_change = time.time() - self._last_boiler_change
            min_on_sec = self._min_cycle_on * 60
            if current_boiler_on and time_since_change < min_on_sec:
                _LOGGER.debug("PWM Tick: Boiler wants to turn OFF, but min_cycle_on (%.0fs) hasn't elapsed. Waiting...", min_on_sec)
                return
                
            # Cancel any pending valve-delay task even if boiler isn't on yet
            if self._pending_boiler_task:
                _LOGGER.debug("PWM Tick: Cancelling pending valve-delay task (Peak Demand: %.1f%%)", peak_demand)
                self._pending_boiler_task.cancel()
                self._pending_boiler_task = None
            if current_boiler_on:
                _LOGGER.debug("PWM Tick: Boiler → OFF (Peak Demand: %.1f%%)", peak_demand)
                await self._force_boiler_off()

    async def _async_update_boiler(self, emergency_off: bool = False) -> None:
        """Fallback for emergency off and anti-seize."""
        if emergency_off:
            _LOGGER.debug("Emergency OFF triggered. Stopping boiler.")
            if self._pending_boiler_task:
                self._pending_boiler_task.cancel()
                self._pending_boiler_task = None
            await self._force_boiler_off()

    def _schedule_boiler_check(self, delay_seconds: float, turn_on: bool) -> None:
        """Schedule a delayed boiler update (used for valve delay)."""
        if self._pending_boiler_task:
            self._pending_boiler_task.cancel()

        async def _delayed_check():
            try:
                await asyncio.sleep(delay_seconds)
                if turn_on:
                    await self._force_boiler_on()
                else:
                    await self._force_boiler_off()
            except asyncio.CancelledError:
                pass

        self._pending_boiler_task = self.hass.async_create_task(_delayed_check())

    async def _force_boiler_on(self) -> None:
        """Actually turn the boiler on and set locks."""
        if self._pending_boiler_task:
            self._pending_boiler_task.cancel()
            self._pending_boiler_task = None

        await self.hass.services.async_call(
            "switch",
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: self.boiler_switch},
            blocking=False,
        )
        self._last_boiler_change = time.time()
        _LOGGER.debug("Boiler forced ON")

    async def _force_boiler_off(self) -> None:
        """Actually turn the boiler off and set locks."""
        if self._pending_boiler_task:
            self._pending_boiler_task.cancel()
            self._pending_boiler_task = None

        await self.hass.services.async_call(
            "switch",
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: self.boiler_switch},
            blocking=False,
        )
        self._last_boiler_change = time.time()
        _LOGGER.debug("Boiler forced OFF")

    async def async_apply_master_on(self) -> None:
        """Master turned ON: set heat mode for enabled zones, off for disabled."""
        _LOGGER.debug("Master ON → applying to all zones")
        for zone in self.zones:
            climate_id = make_zone_entity_id(zone[CONF_ZONE_NAME])
            mode = self._zone_modes.get(climate_id, ZONE_MODE_PRIMARY)
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
        await self._async_update_boiler(emergency_off=True)



    async def _async_set_hvac_mode(self, climate_entity: str, mode: str) -> None:
        """Set HVAC mode on a climate entity."""
        state = self.hass.states.get(climate_entity)
        if state is None:
            _LOGGER.warning("Climate entity %s not found, skipping", climate_entity)
            return

        current_mode = state.state
        if current_mode == mode:
            return  # Already in correct mode

        _LOGGER.debug("Setting %s → hvac_mode: %s", climate_entity, mode)
        await self.hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            {ATTR_ENTITY_ID: climate_entity, ATTR_HVAC_MODE: mode},
            blocking=False,
        )

    @callback
    def _async_check_anti_seize(self, now: datetime) -> None:
        """Check if we need to run the anti-seize routine."""
        if not self.get_persistent_data(KEY_ANTI_SEIZE_ENABLED, False):
            return
            
        if self._anti_seize_running:
            return
            
        idle_seconds = time.time() - self._last_active_time
        idle_days = idle_seconds / 86400.0
        anti_seize_idle_days = self.get_persistent_data(KEY_ANTI_SEIZE_IDLE_DAYS, 15)
        
        if idle_days >= anti_seize_idle_days:
            _LOGGER.info("Anti-seize triggered. System idle for %.1f days (threshold: %d days).", idle_days, anti_seize_idle_days)
            self.hass.async_create_task(self._async_execute_anti_seize())

    async def _async_execute_anti_seize(self) -> None:
        """Execute the anti-seize routine."""
        self._anti_seize_running = True
        
        try:
            _LOGGER.info("Starting Anti-seize routine...")
            
            # 1. Save current state of all enabled zones and open them
            self._pre_anti_seize_state.clear()
            zones_to_open = []
            
            for zone in self.zones:
                climate_id = make_zone_entity_id(zone[CONF_ZONE_NAME])
                # Check if zone has anti-seize enabled
                if not zone.get(CONF_ZONE_ANTI_SEIZE, True):
                    _LOGGER.debug("Skipping zone %s (anti-seize disabled)", climate_id)
                    continue
                    
                state = self.hass.states.get(climate_id)
                if state:
                    self._pre_anti_seize_state[climate_id] = state.state
                    zones_to_open.append(climate_id)
            
            if not zones_to_open:
                _LOGGER.info("No zones enabled for anti-seize. Skipping routine.")
                self._last_active_time = time.time()
                return
                
            _LOGGER.debug("Opening zones: %s", zones_to_open)
            for climate_id in zones_to_open:
                # To force open, we set to Heat. If it's a TRV, it will open. If it's a VT, it will turn on relay.
                # Ideally, we should also set temperature to max, but just turning to HEAT usually opens it fully 
                # or enough to move the mechanism.
                await self._async_set_hvac_mode(climate_id, HVAC_MODE_HEAT)
                
            # 2. Wait for valves to open
            if self._valve_delay > 0:
                _LOGGER.debug("Waiting %s seconds for valves to open...", self._valve_delay)
                await asyncio.sleep(self._valve_delay)
                
            # 3. Fire boiler if configured
            anti_seize_boiler = self.get_persistent_data(CONF_ANTI_SEIZE_BOILER, False)
            if anti_seize_boiler:
                _LOGGER.debug("Activating boiler for anti-seize...")
                await self.hass.services.async_call(
                    "switch",
                    SERVICE_TURN_ON,
                    {ATTR_ENTITY_ID: self.boiler_switch},
                    blocking=False,
                )
                
            # 4. Wait for the duration
            anti_seize_duration = self.get_persistent_data(KEY_ANTI_SEIZE_DURATION, 2)
            duration_seconds = anti_seize_duration * 60
            _LOGGER.debug("Running anti-seize for %d secondi...", duration_seconds)
            await asyncio.sleep(duration_seconds)
            
            # 5. Turn off boiler if we turned it on
            if anti_seize_boiler:
                _LOGGER.debug("Deactivating boiler after anti-seize...")
                await self.hass.services.async_call(
                    "switch",
                    SERVICE_TURN_OFF,
                    {ATTR_ENTITY_ID: self.boiler_switch},
                    blocking=False,
                )
                
            # 6. Restore all zones
            _LOGGER.debug("Restoring zones to pre-anti-seize state...")
            for climate_id, old_state in self._pre_anti_seize_state.items():
                await self._async_set_hvac_mode(climate_id, old_state)
                    
            _LOGGER.info("Anti-seize routine completed successfully.")
            self._last_active_time = time.time()
            
        except Exception as e:
            _LOGGER.error("Error during anti-seize routine: %s", e)
        finally:
            self._anti_seize_running = False

