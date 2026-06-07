"""Coordinator for Multizone Thermostat: handles all heating logic."""
from __future__ import annotations

import logging
from typing import Any

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

from .const import (
    CONF_BOILER_SWITCH,
    CONF_ZONE_CLIMATE,
    CONF_ZONE_TRV_SYNC,
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

        # State: master on/off and per-zone on/off
        # Loaded/saved externally by switch entities using RestoreState
        self._master_state: bool = False
        self._zone_states: dict[str, bool] = {
            z[CONF_ZONE_CLIMATE]: True for z in zones
        }

        self._unsub_listeners: list = []
        self._switch_entities: dict[str, Any] = {}  # entity_id -> switch object

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

    def _get_zone(self, climate_entity: str) -> dict | None:
        """Get zone config by climate entity ID."""
        for zone in self.zones:
            if zone[CONF_ZONE_CLIMATE] == climate_entity:
                return zone
        return None

    async def _async_update_boiler(self) -> None:
        """Turn boiler ON if any zone is heating, OFF if all are idle/off."""
        any_heating = False

        for zone in self.zones:
            climate_id = zone[CONF_ZONE_CLIMATE]
            state = self.hass.states.get(climate_id)
            if state is None:
                continue
            hvac_action = state.attributes.get(ATTR_HVAC_ACTION, "")
            if hvac_action == HVAC_ACTION_HEATING:
                any_heating = True
                break

        boiler_state = self.hass.states.get(self.boiler_switch)
        current_boiler_on = boiler_state is not None and boiler_state.state == STATE_ON

        if any_heating and not current_boiler_on:
            _LOGGER.debug("Boiler → ON (at least one zone heating)")
            await self.hass.services.async_call(
                "switch",
                SERVICE_TURN_ON,
                {ATTR_ENTITY_ID: self.boiler_switch},
                blocking=False,
            )
        elif not any_heating and current_boiler_on:
            _LOGGER.debug("Boiler → OFF (no zones heating)")
            await self.hass.services.async_call(
                "switch",
                SERVICE_TURN_OFF,
                {ATTR_ENTITY_ID: self.boiler_switch},
                blocking=False,
            )

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
        # but we also force it off here for safety
        await self.hass.services.async_call(
            "switch",
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: self.boiler_switch},
            blocking=False,
        )

    async def async_apply_zone_on(self, climate_entity: str) -> None:
        """Zone switch turned ON (only if master is ON)."""
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
