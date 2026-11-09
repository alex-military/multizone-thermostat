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
    CONF_ZONE_ALLOW_PASSIVE_HEAT,
    CONF_ZONE_TARGET_TEMP,
    DEFAULT_PRESET_TEMPS,
    DEFAULT_COOLING_PRESET_TEMPS,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
)

_LOGGER = logging.getLogger(__name__)

class PreWindowState(dict):
    """Dictionary representing pre-window zone state with backward-compatible string equality."""

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str):
            return self.get("mode") == other
        return super().__eq__(other)


class ZoneManager:
    """
    Responsabilità:
    - Registrazione e stato delle zone
    - Associazione TRV e sync
    - Gestione finestre (bypass)
    - Memorizzazione preset a doppio binario (Heating vs Cooling)
    """

    def __init__(self, hass: HomeAssistant, coordinator: Any) -> None:
        self.hass = hass
        self.coordinator = coordinator
        self.zones = coordinator.zones
        
        self._zone_modes: dict[str, str] = {
            (z.get("climate_id") or make_zone_entity_id(z.get(CONF_ZONE_NAME, "unnamed"))): ZONE_MODE_PRIMARY 
            for z in self.zones if z.get(CONF_ZONE_NAME)
        }
        self._pre_window_state: dict[str, Any] = {}
        self._last_manual_temps: dict[str, float] = {}
        self._last_manual_temps_cool: dict[str, float] = {}
        self._presets_heat: dict[str, dict[str, dict[str, Any]]] = {}
        self._presets_cool: dict[str, dict[str, dict[str, Any]]] = {}
        self._current_global_preset: str = GLOBAL_PRESET_MANUAL

    def _get_manual_temps_dict(self, hvac_mode: str | None = None) -> dict[str, float]:
        """Return the manual temperatures dictionary based on hvac_mode or master operation mode."""
        mode = hvac_mode
        if mode is None:
            if hasattr(self.coordinator, "get_master_hvac_mode") and callable(self.coordinator.get_master_hvac_mode):
                mode = self.coordinator.get_master_hvac_mode()
            else:
                mode = getattr(self.coordinator, "master_hvac_mode", HVAC_MODE_HEAT)
        if mode == HVAC_MODE_COOL:
            return self._last_manual_temps_cool
        return self._last_manual_temps

    def record_manual_temp(self, entity_id: str, temp: float, hvac_mode: str | None = None) -> None:
        """Record manual temperature separated by season."""
        effective_mode = hvac_mode
        if effective_mode is None:
            if hasattr(self.coordinator, "get_master_hvac_mode") and callable(self.coordinator.get_master_hvac_mode):
                effective_mode = self.coordinator.get_master_hvac_mode()
            else:
                effective_mode = getattr(self.coordinator, "master_hvac_mode", HVAC_MODE_HEAT)
        d = self._get_manual_temps_dict(effective_mode)
        d[entity_id] = float(temp)
        if effective_mode != HVAC_MODE_COOL and d is not self._last_manual_temps:
            self._last_manual_temps[entity_id] = float(temp)

    def get_state_for_storage(self) -> dict[str, Any]:
        """Return zone manager state for persistent storage."""
        return {
            "last_manual_temps": dict(self._last_manual_temps),
            "last_manual_temps_cool": dict(self._last_manual_temps_cool),
            "zone_modes": dict(self._zone_modes),
            "pre_window_state": dict(self._pre_window_state),
        }

    def restore_state_from_storage(self, data: dict[str, Any]) -> None:
        """Restore zone manager state from persistent storage."""
        if not isinstance(data, dict):
            return
        if "last_manual_temps" in data and isinstance(data["last_manual_temps"], dict):
            self._last_manual_temps.update({str(k): float(v) for k, v in data["last_manual_temps"].items()})
        if "last_manual_temps_cool" in data and isinstance(data["last_manual_temps_cool"], dict):
            self._last_manual_temps_cool.update({str(k): float(v) for k, v in data["last_manual_temps_cool"].items()})
        if "zone_modes" in data and isinstance(data["zone_modes"], dict):
            self._zone_modes.update(data["zone_modes"])
        if "pre_window_state" in data and isinstance(data["pre_window_state"], dict):
            self._pre_window_state.update(data["pre_window_state"])

    @property
    def active_preset_track(self) -> str:
        """Return 'cool' or 'heat' depending on current coordinator master operation mode."""
        if hasattr(self.coordinator, "master_hvac_mode") and self.coordinator.master_hvac_mode == HVAC_MODE_COOL:
            return HVAC_MODE_COOL
        return HVAC_MODE_HEAT

    @property
    def presets(self) -> dict[str, dict[str, dict[str, Any]]]:
        """Return active track presets dictionary."""
        return self._presets_cool if self.active_preset_track == HVAC_MODE_COOL else self._presets_heat

    @property
    def _presets(self) -> dict[str, dict[str, dict[str, Any]]]:
        """Backward-compatibility alias for internal access."""
        return self.presets

    @property
    def presets_heat(self) -> dict[str, dict[str, dict[str, Any]]]:
        """Return heating presets."""
        return self._presets_heat

    @property
    def presets_cool(self) -> dict[str, dict[str, dict[str, Any]]]:
        """Return cooling presets."""
        return self._presets_cool

    def load_state(
        self,
        pre_window_state: dict,
        presets: dict,
        zone_modes: dict,
        presets_cool: dict | None = None,
    ) -> None:
        """Load restored state from storage."""
        if pre_window_state is not None:
            self._pre_window_state = pre_window_state
        if presets is not None:
            if isinstance(presets, dict) and ("presets_heat" in presets or "presets_cool" in presets):
                self._presets_heat = presets.get("presets_heat", {})
                self._presets_cool = presets.get("presets_cool", {})
            else:
                self._presets_heat = presets
                if presets_cool is not None:
                    self._presets_cool = presets_cool
        elif presets_cool is not None:
            self._presets_cool = presets_cool

        if zone_modes is not None:
            for z, m in zone_modes.items():
                self._zone_modes[z] = m

        if isinstance(self._presets_heat, dict) and "manual" in self._presets_heat and isinstance(self._presets_heat["manual"], dict):
            for cid, data in self._presets_heat["manual"].items():
                if isinstance(data, dict) and data.get("target_temp") is not None:
                    try:
                        self._last_manual_temps[cid] = float(data["target_temp"])
                    except (ValueError, TypeError):
                        pass

        if isinstance(self._presets_cool, dict) and "manual" in self._presets_cool and isinstance(self._presets_cool["manual"], dict):
            for cid, data in self._presets_cool["manual"].items():
                if isinstance(data, dict) and data.get("target_temp") is not None:
                    try:
                        self._last_manual_temps_cool[cid] = float(data["target_temp"])
                    except (ValueError, TypeError):
                        pass

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
            key = f"{KEY_PASSIVE_HEAT_PREFIX}{safe_name}"
            default_val = bool(z.get(CONF_ZONE_ALLOW_PASSIVE_HEAT, False))
            return bool(self.coordinator.get_persistent_data(key, default_val))
        return False

    def get_zone_mode(self, climate_entity: str) -> str:
        """Get current zone mode, prioritizing window-open bypass and calendar overrides."""
        if climate_entity in self._pre_window_state and self._zone_modes.get(climate_entity) == ZONE_MODE_BYPASS:
            return ZONE_MODE_BYPASS
        if hasattr(self.coordinator, "calendar_manager") and climate_entity in self.coordinator.calendar_manager.mode_overrides:
            return self.coordinator.calendar_manager.mode_overrides[climate_entity]
        return self._zone_modes.get(climate_entity, ZONE_MODE_PRIMARY)

    def set_zone_mode(self, climate_entity: str, mode: str, save_to_preset: bool = True) -> None:
        """Set zone mode and persist/update dependencies."""
        self._zone_modes[climate_entity] = mode
        self.coordinator.demand_aggregator.set_zone_mode(climate_entity, mode)

        # Persist zone mode directly in settings (copy & update synchronously to avoid race across multiple zones)
        existing_modes = self.coordinator.get_persistent_data("zone_modes", {})
        zone_modes = dict(existing_modes) if isinstance(existing_modes, dict) else {}
        zone_modes[climate_entity] = mode
        if hasattr(self.coordinator, "_settings") and isinstance(self.coordinator._settings, dict):
            self.coordinator._settings["zone_modes"] = zone_modes
        self.hass.async_create_task(self.coordinator.async_set_persistent_data("zone_modes", zone_modes))

        # Notify climate entity callback so extra_state_attributes update immediately
        if climate_entity in self.coordinator._climate_callbacks:
            self.coordinator._climate_callbacks[climate_entity]()

        # If a preset is active and this is not a temporary window bypass, save the mode state to active track
        if save_to_preset and self._current_global_preset and climate_entity not in self._pre_window_state:
            target_track = self._presets_cool if (self.active_preset_track == HVAC_MODE_COOL) else self._presets_heat
            if self._current_global_preset not in target_track:
                target_track[self._current_global_preset] = {}
            if climate_entity not in target_track[self._current_global_preset]:
                target_track[self._current_global_preset][climate_entity] = {}

            target_track[self._current_global_preset][climate_entity]["mode"] = mode
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
        """Set the global preset and apply it to all zones on the active track."""
        is_cool = (self.active_preset_track == HVAC_MODE_COOL)

        # If switching away from manual mode, record current manual temperatures in memory
        if self._current_global_preset in (GLOBAL_PRESET_MANUAL, "manual") and preset not in (GLOBAL_PRESET_MANUAL, "manual"):
            for zone in self.zones:
                name = zone.get(CONF_ZONE_NAME)
                if not name:
                    continue
                cid = zone.get("climate_id") or make_zone_entity_id(name)
                cur_temp = None
                climate_ent = getattr(self.coordinator, "_climate_entities", {}).get(cid)
                if climate_ent is not None and getattr(climate_ent, "target_temperature", None) is not None:
                    cur_temp = float(climate_ent.target_temperature)
                elif hasattr(self, "hass") and self.hass and hasattr(self.hass, "states"):
                    st = self.hass.states.get(cid)
                    if st and st.attributes.get("temperature") is not None:
                        try:
                            cur_temp = float(st.attributes["temperature"])
                        except (ValueError, TypeError):
                            pass
                if cur_temp is not None:
                    self.record_manual_temp(cid, cur_temp, HVAC_MODE_COOL if is_cool else HVAC_MODE_HEAT)
                    target_track_manual = self._presets_cool if is_cool else self._presets_heat
                    if "manual" not in target_track_manual:
                        target_track_manual["manual"] = {}
                    if cid not in target_track_manual["manual"]:
                        target_track_manual["manual"][cid] = {}
                    target_track_manual["manual"][cid]["target_temp"] = cur_temp

        self._current_global_preset = preset
        _LOGGER.debug("Global preset changed to '%s' (active track: %s)", preset, self.active_preset_track)
        
        # Notify the UI select entity if it's registered
        if "global_preset" in self.coordinator._select_entities:
            self.coordinator._select_entities["global_preset"].async_write_ha_state()

        target_track = self._presets_cool if is_cool else self._presets_heat

        # Iterate over configured zones
        for zone in self.zones:
            name = zone.get(CONF_ZONE_NAME)
            if not name:
                continue
            climate_id = make_zone_entity_id(name)

            # In cooling mode, if zone cannot cool, skip setpoint change
            if is_cool and hasattr(self.coordinator, "can_zone_cool") and not self.coordinator.can_zone_cool(climate_id):
                continue

            # Determine target temperature
            target_temp = None
            if preset in target_track and climate_id in target_track[preset]:
                target_temp = target_track[preset][climate_id].get("target_temp")
            if target_temp is None:
                target_temp = self.get_preset_temperature(preset, climate_id, HVAC_MODE_COOL if is_cool else HVAC_MODE_HEAT)

            if target_temp is not None:
                t_val = float(target_temp)
                climate_ent = getattr(self.coordinator, "_climate_entities", {}).get(climate_id)
                if climate_ent is not None and hasattr(climate_ent, "_target_temperature"):
                    climate_ent._target_temperature = t_val
                sched_mgr = getattr(self.coordinator, "schedule_manager", None)
                if sched_mgr and getattr(sched_mgr, "scheduler_enabled", False) is True:
                    if preset == "manual":
                        sched_mgr.record_manual_override(climate_id, t_val)
                    elif hasattr(sched_mgr, "manual_overrides") and isinstance(sched_mgr.manual_overrides, dict):
                        sched_mgr.manual_overrides.pop(climate_id, None)
                await self.hass.services.async_call(
                    CLIMATE_DOMAIN,
                    SERVICE_SET_TEMPERATURE,
                    {ATTR_ENTITY_ID: climate_id, ATTR_TEMPERATURE: t_val},
                    blocking=False,
                )

            # Determine zone mode
            mode = None
            if preset in target_track and climate_id in target_track[preset]:
                values = target_track[preset][climate_id]
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
            if not trv_state or trv_state.state in ("unavailable", "unknown"):
                continue
                
            # 1. Sync HVAC Mode (Base hardware compatibility)
            supported_hvac = trv_state.attributes.get("hvac_modes") or []
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
                if "manual" in supported_presets:
                    target_preset = "manual"
                elif "none" in supported_presets:
                    target_preset = "none"
                elif "boost" in supported_presets:
                    target_preset = "boost"
            elif new_state == HVACMode.OFF:
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
            
        matching_zones = [z for z in self.zones if z.get(CONF_ZONE_WINDOW_SENSOR) == sensor_id and z.get(CONF_ZONE_NAME)]
        _LOGGER.debug("Window listener: matching zones: %s", matching_zones)
        if not matching_zones:
            return
            
        for zone in matching_zones:
            climate_id = make_zone_entity_id(zone[CONF_ZONE_NAME])
            zone_select = self.coordinator._select_entities.get(f"zone_mode_{climate_id}")
            _LOGGER.debug("Window listener: zone_select for %s: %s", climate_id, zone_select)
            
            if new_state.state == "on":
                anti_frost_active = self.coordinator.is_zone_in_frost_emergency(climate_id)
                if anti_frost_active:
                    _LOGGER.warning("Window opened (%s) for %s, but Anti-Frost protection is active! Skipping bypass to prevent freezing.", sensor_id, climate_id)
                    continue

                _LOGGER.debug("Window opened (%s), bypassing zone %s", sensor_id, climate_id)
                if climate_id not in self._pre_window_state:
                    current_mode = self._zone_modes.get(climate_id, ZONE_MODE_PRIMARY)
                    climate_ent = getattr(self.coordinator, "_climate_entities", {}).get(climate_id)
                    is_off = False
                    if climate_ent and hasattr(climate_ent, "hvac_mode"):
                        is_off = (climate_ent.hvac_mode == HVACMode.OFF or str(climate_ent.hvac_mode).lower().endswith("off"))
                    elif hasattr(self, "hass") and self.hass and hasattr(self.hass, "states"):
                        st = self.hass.states.get(climate_id)
                        if st and st.state.lower() == "off":
                            is_off = True
                    self._pre_window_state[climate_id] = PreWindowState({"mode": current_mode, "was_off": is_off})
                    self.hass.async_create_task(self.coordinator.async_save_storage())
                
                if self._zone_modes.get(climate_id) != ZONE_MODE_BYPASS:
                    self.coordinator.record_diagnostic_event("WINDOW_OPENED_BYPASS", {"sensor": sensor_id, "zone": climate_id})
                    if zone_select:
                        self.hass.async_create_task(zone_select.async_select_option(ZONE_MODE_BYPASS))
                    else:
                        self.set_zone_mode(climate_id, ZONE_MODE_BYPASS, save_to_preset=False)
                    
            elif new_state.state in ("off", "unavailable", "unknown"):
                _LOGGER.debug("Window closed or sensor lost (%s), restoring zone %s", sensor_id, climate_id)
                if climate_id in self._pre_window_state:
                    raw_saved = self._pre_window_state.pop(climate_id)
                    self.hass.async_create_task(self.coordinator.async_save_storage())
                    if isinstance(raw_saved, dict):
                        was_mode = raw_saved.get("mode", ZONE_MODE_PRIMARY)
                        was_off = bool(raw_saved.get("was_off", False))
                    elif isinstance(raw_saved, (tuple, list)):
                        was_mode = raw_saved[0]
                        was_off = bool(raw_saved[1]) if len(raw_saved) > 1 else False
                    else:
                        was_mode = str(raw_saved)
                        was_off = False
                    
                    if was_off:
                        if hasattr(self.coordinator, "_async_set_hvac_mode"):
                            self.hass.async_create_task(self.coordinator._async_set_hvac_mode(climate_id, HVACMode.OFF))
                        elif climate_ent := getattr(self.coordinator, "_climate_entities", {}).get(climate_id):
                            self.hass.async_create_task(climate_ent.async_set_hvac_mode(HVACMode.OFF))

                    if self._zone_modes.get(climate_id) != was_mode:
                        self.coordinator.record_diagnostic_event("WINDOW_CLOSED_RESTORE", {"sensor": sensor_id, "zone": climate_id, "mode": was_mode})
                        if zone_select:
                            self.hass.async_create_task(zone_select.async_select_option(was_mode))
                        else:
                            self.set_zone_mode(climate_id, was_mode, save_to_preset=False)

    def update_preset_temperature(
        self,
        preset: str,
        zone_id: str,
        temp: float,
        hvac_mode: str | None = None,
    ) -> None:
        """Update the target temperature of a specific zone in a preset (heat or cool track) and save."""
        is_cool = (hvac_mode == HVAC_MODE_COOL) or (hvac_mode is None and self.active_preset_track == HVAC_MODE_COOL)
        target_track = self._presets_cool if is_cool else self._presets_heat

        if preset in (GLOBAL_PRESET_MANUAL, "manual"):
            self.record_manual_temp(zone_id, float(temp), HVAC_MODE_COOL if is_cool else HVAC_MODE_HEAT)

        if preset not in target_track:
            target_track[preset] = {}
        if zone_id not in target_track[preset]:
            target_track[preset][zone_id] = {}
            
        target_track[preset][zone_id]["target_temp"] = float(temp)
        self.hass.async_create_task(self.coordinator._async_save_presets_storage())

    def get_preset_temperature(
        self,
        preset: str,
        climate_id: str,
        hvac_mode: str | None = None,
    ) -> float | None:
        """Resolve preset temperature dynamically for heating or cooling track."""
        is_cool = (hvac_mode == HVAC_MODE_COOL) or (hvac_mode is None and self.active_preset_track == HVAC_MODE_COOL)
        target_track = self._presets_cool if is_cool else self._presets_heat
        default_temps = DEFAULT_COOLING_PRESET_TEMPS if is_cool else DEFAULT_PRESET_TEMPS

        val = target_track.get(preset, {}).get(climate_id, {}).get("target_temp")
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                pass

        if preset in (GLOBAL_PRESET_MANUAL, "manual"):
            manual_dict = self._get_manual_temps_dict(HVAC_MODE_COOL if is_cool else HVAC_MODE_HEAT)
            if climate_id in manual_dict:
                return float(manual_dict[climate_id])
            if not is_cool and hasattr(self, "_last_manual_temps") and climate_id in self._last_manual_temps:
                return float(self._last_manual_temps[climate_id])
            z = self.get_zone(climate_id)
            if z and z.get(CONF_ZONE_TARGET_TEMP) is not None:
                try:
                    return float(z[CONF_ZONE_TARGET_TEMP])
                except (ValueError, TypeError):
                    pass
            return float(default_temps.get("comfort", 24.5 if is_cool else 20.5))

        if preset in default_temps:
            if preset == "comfort":
                z = self.get_zone(climate_id)
                if z and z.get(CONF_ZONE_TARGET_TEMP) is not None:
                    try:
                        return float(default_temps["comfort"]) if is_cool else float(z[CONF_ZONE_TARGET_TEMP])
                    except (ValueError, TypeError):
                        pass
                return float(default_temps.get("comfort", 24.5 if is_cool else 20.5))
            return float(default_temps[preset])
        return None
