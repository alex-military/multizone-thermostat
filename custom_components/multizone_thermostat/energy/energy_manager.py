"""Energy Manager for Multizone Thermostat (Phase 11).

Single Responsibility: Monitors PV solar power, grid export, battery storage, and external
optimization signals (EMHASS/Predbat). Computes solar surplus / inverter clipping, enforces
battery reserve protections (night reservation + continuous discharge guard), and manages
dynamic heat source priority permissions.
"""
from __future__ import annotations

import logging
import inspect
import time
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from ..const import (
    CONF_ENERGY_MANAGEMENT_ENABLED,
    DEFAULT_ENERGY_MANAGEMENT_ENABLED,
    CONF_SOLAR_POWER_SENSOR,
    CONF_GRID_EXPORT_SENSOR,
    CONF_BATTERY_SOC_SENSOR,
    CONF_BATTERY_POWER_SENSOR,
    CONF_EXTERNAL_SOLAR_OVERRIDE_ENTITY,
    CONF_SOLAR_EXPORT_THRESHOLD,
    DEFAULT_SOLAR_EXPORT_THRESHOLD,
    CONF_BATTERY_MIN_RESERVE_SOC,
    DEFAULT_BATTERY_MIN_RESERVE_SOC,
    CONF_SOLAR_MIN_RUN_TIME,
    DEFAULT_SOLAR_MIN_RUN_TIME,
    CONF_SOLAR_OVERHEAT_OFFSET,
    DEFAULT_SOLAR_OVERHEAT_OFFSET,
    CONF_SOLAR_FORECAST_SENSOR,
    CONF_SOLAR_IRRADIANCE_SENSOR,
    CONF_BATTERY_MAX_DISCHARGE_TIME,
    DEFAULT_BATTERY_MAX_DISCHARGE_TIME,
    CONF_BATTERY_POWER_INVERTED,
    DEFAULT_BATTERY_POWER_INVERTED,
    KEY_ALLOW_SPLIT_HEATING,
    KEY_ALLOW_SPLIT_COOLING,
    KEY_HEAT_SOURCE_PRIORITY,
    HEAT_SOURCE_PRIORITIES,
    DEFAULT_HEAT_SOURCE_PRIORITY,
    SOURCE_PRIORITY_GAS,
    SOURCE_PRIORITY_ELECTRIC,
    SOURCE_PRIORITY_GAS_ONLY,
    SOURCE_PRIORITY_ELECTRIC_ONLY,
)

_LOGGER = logging.getLogger(__name__)


