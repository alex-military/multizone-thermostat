"""Master HVAC operation and whole-house coordination for Multizone Thermostat."""
from __future__ import annotations
import inspect

import logging
from typing import Any

from homeassistant.components.climate import (
    DOMAIN as CLIMATE_DOMAIN,
    HVACMode,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
    ATTR_HVAC_MODE,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE

from .const import (
    CONF_ZONE_NAME,
    CONF_MASTER_HVAC_MODE,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    HVAC_MODE_OFF,
    ZONE_MODE_BYPASS,
    make_zone_entity_id,
)

_LOGGER = logging.getLogger(__name__)


class MasterController:
    """Coordinates master whole-house HVAC operation (heat, cool, master on, master off)."""

    def __init__(self, coordinator: Any) -> None:
        """Initialize the MasterController."""
        self.coordinator = coordinator
        self.hass = coordinator.hass

    async def async_set_master_hvac_mode(self, mode: str) -> None:
        """Set master operation mode ('heat' or 'cool') and coordinate whole-house operation."""
        if mode not in (HVAC_MODE_HEAT, HVAC_MODE_COOL):
            _LOGGER.warning("Invalid master HVAC mode: %s", mode)
            return

        self.coordinator.master_hvac_mode = mode
        await self.coordinator.async_set_persistent_data(CONF_MASTER_HVAC_MODE, mode)
        _LOGGER.info("Master HVAC mode set to '%s'", mode)

        if "master_operation_mode" in self.coordinator._select_entities:
            self.coordinator._select_entities["master_operation_mode"].async_write_ha_state()

        if "global_preset" in self.coordinator._select_entities:
            self.coordinator._select_entities["global_preset"].async_write_ha_state()

        for zone in self.coordinator.zones:
            name = zone.get(CONF_ZONE_NAME)
            if not name:
                continue
            cid = make_zone_entity_id(name)
            t = self.coordinator.zone_manager.get_preset_temperature(
                self.coordinator.zone_manager.current_global_preset, cid, mode
            )
            if t is not None and (mode != HVAC_MODE_COOL or self.coordinator.can_zone_cool(cid)):
                t_val = float(t)
                climate_ent = getattr(self.coordinator, "_climate_entities", {}).get(cid)
                if climate_ent is not None and hasattr(climate_ent, "_target_temperature"):
                    climate_ent._target_temperature = t_val
                sched_mgr = getattr(self.coordinator, "schedule_manager", None)
                if sched_mgr and getattr(sched_mgr, "scheduler_enabled", False) is True:
                    if self.coordinator.zone_manager.current_global_preset == "manual":
                        sched_mgr.record_manual_override(cid, t_val)

        if self.coordinator.get_master_state():
            if mode == HVAC_MODE_COOL:
                for zone in self.coordinator.zones:
                    name = zone.get(CONF_ZONE_NAME)
                    if not name:
                        continue
                    cid = make_zone_entity_id(name)
                    z_mode = self.coordinator.zone_manager.get_zone_mode(cid)
                    if self.coordinator.can_zone_cool(cid) and z_mode != ZONE_MODE_BYPASS:
                        await self.async_set_hvac_mode(cid, HVAC_MODE_COOL)
                        t = self.coordinator.zone_manager.get_preset_temperature(
                            self.coordinator.zone_manager.current_global_preset, cid, HVAC_MODE_COOL
                        )
                        if t is not None:
                            await self.hass.services.async_call(
                                CLIMATE_DOMAIN,
                                SERVICE_SET_TEMPERATURE,
                                {ATTR_ENTITY_ID: cid, ATTR_TEMPERATURE: float(t)},
                                blocking=True,
                            )
                    else:
                        await self.async_set_hvac_mode(cid, HVAC_MODE_OFF)
            else:
                for zone in self.coordinator.zones:
                    name = zone.get(CONF_ZONE_NAME)
                    if not name:
                        continue
                    cid = make_zone_entity_id(name)
                    z_mode = self.coordinator.zone_manager.get_zone_mode(cid)
                    if z_mode != ZONE_MODE_BYPASS:
                        await self.async_set_hvac_mode(cid, HVAC_MODE_HEAT)
                        t = self.coordinator.zone_manager.get_preset_temperature(
                            self.coordinator.zone_manager.current_global_preset, cid, HVAC_MODE_HEAT
                        )
                        if t is not None:
                            await self.hass.services.async_call(
                                CLIMATE_DOMAIN,
                                SERVICE_SET_TEMPERATURE,
                                {ATTR_ENTITY_ID: cid, ATTR_TEMPERATURE: float(t)},
                                blocking=True,
                            )
                    else:
                        await self.async_set_hvac_mode(cid, HVAC_MODE_OFF)

        if hasattr(self.coordinator, "_master_switch") and self.coordinator._master_switch:
            self.coordinator._master_switch.async_write_ha_state()

        await self.coordinator.async_update_all_climates()

    async def async_apply_master_on(self) -> None:
        """Master turned ON: set current master HVAC mode (heat or cool) for capable enabled zones."""
        _LOGGER.debug("Master ON (mode: %s) → applying to all zones", self.coordinator.master_hvac_mode)
        if self.coordinator.master_hvac_mode == HVAC_MODE_COOL:
            for zone in self.coordinator.zones:
                cid = make_zone_entity_id(zone[CONF_ZONE_NAME])
                mode = self.coordinator.zone_manager.get_zone_mode(cid)
                if self.coordinator.can_zone_cool(cid) and mode != ZONE_MODE_BYPASS:
                    await self.async_set_hvac_mode(cid, HVAC_MODE_COOL)
                    t = self.coordinator.zone_manager.get_preset_temperature(
                        self.coordinator.zone_manager.current_global_preset, cid, HVAC_MODE_COOL
                    )
                    if t is not None:
                        await self.hass.services.async_call(
                            CLIMATE_DOMAIN,
                            SERVICE_SET_TEMPERATURE,
                            {ATTR_ENTITY_ID: cid, ATTR_TEMPERATURE: float(t)},
                            blocking=True,
                        )
                else:
                    await self.async_set_hvac_mode(cid, HVAC_MODE_OFF)
        else:
            for zone in self.coordinator.zones:
                cid = make_zone_entity_id(zone[CONF_ZONE_NAME])
                mode = self.coordinator.zone_manager.get_zone_mode(cid)
                if mode != ZONE_MODE_BYPASS:
                    await self.async_set_hvac_mode(cid, HVAC_MODE_HEAT)
                    t = self.coordinator.zone_manager.get_preset_temperature(
                        self.coordinator.zone_manager.current_global_preset, cid, HVAC_MODE_HEAT
                    )
                    if t is not None:
                        await self.hass.services.async_call(
                            CLIMATE_DOMAIN,
                            SERVICE_SET_TEMPERATURE,
                            {ATTR_ENTITY_ID: cid, ATTR_TEMPERATURE: float(t)},
                            blocking=True,
                        )
                else:
                    await self.async_set_hvac_mode(cid, HVAC_MODE_OFF)

    async def async_apply_master_off(self) -> None:
        """Master turned OFF: turn off all zones and boiler."""
        _LOGGER.debug("Master OFF → turning off all zones")
        for zone in self.coordinator.zones:
            climate_id = make_zone_entity_id(zone[CONF_ZONE_NAME])
            await self.async_set_hvac_mode(climate_id, HVAC_MODE_OFF)

        # Boiler will auto-turn off via state change listener,
        # but we also force it off here for safety ignoring locks
        await self.coordinator.plant_orchestrator.boiler_backend.async_emergency_off()
        hp_backend = getattr(self.coordinator, "heat_pump_backend", None) or getattr(
            self.coordinator.plant_orchestrator, "heat_pump_backend", None
        )
        if hp_backend is not None and hasattr(hp_backend, "async_emergency_off"):
            res = hp_backend.async_emergency_off()
            if inspect.isawaitable(res):
                await res

    async def async_set_hvac_mode(self, climate_entity: str, mode: str) -> None:
        """Set HVAC mode on a climate entity."""
        climate_ent = getattr(self.coordinator, "_climate_entities", {}).get(climate_entity)
        if climate_ent is not None:
            if hasattr(HVACMode, mode.upper()):
                climate_ent._hvac_mode = HVACMode(mode)
            else:
                climate_ent._hvac_mode = mode

        state = self.hass.states.get(climate_entity) if hasattr(self.hass, "states") and self.hass.states else None
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
