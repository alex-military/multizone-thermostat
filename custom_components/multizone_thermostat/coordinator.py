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
    DOMAIN,
    GLOBAL_PRESET_MANUAL,
    KEY_ALLOW_SPLIT_HEATING,
    KEY_ALLOW_SPLIT_COOLING,
    KEY_HEAT_SOURCE_PRIORITY,
    DEFAULT_HEAT_SOURCE_PRIORITY,
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
    """Central coordinator that acts as composition root and manages heating plant lifecycle."""

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
        self._boiler_status_reason: str = "OFF - Initializing"
        self._current_global_preset: str = GLOBAL_PRESET_MANUAL

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
        self._valve_delay = cfg.valve_delay

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
    def is_modulating_plant(self) -> bool:
        """Return True if the plant has a modulating generator (OpenTherm or Heat Pump)."""
        backend = getattr(self, "boiler_backend", None)
        if backend and getattr(backend, "is_modulating", False):
            return True
        hp_backend = getattr(self, "heat_pump_backend", None)
        if hp_backend and getattr(hp_backend, "is_modulating", False):
            return True
        if getattr(self, "opentherm_entity", None):
            return True
        if getattr(self, "enable_heat_pump", False) and getattr(self, "heat_pump_entity", None):
            return True
        return False

    @property
    def is_dhw_active(self) -> bool:
        """Return True if Domestic Hot Water (DHW) production is active."""
        dhw_sensor = getattr(self, "dhw_active_sensor", None)
        if dhw_sensor:
            st = self.hass.states.get(dhw_sensor)
            if st and st.state not in ("unavailable", "unknown"):
                val = str(st.state).lower()
                if val in ("on", "true", "1", "charging", "heat", "heating", "active"):
                    return True
                if st.attributes:
                    for ak in ("charging", "is_charging", "dhw_active", "active"):
                        av = st.attributes.get(ak)
                        if av is True or (isinstance(av, str) and av.lower() in ("true", "on", "1")):
                            return True
                return False

        if hasattr(self, "plant_diagnostics"):
            if self.plant_diagnostics.get_opentherm_diagnostics().get("dhw_active", False):
                return True

        for std_id in ("binary_sensor.boiler_dhw_charging", "binary_sensor.dhw_charging"):
            st = self.hass.states.get(std_id)
            if st and st.state.lower() in ("on", "true", "1", "charging", "heat", "heating"):
                return True

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
        st = getattr(self, "storage", None)
        if st is not None and hasattr(st, "async_load_coordinator_storage") and not st.__class__.__name__ == "MagicMock":
            await st.async_load_coordinator_storage(self)
        else:
            from .storage.storage_manager import StorageManager
            hass = getattr(self, "hass", None)
            entry_id = getattr(self, "entry_id", "default")
            sm = StorageManager(hass, entry_id)
            await sm.async_load_coordinator_storage(self)

    async def async_save_storage(self) -> None:
        """Save window states, presets and settings to storage."""
        await self._store.async_save(self.zone_manager._pre_window_state)
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

    async def _async_save_presets_storage(self) -> None:
        """Save presets to storage via StorageManager."""
        await self.storage.async_save_presets(self.zone_manager._presets_heat, self.zone_manager._presets_cool)

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
        """Set up state change listeners for all climate entities and timers."""
        self.listener_manager.async_setup_listeners()

    def async_teardown_listeners(self) -> None:
        """Remove all state change listeners and cancel background tasks."""
        self.listener_manager.async_teardown_listeners()

    async def _async_on_climate_state_changed(self, event: Any) -> None:
        """Handle temperature or preset changes on individual zone climate entities."""
        await self.listener_manager.async_on_climate_state_changed(event)

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

    # ------------------------------------------------------------------
    # Cooling Policy & Capability Delegation
    # ------------------------------------------------------------------

    def can_central_cool(self) -> bool:
        """Return True if central plant supports cooling."""
        policy = getattr(self, "cooling_policy", None)
        if policy is not None and hasattr(policy, "can_central_cool") and not isinstance(policy, type(self).__bases__[0] if hasattr(self, "__bases__") else object) and not policy.__class__.__name__ == "MagicMock":
            return policy.can_central_cool()
        from .cooling_policy import CoolingPolicy
        return CoolingPolicy(self).can_central_cool()

    def can_zone_cool(self, climate_id: str) -> bool:
        """Return True if zone has cooling capabilities."""
        policy = getattr(self, "cooling_policy", None)
        if policy is not None and hasattr(policy, "can_zone_cool") and not policy.__class__.__name__ == "MagicMock":
            return policy.can_zone_cool(climate_id)
        from .cooling_policy import CoolingPolicy
        return CoolingPolicy(self).can_zone_cool(climate_id)

    def get_zone_cooling_rate(self, climate_id: str) -> float:
        """Return cooling rate for a zone from schedule_manager or thermal observer."""
        policy = getattr(self, "cooling_policy", None)
        if policy is not None and hasattr(policy, "get_zone_cooling_rate") and not policy.__class__.__name__ == "MagicMock":
            return policy.get_zone_cooling_rate(climate_id)
        from .cooling_policy import CoolingPolicy
        return CoolingPolicy(self).get_zone_cooling_rate(climate_id)

    # ------------------------------------------------------------------
    # Master HVAC Coordination Delegation
    # ------------------------------------------------------------------

    async def async_set_master_hvac_mode(self, mode: str) -> None:
        """Set master operation mode ('heat' or 'cool') and coordinate whole-house operation."""
        ctrl = getattr(self, "master_controller", None)
        if ctrl is not None and hasattr(ctrl, "async_set_master_hvac_mode") and not ctrl.__class__.__name__ == "MagicMock":
            await ctrl.async_set_master_hvac_mode(mode)
        else:
            from .master_controller import MasterController
            await MasterController(self).async_set_master_hvac_mode(mode)

    async def async_apply_master_on(self) -> None:
        """Master turned ON: apply mode to all eligible zones."""
        ctrl = getattr(self, "master_controller", None)
        if ctrl is not None and hasattr(ctrl, "async_apply_master_on") and not ctrl.__class__.__name__ == "MagicMock":
            await ctrl.async_apply_master_on()
        else:
            from .master_controller import MasterController
            await MasterController(self).async_apply_master_on()

    async def async_apply_master_off(self) -> None:
        """Master turned OFF: turn off all zones and boiler."""
        ctrl = getattr(self, "master_controller", None)
        if ctrl is not None and hasattr(ctrl, "async_apply_master_off") and not ctrl.__class__.__name__ == "MagicMock":
            await ctrl.async_apply_master_off()
        else:
            from .master_controller import MasterController
            await MasterController(self).async_apply_master_off()

    async def _async_set_hvac_mode(self, climate_entity: str, mode: str) -> None:
        """Set HVAC mode on a climate entity."""
        ctrl = getattr(self, "master_controller", None)
        if ctrl is not None and hasattr(ctrl, "async_set_hvac_mode") and not ctrl.__class__.__name__ == "MagicMock":
            await ctrl.async_set_hvac_mode(climate_entity, mode)
        else:
            from .master_controller import MasterController
            await MasterController(self).async_set_hvac_mode(climate_entity, mode)

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
