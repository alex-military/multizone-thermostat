import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

from ..const import DOMAIN

WINDOW_STORAGE_VERSION = 1
PRESET_STORAGE_VERSION = 1
SETTINGS_STORAGE_VERSION = 1

class StorageManager:
    """Gestisce la persistenza locale (I/O) dell'integrazione Multizone Thermostat."""

    def __init__(self, hass: HomeAssistant, entry_id: str):
        self.hass = hass
        self.entry_id = entry_id
        
        # Bug 2 Fixed: Isolate window states per entry_id
        self._window_store = Store(hass, WINDOW_STORAGE_VERSION, f"{DOMAIN}_{entry_id}_window_states")
        self._preset_store = Store(hass, PRESET_STORAGE_VERSION, f"{DOMAIN}_{entry_id}_presets")
        self._settings_store = Store(hass, SETTINGS_STORAGE_VERSION, f"{DOMAIN}_{entry_id}_settings")
        
        # Legacy store for migration
        self._legacy_window_store = Store(hass, WINDOW_STORAGE_VERSION, f"{DOMAIN}.window_states")
        
        self._pre_window_state: dict[str, str] = {}
        self._presets: dict[str, dict] = {}
        self._settings: dict[str, Any] = {}

    @property
    def pre_window_state(self) -> dict[str, str]:
        return self._pre_window_state

    @property
    def presets(self) -> dict[str, dict]:
        return self._presets

    @property
    def settings(self) -> dict[str, Any]:
        return self._settings

    def _get_settings_data(self) -> dict[str, Any]:
        return self._settings

    def _get_window_data(self) -> dict[str, str]:
        return self._pre_window_state

    def _get_preset_data(self) -> dict[str, dict]:
        return self._presets

    async def async_initialize(self) -> None:
        """Load all stored states from disk."""
        stored_windows = await self._window_store.async_load()
        if stored_windows is None:
            # Try to migrate from legacy global window store
            stored_windows = await self._legacy_window_store.async_load()
            if stored_windows and isinstance(stored_windows, dict):
                _LOGGER.info("Migrating legacy window states to entry-specific storage")
                self._pre_window_state.clear()
                self._pre_window_state.update(stored_windows)
                # Save immediately to new store
                self._window_store.async_delay_save(self._get_window_data, 1.0)
        
        if stored_windows and isinstance(stored_windows, dict):
            self._pre_window_state.clear()
            self._pre_window_state.update(stored_windows)
            _LOGGER.debug("Loaded pre_window_state from storage: %s", self._pre_window_state)
            
        stored_presets = await self._preset_store.async_load()
        if stored_presets and isinstance(stored_presets, dict):
            self._presets.clear()
            self._presets.update(stored_presets)
            _LOGGER.debug("Loaded presets from storage: %s", self._presets)
            
        stored_settings = await self._settings_store.async_load()
        if stored_settings and isinstance(stored_settings, dict):
            self._settings.clear()
            self._settings.update(stored_settings)
            _LOGGER.debug("Loaded settings from storage: %s", self._settings)

    def get_data(self, key: str, default: Any = None) -> Any:
        """Get a persistent setting."""
        return self._settings.get(key, default)

    async def async_set_data(self, key: str, value: Any) -> None:
        """Set a persistent setting and save."""
        self._settings[key] = value
        # Bug 3 Fixed: Use delay_save for settings to prevent IO spam (5 seconds)
        self._settings_store.async_delay_save(self._get_settings_data, 5.0)

    async def async_save_windows(self, pre_window_state: dict[str, str]) -> None:
        """Save window states to storage."""
        if pre_window_state is not self._pre_window_state:
            self._pre_window_state.clear()
            self._pre_window_state.update(pre_window_state)
        # Bug 3 Fixed: Use delay_save
        self._window_store.async_delay_save(self._get_window_data, 5.0)

    async def async_save_presets(self, presets: dict[str, dict]) -> None:
        """Save presets to storage."""
        if presets is not self._presets:
            self._presets.clear()
            self._presets.update(presets)
        # Bug 3 Fixed: Use delay_save
        self._preset_store.async_delay_save(self._get_preset_data, 5.0)

    async def async_save_autotuner_states(self, autotuners: dict) -> None:
        """Save autotuner learning progress to storage."""
        data = {climate_id: tuner.dump_state() for climate_id, tuner in autotuners.items()}
        await self.async_set_data("autotuners", data)

    async def async_save_thermal_states(self, thermal_models: dict) -> None:
        """Save thermal model learning progress to storage."""
        data = {climate_id: model.dump_state() for climate_id, model in thermal_models.items()}
        await self.async_set_data("thermal_models", data)

    def debounced_save_thermal_states(self, thermal_models: dict) -> None:
        """Debounced save of thermal model learning progress (avoid SD card wear)."""
        data = {climate_id: model.dump_state() for climate_id, model in thermal_models.items()}
        self._settings["thermal_models"] = data
        
        # Bug 1 Fixed: Use native HA Store delay_save which guarantees flush on HA stop
        self._settings_store.async_delay_save(self._get_settings_data, 120.0)

    def async_unload(self) -> None:
        """Cancel any pending tasks on unload."""
        # Note: Store handles its own shutdown flushing via HA core events.
        pass
