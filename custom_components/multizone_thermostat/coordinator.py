"""Coordinator for Multizone Thermostat: handles all heating logic."""
from __future__ import annotations

from collections import deque
import inspect
import logging
import time
from typing import Any

from homeassistant.core import HomeAssistant
import homeassistant.util.dt as dt_util

from .plant_config import PlantConfig
from .plant_factory import build_plant_subsystems
from .const import (
    KEY_ALLOW_SPLIT_HEATING,
    KEY_ALLOW_SPLIT_COOLING,
    KEY_HEAT_SOURCE_PRIORITY,
    DEFAULT_HEAT_SOURCE_PRIORITY,
    KEY_HP_MIN_CYCLE_ON,
    KEY_HP_MIN_CYCLE_OFF,
    CONF_ZONE_NAME,
    make_zone_entity_id,
)
from .protocols import (
    BoilerBackendProtocol,
    PlantOrchestratorProtocol,
    ZoneControllerProtocol,
)

_LOGGER = logging.getLogger(__name__)


class MultizoneCoordinator:
    """Central coordinator that acts as composition root and manages heating plant lifecycle."""

    boiler_backend: BoilerBackendProtocol | None
    plant_orchestrator: PlantOrchestratorProtocol | None
    zone_controller: ZoneControllerProtocol | None

    def __init__(
        self,
        hass: HomeAssistant,
        entry: Any,
    ) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry_id = entry.entry_id
        self.config = PlantConfig.from_entry(entry)
        self._unsub_listeners: list = []
        self._apply_config(self.config)

        # Internal state tracking
        self.master_device_id: str | None = None
        self._master_state: bool = False
        self._master_switch: Any = None
        self._climate_callbacks: dict[str, Any] = {}
        self._last_active_time: float = time.monotonic()
        self._select_entities: dict[str, Any] = {}
        self._diagnostics_history: deque[dict[str, Any]] = deque(maxlen=100)
        self._climate_entities: dict[str, Any] = {}
        self._entity_id_aliases: dict[str, str] = {}
        self._pid_listeners: list[Any] = []
        self._settings: dict[str, Any] = {}
        self._presets: dict[str, Any] = {}

        # Build and wire all subsystems
        build_plant_subsystems(self, hass, self.config)

    def _apply_config(self, cfg: PlantConfig) -> None:
        """Apply PlantConfig fields to coordinator attributes for backward compatibility."""
        self.boiler_mode = cfg.boiler_mode
        self.boiler_switch = cfg.boiler_switch
        self.opentherm_entity = cfg.opentherm_entity
        self.opentherm_min_temp = cfg.opentherm_min_temp
        self.opentherm_max_temp = cfg.opentherm_max_temp
        self.opentherm_ch_switch = cfg.opentherm_ch_switch
        self.dhw_active_sensor = cfg.dhw_active_sensor
        self.has_mixing_valve = cfg.has_mixing_valve
        self.zones = cfg.zones
        self.presence_sensor = cfg.presence_sensor
        self.weather_sensor_id = cfg.weather_sensor_id
        self.global_calendar_id = cfg.global_calendar_id

        self.enable_gas_heater = cfg.enable_gas_heater
        self.enable_heat_pump = cfg.enable_heat_pump
        self.heat_pump_type = cfg.heat_pump_type
        self.heat_pump_entity = cfg.heat_pump_entity
        self.heat_pump_min_temp = cfg.heat_pump_min_temp
        self.heat_pump_max_temp = cfg.heat_pump_max_temp
        self.heat_pump_ch_switch = cfg.heat_pump_ch_switch
        self.heat_pump_cooling = cfg.heat_pump_cooling
        self.master_hvac_mode = cfg.master_hvac_mode

        self.energy_management_enabled = cfg.energy_management_enabled
        self.solar_power_sensor = cfg.solar_power_sensor
        self.grid_export_sensor = cfg.grid_export_sensor
        self.battery_soc_sensor = cfg.battery_soc_sensor
        self.external_solar_override_entity = cfg.external_solar_override_entity
        self.solar_export_threshold = cfg.solar_export_threshold
        self.battery_min_reserve_soc = cfg.battery_min_reserve_soc

        self._min_cycle_on = cfg.min_cycle_on
        self._min_cycle_off = cfg.min_cycle_off
        self._hp_min_cycle_on = getattr(cfg, "hp_min_cycle_on", cfg.min_cycle_on)
        self._hp_min_cycle_off = getattr(cfg, "hp_min_cycle_off", cfg.min_cycle_off)
        self._valve_delay = cfg.valve_delay

    def register_master_switch(self, switch_entity) -> None:
        """Register the master switch entity."""
        self._master_switch = switch_entity

    def resolve_zone_id(self, climate_id: str) -> str:
        """Resolve an HA-localized or aliased entity_id back to its canonical zone id."""
        return self._entity_id_aliases.get(climate_id, climate_id)

    def register_pid_listener(self, callback_fn) -> None:
        """Register a PID/autotuner UI entity listener."""
        if callback_fn not in self._pid_listeners:
            self._pid_listeners.append(callback_fn)

    def unregister_pid_listener(self, callback_fn) -> None:
        """Unregister a PID/autotuner UI entity listener."""
        if callback_fn in self._pid_listeners:
            self._pid_listeners.remove(callback_fn)

    def async_notify_pid_entities(self) -> None:
        """Notify registered PID/autotuner UI entities and climate entities of updated values."""
        for cb in list(self._pid_listeners):
            try:
                cb()
            except Exception as err:
                _LOGGER.debug("Error notifying PID entity listener: %s", err)
        for cb in list(self._climate_callbacks.values()):
            try:
                cb()
            except Exception as err:
                _LOGGER.debug("Error notifying PID entity listener: %s", err)

    def _pid_unlock_storage_key(self, zone_name: str) -> str:
        resolved = self.resolve_zone_id(zone_name)
        target = zone_name
        if resolved.startswith("climate."):
            for z in getattr(self, "zones", []) or []:
                zname = z.get(CONF_ZONE_NAME)
                if zname and make_zone_entity_id(zname) == resolved:
                    target = zname
                    break
        safe = (target or "").lower().replace(" ", "_").replace("-", "_")
        safe = "".join(c for c in safe if c.isalnum() or c == "_")
        return f"pid_manual_unlock_{safe}"

    def get_pid_manual_unlock(self, zone_name: str) -> bool:
        """Return True if manual PID override sliders are unlocked for a zone."""
        return bool(self.get_persistent_data(self._pid_unlock_storage_key(zone_name), False))

    async def async_set_pid_manual_unlock(self, zone_name: str, unlocked: bool) -> None:
        """Persist manual PID unlock state for a zone and notify dependent entities."""
        await self.async_set_persistent_data(self._pid_unlock_storage_key(zone_name), bool(unlocked))
        self.async_notify_pid_entities()

    def register_climate(
        self,
        entity_id: str,
        callback,
        entity_instance: Any = None,
        canonical_id: str | None = None,
    ) -> None:
        """Register a climate entity for state updates and diagnostics."""
        if canonical_id and entity_id and entity_id != canonical_id:
            self._entity_id_aliases[entity_id] = canonical_id
        canon = canonical_id or self.resolve_zone_id(entity_id)
        self._climate_callbacks[canon] = callback
        self.demand_aggregator.register_climate_callback(canon, callback)
        if entity_instance is not None:
            self._climate_entities[canon] = entity_instance

    def unregister_climate(self, entity_id: str) -> None:
        """Unregister a climate entity on removal."""
        canon = self.resolve_zone_id(entity_id)
        self._climate_callbacks.pop(canon, None)
        self._climate_callbacks.pop(entity_id, None)
        self._climate_entities.pop(canon, None)
        self._climate_entities.pop(entity_id, None)
        self._entity_id_aliases.pop(entity_id, None)
        if hasattr(self, "demand_aggregator"):
            self.demand_aggregator.unregister_climate_callback(canon)
            if canon != entity_id:
                self.demand_aggregator.unregister_climate_callback(entity_id)

    @property
    def _zone_modes(self) -> dict[str, str]:
        """Alias to zone modes owned by ZoneManager."""
        return self.zone_manager._zone_modes

    @property
    def climate_entities(self) -> dict[str, Any]:
        """Return registered climate entities keyed by canonical zone id."""
        return self._climate_entities

    def get_climate_entity(self, climate_id: str) -> Any | None:
        """Return registered climate entity for a zone id or alias."""
        canon = self.resolve_zone_id(climate_id)
        return self._climate_entities.get(canon) or self._climate_entities.get(climate_id)

    @property
    def select_entities(self) -> dict[str, Any]:
        """Return registered select entities."""
        return self._select_entities

    def get_select_entity(self, key: str) -> Any | None:
        """Return registered select entity by key."""
        return self._select_entities.get(key)

    @property
    def zone_demands(self) -> dict[str, float]:
        """Return current zone demands from DemandAggregator."""
        return self.demand_aggregator.zone_demands

    @property
    def _zone_demands(self) -> dict[str, float]:
        """Backward-compatible alias to zone demands owned by DemandAggregator."""
        return self.demand_aggregator._zone_demands

    @property
    def pre_window_state(self) -> dict[str, str]:
        """Alias to pre-window states owned by ZoneManager."""
        zm = getattr(self, "zone_manager", None)
        return getattr(zm, "pre_window_state", getattr(zm, "_pre_window_state", {}))

    @property
    def _pre_window_state(self) -> dict[str, str]:
        """Alias to pre-window states owned by ZoneManager."""
        return self.pre_window_state

    @_pre_window_state.setter
    def _pre_window_state(self, val: dict[str, str]) -> None:
        zm = getattr(self, "zone_manager", None)
        if zm is not None:
            if hasattr(zm, "set_pre_window_state"):
                zm.set_pre_window_state(val)
            else:
                zm._pre_window_state = val

    @property
    def last_active_time(self) -> float:
        """Return monotonic timestamp of when system was last active."""
        return self._last_active_time

    def reset_last_active_time(self) -> None:
        """Reset the last active time timestamp to now."""
        self._last_active_time = time.monotonic()
        settings = getattr(self, "_settings", None)
        if isinstance(settings, dict):
            settings["last_active_wall_time"] = time.time()
        st = getattr(self, "storage", None)
        if st is not None:
            try:
                st.debounced_save_settings()
            except AttributeError:
                pass

    @property
    def is_modulating_plant(self) -> bool:
        """Return True if the plant has a modulating generator (OpenTherm or Heat Pump)."""
        orchestrator = getattr(self, "plant_orchestrator", None)
        from .boiler.plant_orchestrator import PlantOrchestrator, check_is_modulating_plant
        if isinstance(orchestrator, PlantOrchestrator):
            return orchestrator.is_modulating_plant
        return check_is_modulating_plant(self)

    @property
    def is_dhw_active(self) -> bool:
        """Return True if Domestic Hot Water (DHW) production is active."""
        orchestrator = getattr(self, "plant_orchestrator", None)
        from .boiler.plant_orchestrator import PlantOrchestrator, check_is_dhw_active
        if isinstance(orchestrator, PlantOrchestrator):
            return orchestrator.is_dhw_active
        return check_is_dhw_active(self)

    @property
    def boiler_status_reason(self) -> str:
        """Return human-readable explanation of why the boiler is currently in its state."""
        orchestrator = getattr(self, "plant_orchestrator", None)
        from .boiler.plant_orchestrator import PlantOrchestrator, check_boiler_status_reason
        if isinstance(orchestrator, PlantOrchestrator):
            return orchestrator.boiler_status_reason
        return check_boiler_status_reason(self)

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
        except (ValueError, TypeError, KeyError, AttributeError):
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
        st = getattr(self, "storage", None)
        if st is not None:
            try:
                return st.get_data(key, default)
            except AttributeError:
                pass
        settings = getattr(self, "_settings", None)
        if isinstance(settings, dict):
            return settings.get(key, default)
        return default

    async def async_set_persistent_data(self, key: str, value: Any) -> None:
        """Set a persistent setting."""
        st = getattr(self, "storage", None)
        if st is not None:
            try:
                await st.async_set_data(key, value)
                return
            except AttributeError:
                pass
        settings = getattr(self, "_settings", None)
        if isinstance(settings, dict):
            settings[key] = value
        settings_store = getattr(self, "_settings_store", None)
        if settings_store is not None:
            await settings_store.async_save(self._settings)

    def debounced_save_thermal_states(self, thermal_models) -> None:
        st = getattr(self, "storage", None)
        if st is not None:
            st.debounced_save_thermal_states(thermal_models)

    async def async_load_storage(self) -> None:
        """Load stored window states and presets."""
        from .storage.storage_manager import StorageManager
        st = getattr(self, "storage", None)
        if isinstance(st, StorageManager):
            await st.async_load_coordinator_storage(self)
        else:
            hass = getattr(self, "hass", None)
            entry_id = getattr(self, "entry_id", "default")
            sm = StorageManager(hass, entry_id)
            await sm.async_load_coordinator_storage(self)

    async def async_save_storage(self) -> None:
        """Save window states, presets and settings to storage."""
        zm = getattr(self, "zone_manager", None)
        pre_win = getattr(zm, "pre_window_state", getattr(zm, "_pre_window_state", {}))
        await self._store.async_save(pre_win)
        await self._preset_store.async_save(self.storage._get_preset_data())
        await self._settings_store.async_save(self._settings)

    async def _async_save_autotuner_states(self) -> None:
        """Save autotuner learning progress to storage via ZoneController/StorageManager."""
        if hasattr(self, "zone_controller"):
            await self.zone_controller.async_save_autotuner_states()
        else:
            await self.storage.async_save_autotuner_states(self._autotuners)

    async def _async_save_thermal_states(self) -> None:
        """Save thermal model learning progress to storage via StorageManager."""
        await self.storage.async_save_thermal_states(self._thermal_models)

    async def async_save_presets_storage(self) -> None:
        """Save presets to storage via StorageManager."""
        await self.storage.async_save_presets(self.zone_manager._presets_heat, self.zone_manager._presets_cool)

    async def _async_save_presets_storage(self) -> None:
        """Backward-compatible alias for async_save_presets_storage."""
        await self.async_save_presets_storage()

    def register_select(self, key: str, select_entity: Any) -> None:
        """Register a select entity."""
        self._select_entities[key] = select_entity

    @property
    def min_cycle_on(self) -> float:
        """Return minimum cycle on time in minutes."""
        return self._min_cycle_on

    def _has_dedicated_hp_cycle_setting(self, flag_attr: str, persist_key: str) -> bool:
        """Return True if a dedicated heat-pump min cycle time was explicitly configured."""
        if getattr(self, flag_attr, False) is True:
            return True
        persisted = self.get_persistent_data(persist_key, None)
        if persisted is not None and not isinstance(persisted, bool) and isinstance(persisted, (int, float, str)):
            try:
                float(persisted)
                return True
            except (ValueError, TypeError):
                return False
        return False

    def set_min_cycle_on(self, value: float) -> None:
        self._min_cycle_on = float(value)
        bb = getattr(self, "boiler_backend", None)
        if bb is not None:
            try:
                bb.set_min_cycle_on(int(value))
            except AttributeError:
                pass
        hp = getattr(self, "heat_pump_backend", None)
        if hp is not None and not self._has_dedicated_hp_cycle_setting(
            "_hp_min_cycle_on_explicit", KEY_HP_MIN_CYCLE_ON
        ):
            try:
                hp.set_min_cycle_on(float(value))
            except AttributeError:
                pass

    @property
    def min_cycle_off(self) -> float:
        """Return minimum cycle off time in minutes."""
        return self._min_cycle_off

    def set_min_cycle_off(self, value: float) -> None:
        self._min_cycle_off = float(value)
        bb = getattr(self, "boiler_backend", None)
        if bb is not None:
            try:
                bb.set_min_cycle_off(int(value))
            except AttributeError:
                pass
        hp = getattr(self, "heat_pump_backend", None)
        if hp is not None and not self._has_dedicated_hp_cycle_setting(
            "_hp_min_cycle_off_explicit", KEY_HP_MIN_CYCLE_OFF
        ):
            try:
                hp.set_min_cycle_off(float(value))
            except AttributeError:
                pass

    @property
    def hp_min_cycle_on(self) -> float:
        """Return heat pump minimum cycle on time in minutes."""
        return getattr(self, "_hp_min_cycle_on", self._min_cycle_on)

    def set_hp_min_cycle_on(self, value: float) -> None:
        self._hp_min_cycle_on = float(value)
        self._hp_min_cycle_on_explicit = True
        hp = getattr(self, "heat_pump_backend", None)
        if hp is not None:
            try:
                hp.set_min_cycle_on(float(value))
            except AttributeError:
                pass

    @property
    def hp_min_cycle_off(self) -> float:
        """Return heat pump minimum cycle off time in minutes."""
        return getattr(self, "_hp_min_cycle_off", self._min_cycle_off)

    def set_hp_min_cycle_off(self, value: float) -> None:
        self._hp_min_cycle_off = float(value)
        self._hp_min_cycle_off_explicit = True
        hp = getattr(self, "heat_pump_backend", None)
        if hp is not None:
            try:
                hp.set_min_cycle_off(float(value))
            except AttributeError:
                pass

    @property
    def valve_delay(self) -> float:
        """Return valve delay in seconds."""
        return self._valve_delay

    def set_valve_delay(self, value: float) -> None:
        self._valve_delay = float(value)
        for backend_attr in ("boiler_backend", "heat_pump_backend"):
            backend = getattr(self, backend_attr, None)
            if backend is not None:
                try:
                    backend.set_valve_delay(int(value))
                except AttributeError:
                    pass

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
        split_mgr = getattr(self, "split_manager", None)
        if state and split_mgr is not None:
            split_mgr.reset_all_local_manual_overrides()

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
        """Set up state change listeners for all climate entities and timers."""
        self.listener_manager.async_setup_listeners()

    def async_teardown_listeners(self) -> None:
        """Remove all state change listeners and cancel background tasks."""
        self.listener_manager.async_teardown_listeners()

    async def _async_on_climate_state_changed(self, event: Any) -> None:
        """Handle temperature or preset changes on individual zone climate entities."""
        await self.listener_manager.async_on_climate_state_changed(event)

    def get_zone_mode(self, climate_id: str) -> str:
        return self.zone_manager.get_zone_mode(self.resolve_zone_id(climate_id))

    def set_zone_mode(self, climate_id: str, mode: str, save_to_preset: bool = True) -> None:
        self.zone_manager.set_zone_mode(self.resolve_zone_id(climate_id), mode, save_to_preset=save_to_preset)

    def get_zone_demand(self, climate_id: str) -> float:
        return self.demand_aggregator.get_zone_demand(self.resolve_zone_id(climate_id))

    def set_zone_demand(self, climate_id: str, demand: float) -> None:
        self.demand_aggregator.set_zone_demand(self.resolve_zone_id(climate_id), demand)

    def get_autotuner(self, climate_id: str, mode: str | None = None):
        cid = self.resolve_zone_id(climate_id)
        if mode is None:
            return self.zone_controller.get_autotuner(cid)
        return self.zone_controller.get_autotuner(cid, mode=mode)

    def is_zone_in_frost_emergency(self, climate_id: str) -> bool:
        """Return True if anti-frost is enabled and zone temperature is below the safety threshold."""
        fm = getattr(self, "frost_manager", None)
        if fm is not None:
            return fm.is_zone_in_frost_emergency(climate_id)
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

    # ------------------------------------------------------------------
    # Cooling Policy & Capability Delegation
    # ------------------------------------------------------------------

    def can_central_cool(self) -> bool:
        """Return True if central plant supports cooling."""
        from .cooling_policy import CoolingPolicy
        policy = getattr(self, "cooling_policy", None)
        if isinstance(policy, CoolingPolicy):
            return policy.can_central_cool()
        return CoolingPolicy(self).can_central_cool()

    def can_zone_cool(self, climate_id: str) -> bool:
        """Return True if zone has cooling capabilities."""
        from .cooling_policy import CoolingPolicy
        policy = getattr(self, "cooling_policy", None)
        if isinstance(policy, CoolingPolicy):
            return policy.can_zone_cool(climate_id)
        return CoolingPolicy(self).can_zone_cool(climate_id)

    def get_zone_cooling_rate(self, climate_id: str) -> float:
        """Return cooling rate for a zone from schedule_manager or thermal observer."""
        from .cooling_policy import CoolingPolicy
        policy = getattr(self, "cooling_policy", None)
        if isinstance(policy, CoolingPolicy):
            return policy.get_zone_cooling_rate(climate_id)
        return CoolingPolicy(self).get_zone_cooling_rate(climate_id)

    # ------------------------------------------------------------------
    # Master HVAC Coordination Delegation
    # ------------------------------------------------------------------

    async def async_set_master_hvac_mode(self, mode: str) -> None:
        """Set master operation mode ('heat' or 'cool') and coordinate whole-house operation."""
        from .master_controller import MasterController
        ctrl = getattr(self, "master_controller", None)
        if isinstance(ctrl, MasterController):
            await ctrl.async_set_master_hvac_mode(mode)
        else:
            await MasterController(self).async_set_master_hvac_mode(mode)

    async def async_apply_master_on(self) -> None:
        """Master turned ON: apply mode to all eligible zones."""
        from .master_controller import MasterController
        ctrl = getattr(self, "master_controller", None)
        if isinstance(ctrl, MasterController):
            await ctrl.async_apply_master_on()
        else:
            await MasterController(self).async_apply_master_on()

    async def async_apply_master_off(self) -> None:
        """Master turned OFF: turn off all zones and boiler."""
        from .master_controller import MasterController
        ctrl = getattr(self, "master_controller", None)
        if isinstance(ctrl, MasterController):
            await ctrl.async_apply_master_off()
        else:
            await MasterController(self).async_apply_master_off()

    async def async_set_hvac_mode(self, climate_entity: str, mode: str) -> None:
        """Set HVAC mode on a climate entity."""
        from .master_controller import MasterController
        ctrl = getattr(self, "master_controller", None)
        if isinstance(ctrl, MasterController):
            await ctrl.async_set_hvac_mode(climate_entity, mode)
        else:
            await MasterController(self).async_set_hvac_mode(climate_entity, mode)

    async def _async_set_hvac_mode(self, climate_entity: str, mode: str) -> None:
        """Backward-compatible alias for async_set_hvac_mode."""
        await self.async_set_hvac_mode(climate_entity, mode)

    def notify_climate(self, climate_id: str) -> None:
        """Trigger state update callback for a single climate entity."""
        canon = self.resolve_zone_id(climate_id)
        cb = self._climate_callbacks.get(canon) or self._climate_callbacks.get(climate_id)
        if cb:
            cb()

    def notify_all_climates(self) -> None:
        """Trigger state update callbacks for all registered climate entities."""
        for cb in list(self._climate_callbacks.values()):
            cb()

    async def async_update_all_climates(self) -> None:
        """Trigger zone controller re-evaluation and state write on all registered zones."""
        zc = getattr(self, "zone_controller", None)
        states = self.hass.states if self.hass else None
        for entity_id, cb in list(self._climate_callbacks.items()):
            if zc is not None and states is not None:
                st = states.get(entity_id)
                if st is not None:
                    coro = zc.async_update_zone(entity_id, st)
                    if inspect.iscoroutine(coro):
                        await coro
            cb()
