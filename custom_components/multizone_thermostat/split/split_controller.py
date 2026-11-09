"""Split Zone Controller for Multizone Thermostat (Phase 11).

Single Responsibility: Manages room-level direct-expansion Split AC / Heat Pump units
(Quick Heat Boost, Room Probe Sensor Injection, Solar Self-Consumption Actuation, and
Hydronic Demand Decoupling).
"""
from __future__ import annotations

import logging
import time
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE

from ..const import (
    CONF_ZONE_NAME,
    make_zone_entity_id,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    HVAC_MODE_COOL,
    ZONE_MODE_BYPASS,
    CONF_ZONE_SPLIT_CLIMATE,
    CONF_ZONE_SPLIT_ROLE,
    SPLIT_ROLE_HEAT_COOL,
    SPLIT_ROLE_HEATING_ONLY,
    SPLIT_ROLE_COOLING_ONLY,
    DEFAULT_SPLIT_ROLE,
    CONF_ZONE_SPLIT_SOLAR_PRIORITY,
    DEFAULT_SPLIT_SOLAR_PRIORITY,
    CONF_ZONE_SPLIT_QUICK_BOOST,
    DEFAULT_SPLIT_QUICK_BOOST,
    CONF_ZONE_SPLIT_BOOST_DELTA,
    DEFAULT_SPLIT_BOOST_DELTA,
    CONF_ZONE_SPLIT_SENSOR_INJECTION,
    DEFAULT_SPLIT_SENSOR_INJECTION,
    KEY_ALLOW_SPLIT_HEATING,
    KEY_ALLOW_SPLIT_COOLING,
    KEY_HEAT_SOURCE_PRIORITY,
    SOURCE_PRIORITY_GAS,
    SOURCE_PRIORITY_ELECTRIC,
    SOURCE_PRIORITY_AUTO,
    SOURCE_PRIORITY_HYBRID,
    SOURCE_PRIORITY_COMBINED,
    SOURCE_PRIORITY_GAS_ONLY,
    SOURCE_PRIORITY_ELECTRIC_ONLY,
    DEFAULT_HEAT_SOURCE_PRIORITY,
)

_LOGGER = logging.getLogger(__name__)

# Minimum interval between identical commands to prevent Zigbee/IR transmitter spam
COMMAND_MIN_INTERVAL_SEC = 5.0
TEMPERATURE_DEADBAND = 0.4
BOOST_EXIT_HYSTERESIS = 0.3


