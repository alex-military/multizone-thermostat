"""Coordinator for Multizone Thermostat: handles all heating logic."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

import homeassistant.util.dt as dt_util

from homeassistant.components.climate import (
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
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.storage import Store

from .const import (
    CONF_BOILER_SWITCH,
    CONF_ZONE_CLIMATE,
    CONF_ZONE_TRV_SYNC,
    CONF_ZONE_WINDOW_SENSOR,
    CONF_ZONES,
    DOMAIN,
    HVAC_ACTION_HEATING,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    PRESET_MANUAL,
    PRESET_OFF,
)

_LOGGER = logging.getLogger(__name__)

ATTR_HVAC_ACTION = "hvac_action"
ATTR_HVAC_MODE = "hvac_mode"
ATTR_PRESET_MODE = "preset_mode"

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.window_states"


class MultizoneCoordinator:
    """Central coordinator that manages all heating logic."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        boiler_switch: str,
        zones: list[dict],
    ) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry_id = entry_id
        self.boiler_switch = boiler_switch
        self.zones = zones
        
        # These will be updated by the number entities
        self._min_cycle_on = 5
        self._min_cycle_off = 5
        self._valve_delay = 0

        # State: master on/off and per-zone on/off
        # Loaded/saved externally by switch entities using RestoreState
        self._master_state: bool = False
        self._zone_states: dict[str, bool] = {
            z[CONF_ZONE_CLIMATE]: True for z in zones
        }

        self._boiler_locked_on_until: datetime | None = None
        self._boiler_locked_off_until: datetime | None = None
        self._pending_boiler_task: asyncio.Task | None = None

        self._unsub_listeners: list = []
        self._switch_entities: dict[str, Any] = {}  # entity_id -> switch object
        
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._pre_window_state: dict[str, bool] = {}

    async def async_load_storage(self) -> None:
        """Load stored window states."""
        stored = await self._store.async_load()
        if stored and isinstance(stored, dict):
            self._pre_window_state = stored
            _LOGGER.debug("Loaded pre_window_state from storage: %s", self._pre_window_state)

    async def _async_save_storage(self) -> None:
        """Save window states to storage."""
        await self._store.async_save(self._pre_window_state)

    def register_switch(self, climate_or_master: str, switch_entity: Any) -> None:
        """Register a switch entity so coordinator can notify state changes."""
        self._switch_entities[climate_or_master] = switch_entity

    def set_master_state(self, state: bool) -> None:
        """Set master state (called by master switch entity)."""
        self._master_state = state

    def set_zone_state(self, climate_entity: str, state: bool) -> None:
        """Set zone state (called by zone switch entity)."""
        self._zone_states[climate_entity] = state

    def get_master_state(self) -> bool:
        """Get current master state."""
        return self._master_state

    def get_zone_state(self, climate_entity: str) -> bool:
        """Get current zone state."""
        return self._zone_states.get(climate_entity, True)

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
        
        if new_state is None:
            return
            
        # Find which zone this sensor belongs to
        zone = next((z for z in self.zones if z.get(CONF_ZONE_WINDOW_SENSOR) == sensor_id), None)
        if not zone:
            return
            
        climate_id = zone[CONF_ZONE_CLIMATE]
        switch_entity = self._switch_entities.get(climate_id)
        
        if new_state.state == STATE_ON:
            # Window OPENED
            _LOGGER.debug("Window opened (%s), bypassing zone %s", sensor_id, climate_id)
            # Save current state if not already saved (don't overwrite if multiple sensors?)
            if climate_id not in self._pre_window_state:
                current_state = self.get_zone_state(climate_id)
                self._pre_window_state[climate_id] = current_state
                self.hass.async_create_task(self._async_save_storage())
            
            # Turn off the zone via the switch entity (updates UI and coordinator)
            if switch_entity and switch_entity.is_on:
                self.hass.async_create_task(switch_entity.async_turn_off())
                
        elif new_state.state == "off":
            # Window CLOSED
            _LOGGER.debug("Window closed (%s), restoring zone %s", sensor_id, climate_id)
            if climate_id in self._pre_window_state:
                was_on = self._pre_window_state.pop(climate_id)
                self.hass.async_create_task(self._async_save_storage())
                
                # If it was ON, restore it to ON
                if was_on and switch_entity and not switch_entity.is_on:
                    self.hass.async_create_task(switch_entity.async_turn_on())

    def _get_zone(self, climate_entity: str) -> dict | None:
        """Get zone config by climate entity ID."""
        for zone in self.zones:
            if zone[CONF_ZONE_CLIMATE] == climate_entity:
                return zone
        return None

    def set_min_cycle_on(self, value: int) -> None:
        """Set the min cycle on time (minutes)."""
        self._min_cycle_on = value
        
    def set_min_cycle_off(self, value: int) -> None:
        """Set the min cycle off time (minutes)."""
        self._min_cycle_off = value
        
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

        any_heating = False
        for zone in self.zones:
            climate_id = zone[CONF_ZONE_CLIMATE]
            state = self.hass.states.get(climate_id)
            if state is None:
                continue
            if state.attributes.get(ATTR_HVAC_ACTION, "") == HVAC_ACTION_HEATING:
                any_heating = True
                break

        boiler_state = self.hass.states.get(self.boiler_switch)
        current_boiler_on = boiler_state is not None and boiler_state.state == STATE_ON

        if any_heating and not current_boiler_on:
            # Want to turn ON
            if self._boiler_locked_off_until and now < self._boiler_locked_off_until:
                delay = (self._boiler_locked_off_until - now).total_seconds()
                _LOGGER.debug("Boiler is locked OFF. Retrying in %s seconds.", delay)
                self._schedule_boiler_check(delay)
                return

            _LOGGER.debug("Boiler → ON (at least one zone heating)")
            if self._valve_delay > 0:
                _LOGGER.debug("Waiting %s seconds for valves to open...", self._valve_delay)
                self._schedule_boiler_check(self._valve_delay, skip_lock_check=True)
                return
            else:
                await self._force_boiler_on()

        elif not any_heating and current_boiler_on:
            # Want to turn OFF
            if self._boiler_locked_on_until and now < self._boiler_locked_on_until:
                delay = (self._boiler_locked_on_until - now).total_seconds()
                _LOGGER.debug("Boiler is locked ON. Retrying in %s seconds.", delay)
                self._schedule_boiler_check(delay)
                return

            _LOGGER.debug("Boiler → OFF (no zones heating)")
            await self._force_boiler_off()

    def _schedule_boiler_check(self, delay_seconds: float, skip_lock_check: bool = False) -> None:
        """Schedule a delayed boiler update."""
        if self._pending_boiler_task:
            self._pending_boiler_task.cancel()

        async def _delayed_check():
            try:
                await asyncio.sleep(delay_seconds)
                if skip_lock_check:
                    # Time's up for valve delay, turn on now
                    await self._force_boiler_on()
                else:
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
        # Climate feature flag for preset mode is 16
        if not (supported_features & 16):
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
            zone_enabled = self._zone_states.get(climate_id, True)
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

    async def async_apply_zone_on(self, climate_entity: str) -> None:
        """Zone switch turned ON (only if master is ON)."""
        # If user manually turns on, clear pre_window_state so it doesn't revert later
        if climate_entity in self._pre_window_state:
            self._pre_window_state.pop(climate_entity)
            await self._async_save_storage()
            
        if self._master_state:
            _LOGGER.debug("Zone ON: %s", climate_entity)
            await self._async_set_hvac_mode(climate_entity, HVAC_MODE_HEAT)

    async def async_apply_zone_off(self, climate_entity: str) -> None:
        """Zone switch turned OFF."""
        _LOGGER.debug("Zone OFF: %s", climate_entity)
        await self._async_set_hvac_mode(climate_entity, HVAC_MODE_OFF)

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

    def update_zones(self, zones: list[dict], boiler_switch: str) -> None:
        """Update zones and boiler switch when options change."""
        self.zones = zones
        self.boiler_switch = boiler_switch
        # Reset zone states for new zones
        for zone in zones:
            climate_id = zone[CONF_ZONE_CLIMATE]
            if climate_id not in self._zone_states:
                self._zone_states[climate_id] = True
        # Re-setup listeners
        self.async_teardown_listeners()
        self.async_setup_listeners()
