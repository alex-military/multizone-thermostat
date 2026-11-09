import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

from ..const import DOMAIN
try:
    from ..custom_types import PreWindowState
except ImportError:
    from ..zone_manager import PreWindowState

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
        self._presets_heat: dict[str, dict] = {}
        self._presets_cool: dict[str, dict] = {}
        self._presets: dict[str, dict] = self._presets_heat
        self._settings: dict[str, Any] = {}

    @property
    def pre_window_state(self) -> dict[str, str]:
        return self._pre_window_state

    @property
    def presets(self) -> dict[str, dict]:
        """Backward-compatible access returning heating presets."""
        return self._presets_heat

    @property
    def presets_heat(self) -> dict[str, dict]:
        """Return heating presets."""
        return self._presets_heat

    @property
    def presets_cool(self) -> dict[str, dict]:
        """Return cooling presets."""
        return self._presets_cool

    @property
    def settings(self) -> dict[str, Any]:
        return self._settings

    def _get_settings_data(self) -> dict[str, Any]:
        return self._settings

    def _get_window_data(self) -> dict[str, str]:
        return self._pre_window_state

    def _get_preset_data(self) -> dict[str, dict]:
        return {
            "presets_heat": self._presets_heat,
            "presets_cool": self._presets_cool,
        }

    async def async_initialize(self) -> None:
        """Load all stored states from disk."""
        stored_windows = await self._window_store.async_load()
        if stored_windows is None:
            # Try to migrate from legacy global window store
            stored_windows = await self._legacy_window_store.async_load()
            if stored_windows and isinstance(stored_windows, dict):
                _LOGGER.info("Migrating legacy window states to entry-specific storage")
                converted = {
                    k: PreWindowState(v) if isinstance(v, dict) else v
                    for k, v in stored_windows.items()
                }
                self._pre_window_state.clear()
                self._pre_window_state.update(converted)
                # Save immediately to new store
                self._window_store.async_delay_save(self._get_window_data, 1.0)
        
        if stored_windows and isinstance(stored_windows, dict):
            converted = {
                k: PreWindowState(v) if isinstance(v, dict) else v
                for k, v in stored_windows.items()
            }
            self._pre_window_state.clear()
            self._pre_window_state.update(converted)
            _LOGGER.debug("Loaded pre_window_state from storage: %s", self._pre_window_state)
            
        stored_presets = await self._preset_store.async_load()
        if stored_presets and isinstance(stored_presets, dict):
            if "presets_heat" in stored_presets or "presets_cool" in stored_presets:
                self._presets_heat.clear()
                self._presets_heat.update(stored_presets.get("presets_heat", {}))
                self._presets_cool.clear()
                self._presets_cool.update(stored_presets.get("presets_cool", {}))
            else:
                self._presets_heat.clear()
                self._presets_heat.update(stored_presets)
                self._presets_cool.clear()
            _LOGGER.debug("Loaded presets from storage: heat=%s, cool=%s", self._presets_heat, self._presets_cool)
            
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

    async def async_save_windows(self, pre_window_state: dict[str, str | dict]) -> None:
        """Save window states to storage."""
        if pre_window_state is not self._pre_window_state:
            converted = {
                k: PreWindowState(v) if isinstance(v, dict) else v
                for k, v in pre_window_state.items()
            }
            self._pre_window_state.clear()
            self._pre_window_state.update(converted)
        # Bug 3 Fixed: Use delay_save
        self._window_store.async_delay_save(self._get_window_data, 5.0)

    async def async_save_presets(
        self,
        presets_heat: dict[str, dict] | None = None,
        presets_cool: dict[str, dict] | None = None,
    ) -> None:
        """Save presets to storage."""
        if presets_heat is not None:
            if isinstance(presets_heat, dict) and ("presets_heat" in presets_heat or "presets_cool" in presets_heat):
                self._presets_heat.clear()
                self._presets_heat.update(presets_heat.get("presets_heat", {}))
                if "presets_cool" in presets_heat:
                    self._presets_cool.clear()
                    self._presets_cool.update(presets_heat.get("presets_cool", {}))
            elif presets_heat is not self._presets_heat:
                self._presets_heat.clear()
                self._presets_heat.update(presets_heat)
        if presets_cool is not None and presets_cool is not self._presets_cool:
            self._presets_cool.clear()
            self._presets_cool.update(presets_cool)
        # Bug 3 Fixed: Use delay_save
        self._preset_store.async_delay_save(self._get_preset_data, 5.0)

    async def async_save_autotuner_states(
        self,
        autotuners_heat: dict,
        autotuners_cool: dict | None = None,
    ) -> None:
        """Save autotuner learning progress to storage for both heating and cooling tracks."""
        if autotuners_cool is None and isinstance(autotuners_heat, dict):
            # Check if autotuners_heat already contains "heat" or is flat dict
            if "heat" in autotuners_heat or "cool" in autotuners_heat:
                await self.async_set_data("autotuners", autotuners_heat)
                return
            data = {
                "heat": {climate_id: tuner.dump_state() for climate_id, tuner in autotuners_heat.items()},
                "cool": {},
            }
        else:
            data = {
                "heat": {climate_id: tuner.dump_state() for climate_id, tuner in autotuners_heat.items()},
                "cool": {climate_id: tuner.dump_state() for climate_id, tuner in (autotuners_cool or {}).items()},
            }
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

    def debounced_save_settings(self, delay: float = 60.0) -> None:
        """Debounced save of settings/runtime timestamps (avoids SD card wear)."""
        if hasattr(self, "_settings_store") and self._settings_store is not None:
            self._settings_store.async_delay_save(self._get_settings_data, delay)

    def async_unload(self) -> None:
        """Cancel any pending tasks on unload."""
        # Note: Store handles its own shutdown flushing via HA core events.
        pass
