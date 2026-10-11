import logging
from typing import Any

from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.components.climate.const import HVACMode
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN, SERVICE_SET_PRESET_MODE, SERVICE_SET_TEMPERATURE
from homeassistant.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE

from .const import (
    CONF_ZONE_NAME,
    CONF_ZONE_CLIMATES,
    CONF_ZONE_WINDOW_SENSOR,
    CONF_ZONE_TRV_SYNC,
    ZONE_MODE_PRIMARY,
    ZONE_MODE_BYPASS,
    GLOBAL_PRESET_MANUAL,
    make_zone_entity_id,
    KEY_PASSIVE_HEAT_PREFIX,
    CONF_ZONE_ALLOW_PASSIVE_HEAT
)

_LOGGER = logging.getLogger(__name__)

class ZoneManager:
    """
    Responsabilità:
    - Registrazione e stato delle zone
    - Associazione TRV e sync
    - Gestione finestre (bypass)
    - Memorizzazione preset
    """

    def __init__(self, hass: HomeAssistant, coordinator: Any) -> None:
        self.hass = hass
        self.coordinator = coordinator
        self.zones = coordinator.zones
        
        self._zone_modes: dict[str, str] = {
            (z.get("climate_id") or make_zone_entity_id(z.get(CONF_ZONE_NAME, "unnamed"))): ZONE_MODE_PRIMARY 
            for z in self.zones if z.get(CONF_ZONE_NAME)
        }
        self._pre_window_state: dict[str, str] = {}
        self._presets: dict[str, dict[str, dict[str, Any]]] = {}
        self._current_global_preset: str = GLOBAL_PRESET_MANUAL

    def load_state(self, pre_window_state: dict, presets: dict, zone_modes: dict) -> None:
        """Load restored state from storage."""
        if pre_window_state is not None:
            self._pre_window_state = pre_window_state
        if presets is not None:
            self._presets = presets
        if zone_modes is not None:
            for z, m in zone_modes.items():
                self._zone_modes[z] = m

    def get_zone(self, climate_entity: str) -> dict | None:
        """Get the zone configuration dict by entity_id."""
        for zone in self.zones:
            cid = zone.get("climate_id") or make_zone_entity_id(zone.get(CONF_ZONE_NAME, ""))
            if cid == climate_entity:
                return zone
        return None

    def is_passive_heat_allowed(self, climate_id: str) -> bool:
        """Return True if passive heat is allowed dynamically or via zone config."""
        z = self.get_zone(climate_id)
        if z:
            zone_name = z.get(CONF_ZONE_NAME, "")
            safe_name = zone_name.lower().replace(" ", "_").replace("-", "_")
            safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
            key = f"{KEY_PASSIVE_HEAT_PREFIX,
    CONF_ZONE_ALLOW_PASSIVE_HEAT}{safe_name}"
            default_val = bool(z.get(CONF_ZONE_ALLOW_PASSIVE_HEAT, False))
            return bool(self.coordinator.get_persistent_data(key, default_val))
        return False

    def get_zone_mode(self, climate_entity: str) -> str:
        """Get current zone mode, prioritizing calendar overrides."""
        if climate_entity in self.coordinator.calendar_manager.mode_overrides:
            return self.coordinator.calendar_manager.mode_overrides[climate_entity]
        return self._zone_modes.get(climate_entity, ZONE_MODE_PRIMARY)

    def set_zone_mode(self, climate_entity: str, mode: str) -> None:
        """Set zone mode and persist/update dependencies."""
        self._zone_modes[climate_entity] = mode
        self.coordinator.demand_aggregator.set_zone_mode(climate_entity, mode)

        # Persist zone mode directly in settings
        zone_modes = self.coordinator.get_persistent_data("zone_modes", {})
        zone_modes[climate_entity] = mode
        self.hass.async_create_task(self.coordinator.async_set_persistent_data("zone_modes", zone_modes))

        # Notify climate entity callback so extra_state_attributes update immediately
        if climate_entity in self.coordinator._climate_callbacks:
            self.coordinator._climate_callbacks[climate_entity]()

        # If a preset is active, save the mode state
        if self._current_global_preset:
            if self._current_global_preset not in self._presets:
                self._presets[self._current_global_preset] = {}
            if climate_entity not in self._presets[self._current_global_preset]:
                self._presets[self._current_global_preset][climate_entity] = {}

            self._presets[self._current_global_preset][climate_entity]["mode"] = mode
            self.hass.async_create_task(self.coordinator._async_save_presets_storage())

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
        if "global_preset" in self.coordinator._select_entities:
            self.coordinator._select_entities["global_preset"].async_write_ha_state()

        # Restore saved preset values for all zones
        if preset in self._presets:
            for climate_id, values in self._presets[preset].items():
                if "target_temp" in values:
                    # Apply target temp via HA service
                    await self.hass.services.async_call(
                        CLIMATE_DOMAIN,
                        SERVICE_SET_TEMPERATURE,
                        {ATTR_ENTITY_ID: climate_id, ATTR_TEMPERATURE: values["target_temp"]},
                        blocking=False,
                    )
                mode = values.get("mode")
                if not mode and "bypassed" in values:
                    mode = "bypass" if values["bypassed"] else "primary"
                
                if mode:
                    zone_select = self.coordinator._select_entities.get(f"zone_mode_{climate_id}")
                    if zone_select:
                        await zone_select.async_select_option(mode)
                    else:
                        self.set_zone_mode(climate_id, mode)

    async def async_sync_trv_preset(self, zone_id: str, new_state: str) -> None:
        """Sync TRV activation/presets based on Zone state (heat/off)."""
        zone = self.get_zone(zone_id)
        if not zone:
            return
            
        climates = zone.get(CONF_ZONE_CLIMATES, [])
        for trv in climates:
            trv_state = self.hass.states.get(trv)
            if not trv_state:
                continue
                
            # 1. Sync HVAC Mode (Base hardware compatibility)
            supported_hvac = trv_state.attributes.get("hvac_modes") or []
            # We map HVACMode constants which are usually 'heat' and 'off'
            target_hvac = new_state
            if target_hvac in supported_hvac and trv_state.state != target_hvac:
                _LOGGER.debug("Syncing TRV HVAC mode for %s to %s", trv, target_hvac)
                await self.hass.services.async_call(
                    CLIMATE_DOMAIN,
                    "set_hvac_mode",
                    {ATTR_ENTITY_ID: trv, "hvac_mode": target_hvac},
                    blocking=False,
                )
                
            # 2. Sync Presets (Advanced TRVs)
            supported_presets = trv_state.attributes.get("preset_modes") or []
            target_preset = None
            
            if new_state == HVACMode.HEAT:
                # Try to wake up the TRV
                if "manual" in supported_presets:
                    target_preset = "manual"
                elif "none" in supported_presets:
                    target_preset = "none"
                elif "boost" in supported_presets:
                    target_preset = "boost"
            elif new_state == HVACMode.OFF:
                # Try to put the TRV to sleep
                if "off" in supported_presets:
                    target_preset = "off"
                elif "none" in supported_presets:
                    target_preset = "none"
                    
            if target_preset and trv_state.attributes.get("preset_mode") != target_preset:
                _LOGGER.debug("Syncing TRV preset for %s to %s (Zone is %s)", trv, target_preset, new_state)
                await self.hass.services.async_call(
                    CLIMATE_DOMAIN,
                    SERVICE_SET_PRESET_MODE,
                    {ATTR_ENTITY_ID: trv, "preset_mode": target_preset},
                    blocking=False,
                )

    @callback
    def async_on_window_state_changed(self, event: Event) -> None:
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
            zone_select = self.coordinator._select_entities.get(f"zone_mode_{climate_id}")
            _LOGGER.debug("Window listener: zone_select for %s: %s", climate_id, zone_select)
            
            if new_state.state == "on":
                # Window OPENED
                anti_frost_active = self.coordinator.is_zone_in_frost_emergency(climate_id)
                if anti_frost_active:
                    _LOGGER.warning("Window opened (%s) for %s, but Anti-Frost protection is active! Skipping bypass to prevent freezing.", sensor_id, climate_id)
                    continue

                _LOGGER.debug("Window opened (%s), bypassing zone %s", sensor_id, climate_id)
                if climate_id not in self._pre_window_state:
                    current_mode = self.get_zone_mode(climate_id)
                    self._pre_window_state[climate_id] = current_mode
                    self.hass.async_create_task(self.coordinator.async_save_storage())
                
                if zone_select and self.get_zone_mode(climate_id) != ZONE_MODE_BYPASS:
                    self.coordinator.record_diagnostic_event("WINDOW_OPENED_BYPASS", {"sensor": sensor_id, "zone": climate_id})
                    self.hass.async_create_task(zone_select.async_select_option(ZONE_MODE_BYPASS))
                    
            elif new_state.state in ("off", "unavailable", "unknown"):
                # Window CLOSED or sensor lost connection (fail-safe to restore heating)
                _LOGGER.debug("Window closed or sensor lost (%s), restoring zone %s", sensor_id, climate_id)
                if climate_id in self._pre_window_state:
                    was_mode = self._pre_window_state.pop(climate_id)
                    self.hass.async_create_task(self.coordinator.async_save_storage())
                    
                    if zone_select and self.get_zone_mode(climate_id) != was_mode:
                        self.coordinator.record_diagnostic_event("WINDOW_CLOSED_RESTORE", {"sensor": sensor_id, "zone": climate_id, "mode": was_mode})
                        self.hass.async_create_task(zone_select.async_select_option(was_mode))
    def update_preset_temperature(self, preset: str, zone_id: str, temp: float) -> None:
        """Update the target temperature of a specific zone in a preset and save."""
        if preset not in self._presets:
            self._presets[preset] = {}
        if zone_id not in self._presets[preset]:
            self._presets[preset][zone_id] = {}
            
        self._presets[preset][zone_id]["target_temp"] = temp
        self.hass.async_create_task(self.coordinator._async_save_presets_storage())
