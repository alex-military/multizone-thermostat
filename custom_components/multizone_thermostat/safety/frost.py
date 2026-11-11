"""Frost protection safety module."""
from __future__ import annotations

import inspect
import logging
from typing import TYPE_CHECKING

from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE
from ..const import (
    CONF_ZONE_CLIMATES,
    CONF_ZONE_NAME,
    DEFAULT_ANTI_FROST_ENABLED,
    DEFAULT_FROST_PROTECTION_TEMP,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    HVAC_MODE_COOL,
    KEY_ANTI_FROST_ENABLED,
    KEY_FROST_PROTECTION_TEMP,
    make_zone_entity_id,
)
from ..plant_config import get_zone_climates
from .watchdog import SensorWatchdog

SERVICE_SET_TEMPERATURE = "set_temperature"

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class FrostManager:
    """Manages anti-frost protection checks and emergency actions."""

    def __init__(self, hass: HomeAssistant, coordinator) -> None:
        """Initialize frost manager."""
        self.hass = hass
        self.coordinator = coordinator
        self._watchdog = SensorWatchdog(hass)
        self._pre_frost_targets: dict[str, float] = {}
        self._active_frost_emergencies: set[str] = set()
        self._sync_pre_frost_targets_from_storage()

    def _sync_pre_frost_targets_from_storage(self) -> None:
        """Synchronize in-memory pre-frost targets from persistent storage."""
        if hasattr(self.coordinator, "get_persistent_data"):
            stored = self.coordinator.get_persistent_data("pre_frost_targets", {})
            if isinstance(stored, dict):
                for k, v in stored.items():
                    if k not in self._pre_frost_targets:
                        try:
                            self._pre_frost_targets[k] = float(v)
                        except (ValueError, TypeError):
                            pass

    async def _async_persist_pre_frost_targets(self) -> None:
        """Persist pre-frost targets to coordinator storage."""
        data = dict(self._pre_frost_targets)
        if hasattr(self.coordinator, "async_set_persistent_data"):
            res = self.coordinator.async_set_persistent_data("pre_frost_targets", data)
            if inspect.isawaitable(res):
                await res
        if hasattr(self.coordinator, "_settings") and isinstance(self.coordinator._settings, dict):
            self.coordinator._settings["pre_frost_targets"] = data
        if hasattr(self.coordinator, "_persistent_data") and isinstance(self.coordinator._persistent_data, dict):
            self.coordinator._persistent_data["pre_frost_targets"] = data

    def _sync_persist_pre_frost_targets(self) -> None:
        """Synchronously persist pre-frost targets to memory dicts."""
        data = dict(self._pre_frost_targets)
        if hasattr(self.coordinator, "_settings") and isinstance(self.coordinator._settings, dict):
            self.coordinator._settings["pre_frost_targets"] = data
        if hasattr(self.coordinator, "_persistent_data") and isinstance(self.coordinator._persistent_data, dict):
            self.coordinator._persistent_data["pre_frost_targets"] = data

    def check_zone_frost(self, climate_id: str) -> bool:
        """Check if zone is in frost emergency."""
        self._sync_pre_frost_targets_from_storage()
        return self.is_zone_in_frost_emergency(climate_id)

    async def async_check_and_enforce(self) -> bool:
        """Check and enforce frost protection across zones."""
        return await self.async_handle_frost_emergencies()

    def is_zone_in_frost_emergency(self, climate_id: str) -> bool:
        """Return True if anti-frost is enabled and zone temperature is below the safety threshold."""
        if not self.coordinator.get_persistent_data(KEY_ANTI_FROST_ENABLED, DEFAULT_ANTI_FROST_ENABLED):
            return False

        # Try virtual thermostat temperature first
        st = self.hass.states.get(climate_id)
        current_temp = None
        is_faulty = (
            self.coordinator.plant_diagnostics.has_critical_sensor_fault(climate_id)
            if hasattr(self.coordinator, "plant_diagnostics")
            else False
        )
        if st and not is_faulty:
            current_temp = st.attributes.get("current_temperature")

        # WARN-02: Fallback — average TRV sensor readings if virtual thermostat has no temperature yet
        # (e.g., right after boot before TRVs have reported back)
        if current_temp is None:
            zone = self.coordinator.zone_manager.get_zone(climate_id)
            if zone:
                fallback_temp = self._watchdog.get_zone_trv_fallback_temp(zone, self.hass)
                if fallback_temp is not None:
                    current_temp = fallback_temp
                    _LOGGER.debug(
                        "Frost check for %s: using avg TRV temp %.1f°C (virtual has no reading)",
                        climate_id,
                        current_temp,
                    )

        if current_temp is None:
            # L5 fix: If sensor has a critical fault and no valve readings are available,
            # check outdoor weather sensor. If outdoor temperature is freezing (<= 2.0°C),
            # assume conservative frost emergency to prevent pipe freeze.
            weather_id = getattr(self.coordinator, "weather_sensor_id", None)
            if weather_id and hasattr(self.hass, "states") and self.hass.states:
                w_st = self.hass.states.get(weather_id)
                if w_st and w_st.state not in ("unavailable", "unknown", None):
                    out_t = w_st.attributes.get("temperature") if getattr(w_st, "attributes", None) else None
                    if out_t is not None:
                        try:
                            if float(out_t) <= 2.0:
                                _LOGGER.warning(
                                    "Frost check for %s: Sensor faulty & no valves, but outdoor temp is %.1f°C! Engaging safety frost protection.",
                                    climate_id,
                                    float(out_t),
                                )
                                return True
                        except (ValueError, TypeError):
                            pass
            return False

        frost_temp = float(
            self.coordinator.get_persistent_data(KEY_FROST_PROTECTION_TEMP, DEFAULT_FROST_PROTECTION_TEMP)
        )
        try:
            t = float(current_temp)
            # Hysteresis: enter emergency below frost_temp, exit above frost_temp + 1.5°C
            if climate_id in self._active_frost_emergencies:
                is_danger = t < (frost_temp + 1.5)
            else:
                is_danger = t < frost_temp

            if is_danger:
                self._active_frost_emergencies.add(climate_id)
            else:
                self._active_frost_emergencies.discard(climate_id)
            return is_danger
        except (ValueError, TypeError):
            return False

    async def async_handle_frost_emergencies(self) -> bool:
        """Evaluate frost emergency across all zones and trigger emergency heating if needed.
        
        Returns True if any zone triggered a frost emergency.
        """
        frost_emergency = False
        self._sync_pre_frost_targets_from_storage()
        if not self.coordinator.get_persistent_data(KEY_ANTI_FROST_ENABLED, DEFAULT_ANTI_FROST_ENABLED):
            return False

        for zone in self.coordinator.zones:
            climate_id = make_zone_entity_id(zone[CONF_ZONE_NAME])
            if self.is_zone_in_frost_emergency(climate_id):
                frost_emergency = True
                _LOGGER.warning(
                    "Anti-Frost emergency triggered for zone %s! Forcing emergency heating.",
                    climate_id,
                )
                # Force zone demand to 100% so boiler PWM activates
                self.coordinator.set_zone_demand(climate_id, 100.0)
                # Force zone to HEAT mode if OFF or COOL
                st = self.hass.states.get(climate_id)
                if st and st.state in (HVAC_MODE_OFF, HVAC_MODE_COOL, "off", "cool"):
                    await self.coordinator._async_set_hvac_mode(climate_id, HVAC_MODE_HEAT)

                # Set target temperature above frost threshold so TRV internal PID opens valve
                frost_target = (
                    float(
                        self.coordinator.get_persistent_data(
                            KEY_FROST_PROTECTION_TEMP, DEFAULT_FROST_PROTECTION_TEMP
                        )
                    )
                    + 3.0
                )
                st = self.hass.states.get(climate_id)
                if st:
                    # Save user target prior to frost override
                    curr_user_target = st.attributes.get(ATTR_TEMPERATURE)
                    if curr_user_target and curr_user_target > frost_target and climate_id not in self._pre_frost_targets:
                        self._pre_frost_targets[climate_id] = float(curr_user_target)
                        await self._async_persist_pre_frost_targets()

                    if st.attributes.get(ATTR_TEMPERATURE) != frost_target:
                        await self.hass.services.async_call(
                            CLIMATE_DOMAIN,
                            SERVICE_SET_TEMPERATURE,
                            {ATTR_ENTITY_ID: climate_id, ATTR_TEMPERATURE: frost_target},
                            blocking=False,
                        )
            else:
                # Zone is NOT in frost emergency: restore previous user target if it was overridden
                if climate_id in self._pre_frost_targets:
                    restored_target = self._pre_frost_targets.pop(climate_id)
                    await self._async_persist_pre_frost_targets()
                    _LOGGER.info(
                        "Anti-Frost emergency ended for %s: restoring user target to %.1f°C",
                        climate_id,
                        restored_target,
                    )
                    await self.hass.services.async_call(
                        CLIMATE_DOMAIN,
                        SERVICE_SET_TEMPERATURE,
                        {ATTR_ENTITY_ID: climate_id, ATTR_TEMPERATURE: restored_target},
                        blocking=False,
                    )

        return frost_emergency


FrostProtectionManager = FrostManager