class EnergyManager:
    """Evaluates real-time solar surplus and manages heat source arbitration."""

    def __init__(self, hass: HomeAssistant, coordinator: Any, config: dict[str, Any]) -> None:
        """Initialize EnergyManager."""
        self.hass = hass
        self.coordinator = coordinator
        self.config = config

        self.enabled: bool = bool(
            config.get(CONF_ENERGY_MANAGEMENT_ENABLED, DEFAULT_ENERGY_MANAGEMENT_ENABLED)
        )
        self.solar_sensor: str | None = config.get(CONF_SOLAR_POWER_SENSOR)
        self.export_sensor: str | None = config.get(CONF_GRID_EXPORT_SENSOR)
        self.battery_sensor: str | None = config.get(CONF_BATTERY_SOC_SENSOR)
        self.battery_power_sensor: str | None = config.get(CONF_BATTERY_POWER_SENSOR)
        self.forecast_sensor: str | None = config.get(CONF_SOLAR_FORECAST_SENSOR)
        self.irradiance_sensor: str | None = config.get(CONF_SOLAR_IRRADIANCE_SENSOR)
        self.override_entity: str | None = config.get(CONF_EXTERNAL_SOLAR_OVERRIDE_ENTITY)
        self.battery_power_inverted: bool = bool(config.get(CONF_BATTERY_POWER_INVERTED, DEFAULT_BATTERY_POWER_INVERTED))

        try:
            self.export_threshold: float = float(
                config.get(CONF_SOLAR_EXPORT_THRESHOLD, DEFAULT_SOLAR_EXPORT_THRESHOLD)
            )
        except (ValueError, TypeError):
            self.export_threshold = DEFAULT_SOLAR_EXPORT_THRESHOLD

        try:
            self.min_reserve_soc: float = float(
                config.get(CONF_BATTERY_MIN_RESERVE_SOC, DEFAULT_BATTERY_MIN_RESERVE_SOC)
            )
        except (ValueError, TypeError):
            self.min_reserve_soc = DEFAULT_BATTERY_MIN_RESERVE_SOC

        try:
            self.solar_min_run_time: float = (
                float(config[CONF_SOLAR_MIN_RUN_TIME])
                if CONF_SOLAR_MIN_RUN_TIME in config and config[CONF_SOLAR_MIN_RUN_TIME] is not None
                else float(DEFAULT_SOLAR_MIN_RUN_TIME)
            )
        except (ValueError, TypeError):
            self.solar_min_run_time = float(DEFAULT_SOLAR_MIN_RUN_TIME)

        try:
            self.solar_overheat_offset: float = float(
                config.get(CONF_SOLAR_OVERHEAT_OFFSET, DEFAULT_SOLAR_OVERHEAT_OFFSET)
            )
        except (ValueError, TypeError):
            self.solar_overheat_offset = float(DEFAULT_SOLAR_OVERHEAT_OFFSET)

        try:
            self.battery_max_discharge_time: float = float(
                config.get(CONF_BATTERY_MAX_DISCHARGE_TIME, DEFAULT_BATTERY_MAX_DISCHARGE_TIME)
            )
        except (ValueError, TypeError):
            self.battery_max_discharge_time = float(DEFAULT_BATTERY_MAX_DISCHARGE_TIME)

        self._unsub_listeners: list[Any] = []
        self._last_surplus_state: bool = False
        self._discharge_start_timestamp: float | None = None

    def is_energy_management_enabled(self) -> bool:
        """Return True if energy management is active."""
        return self.enabled

    def _safe_float(self, val: Any) -> float | None:
        """Safely convert state value to float, handling common unit conversions."""
        if val in (None, "unavailable", "unknown", ""):
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    def get_solar_power(self) -> float | None:
        """Return current solar generation power in Watts."""
        if not self.solar_sensor or not hasattr(self.hass, "states"):
            return None
        st = self.hass.states.get(self.solar_sensor)
        if not st:
            return None
        val = self._safe_float(st.state)
        if val is None:
            return None
        unit = st.attributes.get("unit_of_measurement", "").lower() if getattr(st, "attributes", None) else ""
        if unit == "kw":
            return val * 1000.0
        return val

    def get_grid_export(self) -> float | None:
        """Return current grid export power in Watts (positive = exporting)."""
        if not self.export_sensor or not hasattr(self.hass, "states"):
            return None
        st = self.hass.states.get(self.export_sensor)
        if not st:
            return None
        val = self._safe_float(st.state)
        if val is None:
            return None
        unit = st.attributes.get("unit_of_measurement", "").lower() if getattr(st, "attributes", None) else ""
        if unit == "kw":
            return val * 1000.0
        return val

    def get_battery_soc(self) -> float | None:
        """Return current home battery State of Charge in percentage."""
        if not self.battery_sensor or not hasattr(self.hass, "states"):
            return None
        st = self.hass.states.get(self.battery_sensor)
        if not st:
            return None
        return self._safe_float(st.state)

    def get_battery_power(self) -> float | None:
        """Return battery power in Watts (standard: positive = charging, negative = discharging)."""
        if not self.battery_power_sensor or not hasattr(self.hass, "states"):
            return None
        st = self.hass.states.get(self.battery_power_sensor)
        if not st:
            return None
        val = self._safe_float(st.state)
        if val is None:
            return None
        unit = st.attributes.get("unit_of_measurement", "").lower() if getattr(st, "attributes", None) else ""
        if unit == "kw":
            val *= 1000.0
        if self.battery_power_inverted:
            val = -val
        return val

    def get_solar_forecast(self) -> float | None:
        """Return solar forecast value (e.g. Watts or kWh remaining)."""
        if not self.forecast_sensor or not hasattr(self.hass, "states"):
            return None
        st = self.hass.states.get(self.forecast_sensor)
        if not st:
            return None
        return self._safe_float(st.state)

    def get_solar_irradiance(self) -> float | None:
        """Return solar irradiance in W/m² or lux."""
        if not self.irradiance_sensor or not hasattr(self.hass, "states"):
            return None
        st = self.hass.states.get(self.irradiance_sensor)
        if not st:
            return None
        return self._safe_float(st.state)

    def is_battery_discharging_too_long(self) -> bool:
        """Return True if battery has been actively discharging (> 150W) for longer than max discharge time."""
        bat_p = self.get_battery_power()
        if bat_p is None:
            self._discharge_start_timestamp = None
            return False

        # If discharging (negative power < -150W)
        if bat_p < -150.0:
            now_mono = time.monotonic()
            if self._discharge_start_timestamp is None:
                self._discharge_start_timestamp = now_mono
                return False
            elapsed_min = (now_mono - self._discharge_start_timestamp) / 60.0
            if elapsed_min >= self.battery_max_discharge_time:
                _LOGGER.warning(
                    "Battery discharge guard tripped: discharging %.0fW continuously for %.1f min (limit %.1f min). Suppressing electric surplus to protect night reserve.",
                    bat_p,
                    elapsed_min,
                    self.battery_max_discharge_time,
                )
                return True
        else:
            self._discharge_start_timestamp = None

        return False

    def get_external_override_power(self) -> float | None:
        """Return allocated deferrable load power in Watts if override entity is numeric (e.g. EMHASS sensor.p_deferrable0)."""
        if not self.override_entity or not hasattr(self.hass, "states"):
            return None
        st = self.hass.states.get(self.override_entity)
        if not st:
            return None
        val = self._safe_float(st.state)
        if val is None:
            return None
        unit = st.attributes.get("unit_of_measurement", "").lower() if getattr(st, "attributes", None) else ""
        if unit == "kw":
            return val * 1000.0
        return val

    def is_external_override_active(self) -> bool:
        """Check if an external solar optimizer signal (EMHASS / Predbat) is active."""
        if not self.override_entity or not hasattr(self.hass, "states"):
            return False
        st = self.hass.states.get(self.override_entity)
        if not st or st.state in (None, "unavailable", "unknown", ""):
            return False
        raw = str(st.state).strip().lower()
        if raw in ("on", "true", "1", "active", "charging", "exporting", "boost"):
            return True
        if raw in ("off", "false", "0", "idle", "standby"):
            return False
        num_val = self._safe_float(st.state)
        if num_val is not None:
            return num_val > 0.0
        return False

    def is_solar_surplus(self) -> bool:
        """Calculate whether free solar surplus is currently available.

        Priority order:
        1. Continuous Battery Discharge Guard -> if battery is discharging for too long, strictly suppresses surplus!
        2. External optimizer override (EMHASS/Predbat) -> Forces True immediately.
        3. Energy management enabled with sensor telemetry:
           - Battery reserve check: if battery SOC < min_reserve_soc, surplus is suppressed (reserve for the night).
           - Off-Grid / Battery Saturated Clipping: if SOC >= 95% and PV >= 300W (or battery charging >= 500W), surplus is True.
           - Grid export check: if exporting >= export_threshold, surplus is True.
           - Solar power check: if solar power >= export_threshold and no export sensor configured.
        """
        # 1. Battery discharge guard has top priority against wasting stored energy
        if self.is_battery_discharging_too_long():
            return False

        # 2. External override
        if self.is_external_override_active():
            _LOGGER.debug("Solar surplus ACTIVE via external optimizer override (%s)", self.override_entity)
            return True

        if not self.enabled:
            return False

        # 3. Night reserve protection (SoC check)
        soc = self.get_battery_soc()
        if soc is not None and soc < self.min_reserve_soc:
            _LOGGER.debug(
                "Solar surplus suppressed: Battery SoC %.1f%% below reserve %.1f%%",
                soc,
                self.min_reserve_soc,
            )
            return False

        # 4. Off-Grid & Zero-Export Clipping (Battery high >= 95% & PV generating >= 300W or charging)
        solar_w = self.get_solar_power()
        bat_p = self.get_battery_power()
        if soc is not None and soc >= 95.0:
            if (solar_w is not None and solar_w >= 300.0) or (bat_p is not None and bat_p >= 400.0):
                _LOGGER.debug(
                    "Solar surplus ACTIVE via Off-Grid/Battery Saturation (SoC=%.1f%%, PV=%sW, BatP=%sW)",
                    soc,
                    solar_w,
                    bat_p,
                )
                return True

        # 5. Grid Export (if export sensor is available)
        export_w = self.get_grid_export()
        if export_w is not None:
            is_surplus = export_w >= self.export_threshold
            _LOGGER.debug(
                "Solar surplus check (export): %.1fW >= %.1fW -> %s",
                export_w,
                self.export_threshold,
                is_surplus,
            )
            return is_surplus

        # 6. Solar Generation fallback (pure Off-Grid without export sensor)
        if solar_w is not None:
            is_surplus = solar_w >= self.export_threshold
            _LOGGER.debug(
                "Solar surplus check (generation): %.1fW >= %.1fW -> %s",
                solar_w,
                self.export_threshold,
                is_surplus,
            )
            return is_surplus

        return False

    def is_split_heating_allowed(self) -> bool:
        """Return True if split heating is allowed by master switch."""
        if hasattr(self.coordinator, "get_persistent_data"):
            val = self.coordinator.get_persistent_data(KEY_ALLOW_SPLIT_HEATING, True)
            return bool(val)
        return True

    def is_split_cooling_allowed(self) -> bool:
        """Return True if split cooling is allowed by master switch."""
        if hasattr(self.coordinator, "get_persistent_data"):
            val = self.coordinator.get_persistent_data(KEY_ALLOW_SPLIT_COOLING, True)
            return bool(val)
        return True

    def get_heat_source_priority(self) -> str:
        """Return current heat source arbitration priority."""
        if hasattr(self.coordinator, "get_persistent_data"):
            val = self.coordinator.get_persistent_data(
                KEY_HEAT_SOURCE_PRIORITY, DEFAULT_HEAT_SOURCE_PRIORITY
            )
            valid = set(HEAT_SOURCE_PRIORITIES) | {SOURCE_PRIORITY_GAS, SOURCE_PRIORITY_ELECTRIC}
            if val in valid:
                return str(val)
        return DEFAULT_HEAT_SOURCE_PRIORITY

    async def async_set_split_heating_allowed(self, allowed: bool) -> None:
        """Persist master permission for split heating."""
        if hasattr(self.coordinator, "async_set_persistent_data"):
            await self.coordinator.async_set_persistent_data(KEY_ALLOW_SPLIT_HEATING, bool(allowed))
        self._notify_coordinator_update()

    async def async_set_split_cooling_allowed(self, allowed: bool) -> None:
        """Persist master permission for split cooling."""
        if hasattr(self.coordinator, "async_set_persistent_data"):
            await self.coordinator.async_set_persistent_data(KEY_ALLOW_SPLIT_COOLING, bool(allowed))
        self._notify_coordinator_update()

    async def async_set_heat_source_priority(self, priority: str) -> None:
        """Persist heat source priority (auto, hybrid, combined, gas_only, electric_only)."""
        valid_priorities = set(HEAT_SOURCE_PRIORITIES) | {SOURCE_PRIORITY_GAS, SOURCE_PRIORITY_ELECTRIC}
        if priority not in valid_priorities:
            raise ValueError(f"Invalid heat source priority: {priority}")
        if hasattr(self.coordinator, "async_set_persistent_data"):
            await self.coordinator.async_set_persistent_data(KEY_HEAT_SOURCE_PRIORITY, priority)
        self._notify_coordinator_update()

    def _notify_coordinator_update(self) -> None:
        """Trigger an update on all zones when energy state or priority changes."""
        if hasattr(self.coordinator, "async_update_all_climates"):
            coro = self.coordinator.async_update_all_climates()
            if inspect.iscoroutine(coro) and hasattr(self.hass, "async_create_task"):
                self.hass.async_create_task(coro)
            elif callable(coro):
                coro()

    @callback
    def _async_on_energy_state_change(self, event: Any) -> None:
        """Handle state changes on tracked solar/grid/battery/override entities."""
        current_surplus = self.is_solar_surplus()
        if current_surplus != self._last_surplus_state:
            _LOGGER.info(
                "EnergyManager: Solar surplus state changed: %s -> %s",
                self._last_surplus_state,
                current_surplus,
            )
            self._last_surplus_state = current_surplus
            self._notify_coordinator_update()

    async def async_start(self) -> None:
        """Start tracking configured energy entities."""
        self.setup_listeners()
        self._last_surplus_state = self.is_solar_surplus()

    def async_stop(self) -> None:
        """Stop tracking configured energy entities."""
        self.async_unload()

    def setup_listeners(self) -> None:
        """Subscribe to state changes for configured energy sensors."""
        self.async_unload()
        tracked: list[str] = []
        for entity_id in (
            self.solar_sensor,
            self.export_sensor,
            self.battery_sensor,
            self.battery_power_sensor,
            self.forecast_sensor,
            self.irradiance_sensor,
            self.override_entity,
        ):
            if entity_id and isinstance(entity_id, str) and entity_id != "none":
                tracked.append(entity_id)

        if tracked:
            self._unsub_listeners.append(
                async_track_state_change_event(
                    self.hass, tracked, self._async_on_energy_state_change
                )
            )
            _LOGGER.debug("EnergyManager tracking entities: %s", tracked)

    def async_unload(self) -> None:
        """Remove all state listeners."""
        for unsub in self._unsub_listeners:
            try:
                unsub()
            except Exception:
                pass
        self._unsub_listeners.clear()

    def get_diagnostics(self) -> dict[str, Any]:
        """Return energy telemetry for diagnostic views."""
        return {
            "enabled": self.enabled,
            "solar_power_w": self.get_solar_power(),
            "grid_export_w": self.get_grid_export(),
            "battery_soc_pct": self.get_battery_soc(),
            "battery_power_w": self.get_battery_power(),
            "battery_discharging_guard_active": self.is_battery_discharging_too_long(),
            "solar_forecast": self.get_solar_forecast(),
            "solar_irradiance": self.get_solar_irradiance(),
            "external_override_active": self.is_external_override_active(),
            "external_override_power_w": self.get_external_override_power(),
            "is_solar_surplus": self.is_solar_surplus(),
            "export_threshold_w": self.export_threshold,
            "min_reserve_soc_pct": self.min_reserve_soc,
            "solar_min_run_time_min": self.solar_min_run_time,
            "solar_overheat_offset_c": self.solar_overheat_offset,
            "allow_split_heating": self.is_split_heating_allowed(),
            "allow_split_cooling": self.is_split_cooling_allowed(),
            "heat_source_priority": self.get_heat_source_priority(),
        }