class SplitZoneManager:
    """Manages secondary Room Split Climate Actuators for all configured zones."""

    def __init__(self, hass: HomeAssistant, coordinator: Any) -> None:
        """Initialize the Split Zone Manager."""
        self.hass = hass
        self.coordinator = coordinator
        self.zones = getattr(coordinator, "zones", []) or []

        self._splits: dict[str, dict[str, Any]] = {}
        self._quick_boost_states: dict[str, bool] = {}
        self._split_active_states: dict[str, bool] = {}
        self._last_split_commands: dict[str, dict[str, Any]] = {}
        self._last_command_timestamps: dict[str, float] = {}
        self._solar_run_start_timestamps: dict[str, float] = {}
        self._local_split_manual_on: dict[str, bool] = {}

        self._setup_zones()

    def _setup_zones(self) -> None:
        """Discover and index zones with configured split climate units."""
        for zone in self.zones:
            name = zone.get(CONF_ZONE_NAME)
            if not name:
                continue
            climate_id = make_zone_entity_id(name)
            split_entity = zone.get(CONF_ZONE_SPLIT_CLIMATE)
            if split_entity and str(split_entity).lower() != "none":
                if split_entity == climate_id:
                    _LOGGER.warning("Split entity '%s' matches zone entity ID, ignoring to prevent recursion", split_entity)
                    continue
                self._splits[climate_id] = {
                    "split_entity_id": split_entity,
                    "split_role": zone.get(CONF_ZONE_SPLIT_ROLE, DEFAULT_SPLIT_ROLE),
                    "split_solar_priority": zone.get(CONF_ZONE_SPLIT_SOLAR_PRIORITY, DEFAULT_SPLIT_SOLAR_PRIORITY),
                    "split_quick_boost": zone.get(CONF_ZONE_SPLIT_QUICK_BOOST, DEFAULT_SPLIT_QUICK_BOOST),
                    "split_boost_delta": float(zone.get(CONF_ZONE_SPLIT_BOOST_DELTA, DEFAULT_SPLIT_BOOST_DELTA)),
                    "split_sensor_injection": zone.get(CONF_ZONE_SPLIT_SENSOR_INJECTION, DEFAULT_SPLIT_SENSOR_INJECTION),
                }
                self._quick_boost_states[climate_id] = False
                self._split_active_states[climate_id] = False
                _LOGGER.info(
                    "Split Zone registered for '%s': entity=%s, role=%s, boost=%s, solar=%s",
                    climate_id,
                    split_entity,
                    self._splits[climate_id]["split_role"],
                    self._splits[climate_id]["split_quick_boost"],
                    self._splits[climate_id]["split_solar_priority"],
                )

    def register_zone(self, zone: dict[str, Any]) -> None:
        """Register a single zone split unit."""
        name = zone.get(CONF_ZONE_NAME)
        if not name:
            return
        climate_id = make_zone_entity_id(name)
        split_entity = zone.get(CONF_ZONE_SPLIT_CLIMATE)
        if split_entity and str(split_entity).lower() != "none":
            if split_entity == climate_id:
                _LOGGER.warning("Split entity '%s' matches zone entity ID, ignoring to prevent recursion", split_entity)
                return
            self._splits[climate_id] = {
                "split_entity_id": split_entity,
                "split_role": zone.get(CONF_ZONE_SPLIT_ROLE, DEFAULT_SPLIT_ROLE),
                "split_solar_priority": zone.get(CONF_ZONE_SPLIT_SOLAR_PRIORITY, DEFAULT_SPLIT_SOLAR_PRIORITY),
                "split_quick_boost": zone.get(CONF_ZONE_SPLIT_QUICK_BOOST, DEFAULT_SPLIT_QUICK_BOOST),
                "split_boost_delta": float(zone.get(CONF_ZONE_SPLIT_BOOST_DELTA, DEFAULT_SPLIT_BOOST_DELTA)),
                "split_sensor_injection": zone.get(CONF_ZONE_SPLIT_SENSOR_INJECTION, DEFAULT_SPLIT_SENSOR_INJECTION),
            }
            self._quick_boost_states[climate_id] = False
            self._split_active_states[climate_id] = False

    def is_local_manual_on(self, climate_id: str) -> bool:
        """Return True if zone split has been manually forced ON locally."""
        return self._local_split_manual_on.get(climate_id, False)

    def set_local_manual_on(self, climate_id: str, state: bool) -> None:
        """Set local manual override for split (only runs local split, never boiler)."""
        split_conf = self._splits.get(climate_id)
        if split_conf and split_conf.get("split_entity_id") == climate_id:
            _LOGGER.warning("Ignoring manual split override: split_entity matches zone_id '%s'", climate_id)
            return

        self._local_split_manual_on[climate_id] = bool(state)
        self._split_active_states[climate_id] = bool(state)
        if not state:
            # When manually turned off, turn off split immediately
            if split_conf:
                split_entity = split_conf["split_entity_id"]
                self.hass.async_create_task(
                    self.hass.services.async_call(
                        "climate",
                        "set_hvac_mode",
                        {"entity_id": split_entity, "hvac_mode": HVAC_MODE_OFF},
                        blocking=False,
                    )
                )

    def reset_all_local_manual_overrides(self) -> None:
        """Reset all local manual split overrides when master heating is activated."""
        if self._local_split_manual_on:
            _LOGGER.info("Master switch activated: resetting all localized split overrides to auto.")
            self._local_split_manual_on.clear()

    def has_split(self, climate_id: str) -> bool:
        """Return True if zone has an associated split AC entity."""
        return climate_id in self._splits

    def get_split_info(self, climate_id: str) -> dict[str, Any] | None:
        """Get configuration details for a zone split."""
        return self._splits.get(climate_id)

    def is_quick_boost_active(self, climate_id: str) -> bool:
        """Return True if Quick Heat Boost is currently engaged for this zone."""
        return self._quick_boost_states.get(climate_id, False)

    def is_split_active(self, climate_id: str) -> bool:
        """Return True if split unit is currently running (heating or cooling)."""
        return self._split_active_states.get(climate_id, False)

    def is_split_heating_allowed(self) -> bool:
        """Check runtime master permission for split heating."""
        if hasattr(self.coordinator, "get_persistent_data"):
            val = self.coordinator.get_persistent_data(KEY_ALLOW_SPLIT_HEATING, True)
            if val is not None:
                return bool(val)
        return True

    def is_split_cooling_allowed(self) -> bool:
        """Check runtime master permission for split cooling."""
        if hasattr(self.coordinator, "get_persistent_data"):
            val = self.coordinator.get_persistent_data(KEY_ALLOW_SPLIT_COOLING, True)
            if val is not None:
                return bool(val)
        return True

    def should_suppress_hydronic_demand(self, climate_id: str) -> bool:
        """Return True if hydronic heating (radiators/gas boiler) should be decoupled and zeroed out.

        Logic: When the split is actively covering the thermal load (via Solar Priority
        surplus or Electric Priority), the radiator valve is closed and boiler demand is 0%.
        EXCEPTION: During Quick Boost, both split and radiators run simultaneously for maximum speed.
        """
        if not self.has_split(climate_id):
            return False

        # If master switch is OFF or local manual override is active, strictly decouple hydronics
        master_on = (
            self.coordinator.get_master_state()
            if hasattr(self.coordinator, "get_master_state")
            else True
        )
        if not master_on or self.is_local_manual_on(climate_id):
            return True

        if not self.is_split_active(climate_id):
            return False

        # If Quick Boost is active, we WANT dual-heat boost (do not suppress radiators)
        if self.is_quick_boost_active(climate_id):
            return False

        heat_priority = (
            self.coordinator.get_persistent_data(KEY_HEAT_SOURCE_PRIORITY, DEFAULT_HEAT_SOURCE_PRIORITY)
            if hasattr(self.coordinator, "get_persistent_data")
            else DEFAULT_HEAT_SOURCE_PRIORITY
        )
        # In COMBINED mode, both sources heat together simultaneously (do not suppress hydronics)
        if heat_priority == SOURCE_PRIORITY_COMBINED:
            return False

        # In HYBRID, solar surplus or electric modes, decouple hydronics to save gas
        return True

    def calculate_injected_target(
        self, climate_id: str, current_temp: float, target_temp: float
    ) -> float:
        """Calculate compensated target temperature for the split.

        Overcomes the ceiling effect (where high ceiling probe reads hot air prematurely
        and ramps down the inverter before the living zone reaches target).
        """
        split_conf = self._splits.get(climate_id)
        if not split_conf or not split_conf.get("split_sensor_injection", True):
            return target_temp

        split_entity = split_conf["split_entity_id"]
        ceiling_temp = None

        if hasattr(self.hass, "states") and self.hass.states:
            s_state = self.hass.states.get(split_entity)
            if s_state and s_state.attributes:
                c_temp = s_state.attributes.get("current_temperature")
                if c_temp is not None:
                    try:
                        ceiling_temp = float(c_temp)
                    except (ValueError, TypeError):
                        pass

        if ceiling_temp is not None and ceiling_temp > current_temp:
            # Ceiling is reading hotter than floor/room sensor: inject offset
            probe_offset = ceiling_temp - current_temp
            injected = target_temp + probe_offset
            _LOGGER.debug(
                "[%s] Sensor Injection: Room=%.1f°C, SplitCeiling=%.1f°C -> Offset=+%.1f°C, Target=%.1f°C",
                climate_id,
                current_temp,
                ceiling_temp,
                probe_offset,
                injected,
            )
        elif current_temp < target_temp:
            # Room is still cold: give a +1.5°C push to ensure machine modulates actively
            injected = target_temp + 1.5
        else:
            injected = target_temp

        # Clamp between standard residential heat pump bounds
        return min(30.0, max(16.0, round(injected, 1)))

    def evaluate_split_state(
        self,
        climate_id: str,
        current_temp: float,
        target_temp: float,
        zone_hvac_mode: str,
        solar_surplus: bool = False,
    ) -> tuple[str, float | None, bool]:
        """Evaluate whether the split should be ON (HEAT/COOL) or OFF, and determine target setpoint.

        Returns (desired_mode, desired_target, is_heating_active).
        """
        if not self.has_split(climate_id):
            return (HVAC_MODE_OFF, None, False)

        split_conf = self._splits[climate_id]
        role = split_conf.get("split_role", DEFAULT_SPLIT_ROLE)

        # Global safety & master checks
        master_on = (
            self.coordinator.get_master_state()
            if hasattr(self.coordinator, "get_master_state")
            else True
        )
        zone_mode = (
            self.coordinator.zone_manager.get_zone_mode(climate_id)
            if hasattr(self.coordinator, "zone_manager")
            else "primary"
        )

        is_local_manual = self._local_split_manual_on.get(climate_id, False)

        if zone_mode == ZONE_MODE_BYPASS:
            self._quick_boost_states[climate_id] = False
            self._split_active_states[climate_id] = False
            return (HVAC_MODE_OFF, None, False)

        # Anti-seize safety: do not run splits during hydronic valve anti-seize
        anti_seize = getattr(self.coordinator, "anti_seize_manager", None)
        if anti_seize and getattr(anti_seize, "is_running", False) is True:
            self._quick_boost_states[climate_id] = False
            self._split_active_states[climate_id] = False
            return (HVAC_MODE_OFF, None, False)

        # If not master_on and NOT local manual forced on, split stays OFF
        if not master_on and not is_local_manual:
            self._quick_boost_states[climate_id] = False
            self._split_active_states[climate_id] = False
            return (HVAC_MODE_OFF, None, False)

        # Summer / Cooling Mode Evaluation
        if zone_hvac_mode == HVAC_MODE_COOL:
            self._quick_boost_states[climate_id] = False
            if role == SPLIT_ROLE_HEATING_ONLY or not self.is_split_cooling_allowed():
                self._solar_run_start_timestamps.pop(climate_id, None)
                self._split_active_states[climate_id] = False
                return (HVAC_MODE_OFF, None, False)

            solar_priority = split_conf.get("split_solar_priority", DEFAULT_SPLIT_SOLAR_PRIORITY)
            is_solar_call = (
                solar_surplus
                and (role == SPLIT_ROLE_COOLING_ONLY or role == SPLIT_ROLE_HEAT_COOL)
                and solar_priority
                and self.is_split_cooling_allowed()
            )

            energy_mgr = getattr(self.coordinator, "energy_manager", None)
            overheat_offset = 0.0
            min_run_sec = 0.0
            if energy_mgr is not None:
                raw_off = getattr(energy_mgr, "solar_overheat_offset", 0.0)
                if isinstance(raw_off, (int, float)) and not isinstance(raw_off, bool):
                    overheat_offset = max(0.0, float(raw_off))
                raw_min = getattr(energy_mgr, "solar_min_run_time", 0.0)
                if isinstance(raw_min, (int, float)) and not isinstance(raw_min, bool):
                    min_run_sec = max(0.0, float(raw_min) * 60.0)

            now_mono = time.monotonic()
            if is_solar_call:
                if climate_id not in self._solar_run_start_timestamps:
                    self._solar_run_start_timestamps[climate_id] = now_mono
            elif climate_id in self._solar_run_start_timestamps:
                elapsed_solar = now_mono - self._solar_run_start_timestamps[climate_id]
                if solar_priority and min_run_sec > 0.0 and elapsed_solar < min_run_sec:
                    is_solar_call = True
                    _LOGGER.debug(
                        "[%s] Cooling Solar Anti-Chatter Hold active (%.0fs / %.0fs elapsed)",
                        climate_id,
                        elapsed_solar,
                        min_run_sec,
                    )
                else:
                    self._solar_run_start_timestamps.pop(climate_id, None)

            was_active = self._split_active_states.get(climate_id, False)

            effective_target = (
                max(18.0, round(target_temp - overheat_offset, 1))
                if is_solar_call
                else target_temp
            )

            # In cooling mode, cooling is governed by room demand, local manual button, or solar call
            delta_t_cool = current_temp - effective_target  # positive if room is hot
            has_solar_cool = is_solar_call and ((delta_t_cool > 0.0) if was_active else (delta_t_cool > 0.05))
            should_cool = is_local_manual or has_solar_cool or ((delta_t_cool > 0.0) if was_active else (delta_t_cool > 0.3))

            if should_cool:
                self._split_active_states[climate_id] = True
                return (HVAC_MODE_COOL, effective_target, False)
            else:
                self._solar_run_start_timestamps.pop(climate_id, None)
                self._split_active_states[climate_id] = False
                return (HVAC_MODE_OFF, target_temp, False)

        # Winter / Heating Mode Evaluation
        if not self.is_split_heating_allowed():
            self._quick_boost_states[climate_id] = False
            self._split_active_states[climate_id] = False
            return (HVAC_MODE_OFF, None, False)

        if role == SPLIT_ROLE_COOLING_ONLY:
            self._quick_boost_states[climate_id] = False
            self._split_active_states[climate_id] = False
            return (HVAC_MODE_OFF, None, False)

        # Evaluate Quick Heat Boost
        delta_t = target_temp - current_temp
        boost_threshold = split_conf.get("split_boost_delta", DEFAULT_SPLIT_BOOST_DELTA)
        allow_boost = split_conf.get("split_quick_boost", False)

        if allow_boost:
            if delta_t >= boost_threshold:
                if not self._quick_boost_states.get(climate_id, False):
                    _LOGGER.info(
                        "[%s] Quick Heat Boost ENGAGED: Delta-T=%.1f°C >= Threshold=%.1f°C",
                        climate_id,
                        delta_t,
                        boost_threshold,
                    )
                self._quick_boost_states[climate_id] = True
            elif delta_t <= BOOST_EXIT_HYSTERESIS:
                if self._quick_boost_states.get(climate_id, False):
                    _LOGGER.info(
                        "[%s] Quick Heat Boost DISENGAGED: Room close to comfort (Delta-T=%.1f°C)",
                        climate_id,
                        delta_t,
                    )
                self._quick_boost_states[climate_id] = False
        else:
            self._quick_boost_states[climate_id] = False

        is_boost = self._quick_boost_states.get(climate_id, False)

        # Evaluate Solar Priority & Electric Source Priority
        allow_solar = split_conf.get("split_solar_priority", DEFAULT_SPLIT_SOLAR_PRIORITY)
        heat_priority = (
            self.coordinator.get_persistent_data(KEY_HEAT_SOURCE_PRIORITY, DEFAULT_HEAT_SOURCE_PRIORITY)
            if hasattr(self.coordinator, "get_persistent_data")
            else DEFAULT_HEAT_SOURCE_PRIORITY
        )
        is_electric_forced = heat_priority in (
            SOURCE_PRIORITY_ELECTRIC,
            SOURCE_PRIORITY_ELECTRIC_ONLY,
        )
        is_gas_only = heat_priority == SOURCE_PRIORITY_GAS_ONLY

        energy_mgr = getattr(self.coordinator, "energy_manager", None)
        overheat_offset = 0.0
        min_run_sec = 0.0
        if energy_mgr is not None:
            raw_off = getattr(energy_mgr, "solar_overheat_offset", 0.0)
            if isinstance(raw_off, (int, float)) and not isinstance(raw_off, bool):
                overheat_offset = max(0.0, float(raw_off))
            raw_min = getattr(energy_mgr, "solar_min_run_time", 0.0)
            if isinstance(raw_min, (int, float)) and not isinstance(raw_min, bool):
                min_run_sec = max(0.0, float(raw_min) * 60.0)

        now_mono = time.monotonic()
        is_solar_call = solar_surplus and allow_solar
        if is_solar_call:
            if climate_id not in self._solar_run_start_timestamps:
                self._solar_run_start_timestamps[climate_id] = now_mono
        elif climate_id in self._solar_run_start_timestamps:
            elapsed_solar = now_mono - self._solar_run_start_timestamps[climate_id]
            if allow_solar and min_run_sec > 0.0 and elapsed_solar < min_run_sec:
                is_solar_call = True
                _LOGGER.debug(
                    "[%s] Solar Anti-Chatter Hold active (%.0fs / %.0fs elapsed)",
                    climate_id,
                    elapsed_solar,
                    min_run_sec,
                )
            else:
                self._solar_run_start_timestamps.pop(climate_id, None)

        effective_target_temp = target_temp + overheat_offset if is_solar_call else target_temp
        effective_delta_t = effective_target_temp - current_temp
        should_heat = is_local_manual or (not is_gas_only and (is_boost or is_solar_call or is_electric_forced) and (effective_delta_t > 0.05))

        if should_heat:
            injected_target = self.calculate_injected_target(climate_id, current_temp, effective_target_temp)
            self._split_active_states[climate_id] = True
            return (HVAC_MODE_HEAT, injected_target, True)
        else:
            self._solar_run_start_timestamps.pop(climate_id, None)
            self._split_active_states[climate_id] = False
            return (HVAC_MODE_OFF, target_temp, False)

    async def async_sync_split(
        self, climate_id: str, desired_mode: str, desired_target: float | None
    ) -> None:
        """Send command to physical split climate entity with de-duplication and anti-spam."""
        split_conf = self._splits.get(climate_id)
        if not split_conf:
            return

        split_entity = split_conf["split_entity_id"]
        last_cmd = self._last_split_commands.get(climate_id, {})
        now = time.monotonic()
        last_ts = self._last_command_timestamps.get(climate_id, 0.0)

        # De-duplicate: check if identical command was sent recently
        mode_changed = last_cmd.get("mode") != desired_mode
        temp_changed = False
        if desired_target is not None:
            last_target = last_cmd.get("target")
            if last_target is None or abs(desired_target - last_target) >= TEMPERATURE_DEADBAND:
                temp_changed = True

        if not mode_changed and not temp_changed:
            return

        if not mode_changed and (now - last_ts) < COMMAND_MIN_INTERVAL_SEC:
            _LOGGER.debug(
                "[%s] Suppressing split command spam: %.1fs since last update",
                climate_id,
                now - last_ts,
            )
            return

        self._last_split_commands[climate_id] = {
            "mode": desired_mode,
            "target": desired_target,
        }
        self._last_command_timestamps[climate_id] = now

        try:
            if desired_mode == HVAC_MODE_OFF:
                _LOGGER.info("[%s] Setting split %s to OFF", climate_id, split_entity)
                await self.hass.services.async_call(
                    "climate",
                    "set_hvac_mode",
                    {ATTR_ENTITY_ID: split_entity, "hvac_mode": HVAC_MODE_OFF},
                    blocking=False,
                )
            else:
                _LOGGER.info(
                    "[%s] Setting split %s to %s with setpoint %.1f°C",
                    climate_id,
                    split_entity,
                    desired_mode,
                    desired_target or 21.0,
                )
                await self.hass.services.async_call(
                    "climate",
                    "set_hvac_mode",
                    {ATTR_ENTITY_ID: split_entity, "hvac_mode": desired_mode},
                    blocking=False,
                )
                if desired_target is not None:
                    await self.hass.services.async_call(
                        "climate",
                        "set_temperature",
                        {ATTR_ENTITY_ID: split_entity, ATTR_TEMPERATURE: desired_target},
                        blocking=False,
                    )
        except Exception as err:
            _LOGGER.warning("[%s] Failed to send command to split %s: %s", climate_id, split_entity, err)

    async def async_update_zone_split(
        self,
        climate_id: str,
        current_temp: float,
        target_temp: float,
        zone_hvac_mode: str,
        solar_surplus: bool = False,
    ) -> bool:
        """Evaluate and synchronously update the split entity for a single zone.

        Returns True if the split is actively heating, False otherwise.
        """
        mode, target, is_heating = self.evaluate_split_state(
            climate_id=climate_id,
            current_temp=current_temp,
            target_temp=target_temp,
            zone_hvac_mode=zone_hvac_mode,
            solar_surplus=solar_surplus,
        )
        await self.async_sync_split(climate_id, mode, target)
        return is_heating
