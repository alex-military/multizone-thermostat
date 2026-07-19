"""Coordinator for Multizone Thermostat: handles all heating logic."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, time
import logging
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
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.storage import Store

from .const import (
    CONF_ZONE_CLIMATE,
    CONF_ZONE_TRV_SYNC,
    CONF_ZONE_WINDOW_SENSOR,
    DOMAIN,
    GLOBAL_PRESET_MANUAL,
    HVAC_ACTION_HEATING,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    PRESET_MANUAL,
    PRESET_OFF,
    CONF_PRESENCE_SENSOR,
    KEY_NIGHT_TIME,
    KEY_MORNING_TIME,
    KEY_AUTO_NIGHT_MODE,
    KEY_GEOFENCING_TOGGLE,
    KEY_PRE_AWAY_PRESET,
    KEY_PRE_NIGHT_PRESET,
    GLOBAL_PRESET_SLEEP,
    GLOBAL_PRESET_AWAY,
    GLOBAL_PRESET_COMFORT,
    ZONE_MODE_PRIMARY,
    ZONE_MODE_SECONDARY,
    ZONE_MODE_BYPASS,
)

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
        entry_id: str,
        boiler_switch: str,
        zones: list[dict],
        presence_sensor: str | None = None,
    ) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry_id = entry_id
        self.boiler_switch = boiler_switch
        self.zones = zones
        self.presence_sensor = presence_sensor
        
        # These will be updated by the number entities
        self._min_cycle_on = 5
        self._min_cycle_off = 5
        self._valve_delay = 0

        # State: master on/off and per-zone on/off
        # Loaded/saved externally by entities using RestoreState
        self._master_state: bool = False
        self._zone_modes: dict[str, str] = {
            z[CONF_ZONE_CLIMATE]: ZONE_MODE_PRIMARY for z in zones
        }

        self._boiler_locked_on_until: datetime | None = None
        self._boiler_locked_off_until: datetime | None = None
        self._pending_boiler_task: asyncio.Task | None = None

        self._unsub_listeners: list = []
        self._select_entities: dict[str, Any] = {}  # key -> select object
        
        self._store = Store(hass, WINDOW_STORAGE_VERSION, WINDOW_STORAGE_KEY)
        self._pre_window_state: dict[str, bool] = {}

        self._preset_store = Store(hass, PRESET_STORAGE_VERSION, PRESET_STORAGE_KEY)
        self._presets: dict[str, dict[str, dict[str, Any]]] = {}
        self._current_global_preset: str = GLOBAL_PRESET_MANUAL
        
        self._settings_store = Store(hass, SETTINGS_STORAGE_VERSION, SETTINGS_STORAGE_KEY)
        self._settings: dict[str, Any] = {}
        
        self._last_night_trigger_date: datetime.date | None = None
        self._last_morning_trigger_date: datetime.date | None = None

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

    async def _async_save_storage(self) -> None:
        """Save window states to storage."""
        await self._store.async_save(self._pre_window_state)

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
        """Get current zone mode."""
        return self._zone_modes.get(climate_entity, ZONE_MODE_PRIMARY)

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
        climate_entities = [z[CONF_ZONE_CLIMATE] for z in self.zones]

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

    @callback
    def async_teardown_listeners(self) -> None:
        """Remove all state change listeners."""
        for unsub in self._unsub_listeners:
            unsub()
        self._unsub_listeners.clear()

    @callback
    def _async_on_climate_state_changed(self, event: Event) -> None:
        """Handle climate state changes → manage boiler and TRV preset sync."""
        entity_id = event.data.get("entity_id")
        new_state = event.data.get("new_state")

        if new_state is None:
            return

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

        # 1. Manage boiler demand
        self.hass.async_create_task(self._async_update_boiler())

        # 2. TRV preset sync (if enabled for this zone)
        zone = self._get_zone(entity_id)
        if zone and zone.get(CONF_ZONE_TRV_SYNC, False):
            self.hass.async_create_task(
                self._async_sync_trv_preset(entity_id, new_state.state)
            )

    @callback
    def _async_on_window_state_changed(self, event: Event) -> None:
        """Handle window sensor state changes → bypass/restore zone."""
        sensor_id = event.data.get("entity_id")
        new_state = event.data.get("new_state")
        
        _LOGGER.error("!!! WINDOW LISTENER FIRED: %s -> %s", sensor_id, new_state.state if new_state else "None")

        if new_state is None:
            return
            
        # Find ALL zones this sensor belongs to
        matching_zones = [z for z in self.zones if z.get(CONF_ZONE_WINDOW_SENSOR) == sensor_id]
        _LOGGER.error("!!! WINDOW LISTENER: Matching zones: %s", matching_zones)
        if not matching_zones:
            return
            
        for zone in matching_zones:
            climate_id = zone[CONF_ZONE_CLIMATE]
            zone_select = self._select_entities.get(f"zone_mode_{climate_id}")
            _LOGGER.error("!!! WINDOW LISTENER: zone_select for %s: %s", climate_id, zone_select)
            
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
                night_time = time(n_hour, n_minute)
                morning_time = time(m_hour, m_minute)
                
                if night_time > morning_time:
                    if now >= night_time or now <= morning_time:
                        is_night = True
                else:
                    if now >= night_time and now <= morning_time:
                        is_night = True
                        
                _LOGGER.error("GEOFENCING DEBUG: night_time=%s, morning_time=%s, now=%s, is_night=%s", night_time, morning_time, now, is_night)
            except Exception as ex:
                _LOGGER.error("GEOFENCING DEBUG EXCEPTION: %s", ex)
                
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
                    _LOGGER.info("Auto Night Mode triggered. Setting Sleep mode.")
                    # Save current preset before going to sleep (only if not already sleep)
                    if self._current_global_preset != GLOBAL_PRESET_SLEEP:
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
                    pre_night = self.get_persistent_data(KEY_PRE_NIGHT_PRESET, GLOBAL_PRESET_COMFORT)
                    _LOGGER.info("Auto Morning Mode triggered. Restoring mode: %s", pre_night)
                    self.hass.async_create_task(self.async_set_global_preset(pre_night))
        except Exception:
            pass

    def _get_zone(self, climate_entity: str) -> dict | None:
        """Get zone config by climate entity ID."""
        for zone in self.zones:
            if zone[CONF_ZONE_CLIMATE] == climate_entity:
                return zone
        return None

    def set_min_cycle_on(self, value: int) -> None:
        """Set the min cycle on time (minutes)."""
        self._min_cycle_on = value
        self._boiler_locked_on_until = None
        self.hass.async_create_task(self._async_update_boiler())
        
    def set_min_cycle_off(self, value: int) -> None:
        """Set the min cycle off time (minutes)."""
        self._min_cycle_off = value
        self._boiler_locked_off_until = None
        self.hass.async_create_task(self._async_update_boiler())
        
    def set_valve_delay(self, value: int) -> None:
        """Set the valve delay time (seconds)."""
        self._valve_delay = value

    async def _async_update_boiler(self, emergency_off: bool = False) -> None:
        """Turn boiler ON if any zone is heating, OFF if all are idle/off."""
        now = dt_util.utcnow()

        if emergency_off:
            _LOGGER.debug("Emergency OFF triggered. Resetting locks and stopping boiler.")
            if self._pending_boiler_task:
                self._pending_boiler_task.cancel()
                self._pending_boiler_task = None
            self._boiler_locked_on_until = None
            self._boiler_locked_off_until = None
            await self._force_boiler_off()
            return

        any_primary_heating = False
        for zone in self.zones:
            climate_id = zone[CONF_ZONE_CLIMATE]
            mode = self.get_zone_mode(climate_id)
            
            # Boiler only turns on if a PRIMARY zone needs heat
            if mode != ZONE_MODE_PRIMARY:
                continue
                
            state = self.hass.states.get(climate_id)
            if state is None:
                continue
            if state.attributes.get(ATTR_HVAC_ACTION, "") == HVAC_ACTION_HEATING:
                any_primary_heating = True
                break

        boiler_state = self.hass.states.get(self.boiler_switch)
        current_boiler_on = boiler_state is not None and boiler_state.state == STATE_ON

        if any_primary_heating and not current_boiler_on:
            # Want to turn ON
            if self._boiler_locked_off_until and now < self._boiler_locked_off_until:
                delay = (self._boiler_locked_off_until - now).total_seconds()
                _LOGGER.debug("Boiler is locked OFF. Retrying in %s seconds.", delay)
                self._schedule_boiler_check(delay)
                return

            _LOGGER.debug("Boiler → ON (at least one zone heating)")
            if self._valve_delay > 0:
                _LOGGER.debug("Waiting %s seconds for valves to open...", self._valve_delay)
                self._schedule_boiler_check(self._valve_delay)
                return
            else:
                await self._force_boiler_on()

        elif not any_primary_heating and current_boiler_on:
            # Want to turn OFF
            if self._boiler_locked_on_until and now < self._boiler_locked_on_until:
                delay = (self._boiler_locked_on_until - now).total_seconds()
                _LOGGER.debug("Boiler is locked ON. Retrying in %s seconds.", delay)
                self._schedule_boiler_check(delay)
                return

            _LOGGER.debug("Boiler → OFF (no zones heating)")
            await self._force_boiler_off()

    def _schedule_boiler_check(self, delay_seconds: float) -> None:
        """Schedule a delayed boiler update (used for min-cycle locks and valve delay)."""
        if self._pending_boiler_task:
            self._pending_boiler_task.cancel()

        async def _delayed_check():
            try:
                await asyncio.sleep(delay_seconds)
                await self._async_update_boiler()
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
        if self._min_cycle_on > 0:
            self._boiler_locked_on_until = dt_util.utcnow() + timedelta(minutes=self._min_cycle_on)

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
        if self._min_cycle_off > 0:
            self._boiler_locked_off_until = dt_util.utcnow() + timedelta(minutes=self._min_cycle_off)

    async def _async_sync_trv_preset(self, climate_entity: str, hvac_mode: str) -> None:
        """Sync TRV preset mode based on HVAC mode."""
        if hvac_mode == HVAC_MODE_HEAT:
            preset = PRESET_MANUAL
        elif hvac_mode == HVAC_MODE_OFF:
            preset = PRESET_OFF
        else:
            return

        state = self.hass.states.get(climate_entity)
        if state is None:
            return

        # Check if climate supports presets
        supported_features = state.attributes.get("supported_features", 0)
        if not (supported_features & ClimateEntityFeature.PRESET_MODE):
            _LOGGER.debug(
                "Climate %s does not support presets, skipping sync", climate_entity
            )
            return

        current_preset = state.attributes.get(ATTR_PRESET_MODE)
        if current_preset == preset:
            return

        _LOGGER.debug(
            "TRV preset sync: %s → %s (hvac_mode: %s)", climate_entity, preset, hvac_mode
        )
        await self.hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_PRESET_MODE,
            {ATTR_ENTITY_ID: climate_entity, ATTR_PRESET_MODE: preset},
            blocking=False,
        )

    async def async_apply_master_on(self) -> None:
        """Master turned ON: set heat mode for enabled zones, off for disabled."""
        _LOGGER.debug("Master ON → applying to all zones")
        for zone in self.zones:
            climate_id = zone[CONF_ZONE_CLIMATE]
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
            climate_id = zone[CONF_ZONE_CLIMATE]
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

