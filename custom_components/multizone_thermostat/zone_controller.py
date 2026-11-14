"""Zone Controller for Multizone Thermostat: orchestrates PID, autotuning, thermal model, and weather compensation."""
from __future__ import annotations

import inspect
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from datetime import timezone
import homeassistant.util.dt as dt_util
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from .const import (
    CONF_ZONE_NAME,
    CONF_ZONE_TEMP_SENSOR,
    make_zone_entity_id,
    HVAC_MODE_HEAT,
    ZONE_MODE_BYPASS,
    KEY_WEATHER_CURVE,
)
from .pid_wrapper import MultizonePID
from .autotune import PassiveAutotuneObserver
from .thermal_model import ThermalObserver

_LOGGER = logging.getLogger(__name__)


class ZoneController:
    """Orchestrates PID controllers, autotuning, and thermal models for all zones."""

    def __init__(self, hass: HomeAssistant, coordinator: Any) -> None:
        """Initialize the Zone Controller."""
        self.hass = hass
        self.coordinator = coordinator
        self.zones = coordinator.zones

        self._pids: dict[str, MultizonePID] = {}
        self._autotuners: dict[str, PassiveAutotuneObserver] = {}
        self._thermal_models: dict[str, ThermalObserver] = {}
        self._last_seen_temps: dict[str, float] = {}
        self._last_sensor_reports: dict[str, Any] = {}

        for zone in self.zones:
            name = zone.get(CONF_ZONE_NAME)
            if not name:
                continue
            climate_id = make_zone_entity_id(name)
            # Default Kp=100, Ki=0, Kd=0 (will be overridden by Autolearning later)
            self._pids[climate_id] = MultizonePID(
                kp=100.0, ki=0.0, kd=0.0, out_min=0.0, out_max=100.0, sensor_timeout=7200.0, zone_id=climate_id
            )
            self._autotuners[climate_id] = PassiveAutotuneObserver(climate_id, required_cycles=3)
            self._thermal_models[climate_id] = ThermalObserver(climate_id)

        self._was_dhw_active: bool = False

    @property
    def pids(self) -> dict[str, MultizonePID]:
        """Return dict of zone PIDs."""
        return self._pids

    @property
    def autotuners(self) -> dict[str, PassiveAutotuneObserver]:
        """Return dict of zone autotuners."""
        return self._autotuners

    @property
    def thermal_models(self) -> dict[str, ThermalObserver]:
        """Return dict of zone thermal models."""
        return self._thermal_models

    def _resolve_zone_id(self, climate_id: str) -> str:
        """Resolve an entity ID alias to the canonical zone ID used internally."""
        if climate_id in self._pids:
            return climate_id
        resolver = getattr(self.coordinator, "resolve_zone_id", None)
        if callable(resolver):
            resolved = resolver(climate_id)
            if isinstance(resolved, str) and resolved in self._pids:
                return resolved
        return climate_id

    def get_pid(self, climate_id: str) -> MultizonePID | None:
        """Get PID controller for a zone."""
        return self._pids.get(self._resolve_zone_id(climate_id))

    def get_autotuner(self, climate_id: str) -> PassiveAutotuneObserver | None:
        """Get autotuner for a zone."""
        return self._autotuners.get(self._resolve_zone_id(climate_id))

    def get_thermal_model(self, climate_id: str) -> ThermalObserver | None:
        """Get thermal model for a zone."""
        return self._thermal_models.get(self._resolve_zone_id(climate_id))

    def _apply_tuner_pid_to_controller(self, climate_id: str) -> None:
        """Push effective autotuner/manual PID gains to the active MultizonePID."""
        tuner = self._autotuners.get(climate_id)
        pid = self._pids.get(climate_id)
        if not tuner or not pid:
            return
        completed = tuner.state == tuner.STATE_COMPLETED
        overrides = getattr(tuner, "manual_overrides", {}) or {}
        kp = tuner.kp if (completed or "Kp" in overrides) else 100.0
        ki = tuner.ki if (completed or "Ki" in overrides) else 0.0
        kd = tuner.kd if (completed or "Kd" in overrides) else 0.0
        pid.set_pid_param(kp=kp, ki=ki, kd=kd)

    async def async_set_zone_pid(
        self,
        climate_id: str,
        kp: float | None = None,
        ki: float | None = None,
        kd: float | None = None,
        lock_param: str | None = None,
    ) -> bool:
        """Update manual PID overrides or restore parameters to autotuner control."""
        resolved_id = self._resolve_zone_id(climate_id)
        tuner = self._autotuners.get(resolved_id)
        if not tuner:
            return False
        if lock_param is not None:
            tuner.lock_param(None if str(lock_param).lower() == "all" else str(lock_param))
        tuner.set_manual_pid(kp=kp, ki=ki, kd=kd)
        self._apply_tuner_pid_to_controller(resolved_id)
        await self.async_save_autotuner_states()
        return True

    async def async_reset_zone_autotuner(
        self,
        climate_id: str,
        keep_manual_overrides: bool = False,
    ) -> bool:
        """Reset autotuner cycles and learned PID parameters for a zone."""
        resolved_id = self._resolve_zone_id(climate_id)
        tuner = self._autotuners.get(resolved_id)
        pid = self._pids.get(resolved_id)
        if not tuner:
            return False
        tuner.reset(keep_manual_overrides=keep_manual_overrides)
        self._apply_tuner_pid_to_controller(resolved_id)
        if pid:
            pid.clear_samples()
        await self.async_save_autotuner_states()
        return True

    def load_state(self, autotune_data: dict[str, Any], thermal_data: dict[str, Any]) -> None:
        """Restore autotuner and thermal model states from persistent storage."""
        if autotune_data:
            for climate_id, tuner in self._autotuners.items():
                if climate_id in autotune_data:
                    tuner.load_state(autotune_data[climate_id])
                    overrides = getattr(tuner, "manual_overrides", {}) or {}
                    if tuner.state == tuner.STATE_COMPLETED or overrides:
                        self._apply_tuner_pid_to_controller(climate_id)
                        _LOGGER.info(
                            "Restored Smart PID for %s: Kp=%.1f, Ki=%.4f, Kd=%.1f",
                            climate_id, tuner.kp, tuner.ki, tuner.kd,
                        )

        if thermal_data:
            for climate_id, model in self._thermal_models.items():
                if climate_id in thermal_data:
                    model.load_state(thermal_data[climate_id])
                    _LOGGER.info(
                        "Restored Thermal Model for %s: Heating=%.2f, Cooling=%.2f, Inertia=%.2f",
                        climate_id, model.heating_rate, model.cooling_rate, model.thermal_inertia,
                    )

    async def async_save_autotuner_states(self) -> None:
        """Save autotuner learning progress to storage."""
        if hasattr(self.coordinator, "storage"):
            await self.coordinator.storage.async_save_autotuner_states(self._autotuners)

    async def async_save_thermal_states(self) -> None:
        """Save thermal model learning progress to storage."""
        if hasattr(self.coordinator, "storage"):
            await self.coordinator.storage.async_save_thermal_states(self._thermal_models)

    async def async_update_zone(self, entity_id: str, new_state: Any) -> float:
        """Calculate and update PID demand, autotuner and thermal model for a zone."""
        entity_id = self._resolve_zone_id(entity_id)
        current_temp = new_state.attributes.get("current_temperature")
        target_temp = new_state.attributes.get("temperature")

        if current_temp is None or target_temp is None:
            self.coordinator.demand_aggregator.set_zone_demand(entity_id, 0.0)
            return 0.0

        try:
            current_temp = float(current_temp)
            target_temp = float(target_temp)
        except (ValueError, TypeError):
            self.coordinator.demand_aggregator.set_zone_demand(entity_id, 0.0)
            return 0.0

        if entity_id not in self._thermal_models or entity_id not in self._autotuners or entity_id not in self._pids:
            _LOGGER.warning(
                "Unknown zone entity '%s' not registered in thermal models, autotuners, or PIDs. Unable to calculate demand.",
                entity_id,
            )
            return 0.0

        # Update PID sensor timestamp when a new or fresh reading arrives
        sensor_fresh = False
        if self._last_seen_temps.get(entity_id) != current_temp:
            self._last_seen_temps[entity_id] = current_temp
            sensor_fresh = True
        else:
            # Numeric temperature unchanged: check actual report freshness
            zone_conf = next(
                (z for z in self.zones if (z.get("climate_id") == entity_id or make_zone_entity_id(z.get(CONF_ZONE_NAME, "")) == entity_id)),
                None,
            )
            sensor_id = zone_conf.get(CONF_ZONE_TEMP_SENSOR) if zone_conf else None
            climate_ent = getattr(self.coordinator, "_climate_entities", {}).get(entity_id)
            if climate_ent and getattr(climate_ent, "_safety_fallback_active", False):
                sensor_fresh = True
            elif sensor_id and sensor_id != "none" and hasattr(self.hass, "states") and self.hass.states:
                s_state = self.hass.states.get(sensor_id)
                if s_state and s_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN, "unavailable", "unknown"):
                    reported = getattr(s_state, "last_reported", None) or getattr(s_state, "last_updated", None)
                    if reported is not None:
                        if self._last_sensor_reports.get(entity_id) != reported:
                            self._last_sensor_reports[entity_id] = reported
                            sensor_fresh = True
                        else:
                            try:
                                now_dt = dt_util.utcnow()
                                rep_utc = reported if reported.tzinfo else reported.replace(tzinfo=timezone.utc)
                                if (now_dt - rep_utc).total_seconds() < 7200:
                                    sensor_fresh = True
                            except Exception:
                                pass
            else:
                reported = getattr(new_state, "last_reported", None) or getattr(new_state, "last_updated", None)
                if reported is not None and self._last_sensor_reports.get(entity_id) != reported:
                    self._last_sensor_reports[entity_id] = reported
                    sensor_fresh = True

        if sensor_fresh:
            self._pids[entity_id].update_sensor_timestamp()

        # Check mode (don't calculate if off/bypass)
        hvac_mode = new_state.state
        zone_mode = self.coordinator.zone_manager.get_zone_mode(entity_id)

        if hvac_mode == HVAC_MODE_HEAT and zone_mode != ZONE_MODE_BYPASS:
            is_faulty = (
                self.coordinator.plant_diagnostics.has_critical_sensor_fault(entity_id)
                if hasattr(self.coordinator, "plant_diagnostics")
                else False
            )
            if is_faulty:
                demand = 0.0
                _LOGGER.warning(
                    "Zone %s: Heating demand forced to 0%% due to critical sensor fault/low battery",
                    entity_id,
                )
                self.coordinator.demand_aggregator.set_zone_demand(entity_id, demand)
                return 0.0

            is_dhw = bool(getattr(self.coordinator, "is_dhw_active", False))
            if self._was_dhw_active and not is_dhw:
                _LOGGER.info(
                    "Domestic Hot Water (DHW) production ended: resetting PID integrals, dt and timestamps for all zones."
                )
                for p in self._pids.values():
                    p.clear_samples()
            self._was_dhw_active = is_dhw

            if is_dhw:
                _LOGGER.debug(
                    "Zone %s: PID frozen, boiler is currently producing Domestic Hot Water (DHW Active).",
                    entity_id,
                )
                if entity_id in self._pids:
                    self._pids[entity_id].clear_samples()
                return self.coordinator.demand_aggregator.get_zone_demand(entity_id)

            # Smart Stop: Calculate Effective Target based on learned Inertia
            thermal_model = self._thermal_models[entity_id]
            effective_target = target_temp
            if thermal_model.thermal_inertia > 0.05:
                effective_target = target_temp - thermal_model.thermal_inertia
                # Limit to avoid lowering it too much if inertia is crazy high
                effective_target = max(target_temp - 1.0, effective_target)

            tuner = self._autotuners[entity_id]

            if tuner.state != tuner.STATE_COMPLETED:
                # Hysteresis Fallback Mode (Learning phase)
                tolerance = 0.3
                current_demand = self.coordinator.demand_aggregator.get_zone_demand(entity_id)
                if current_temp <= effective_target - tolerance:
                    demand = 100.0
                elif current_temp >= effective_target + tolerance:
                    demand = 0.0
                else:
                    demand = current_demand  # Keep previous demand inside the hysteresis band
            else:
                # Smart PID Mode
                demand = self._pids[entity_id].calc(current_temp, effective_target)

                # Apply Weather Compensation (Feed Forward)
                try:
                    curve_val = float(self.coordinator.get_persistent_data(KEY_WEATHER_CURVE, 0.0) or 0.0)
                except (ValueError, TypeError):
                    curve_val = 0.0
                if self.coordinator.weather_sensor_id:
                    weather_state = self.hass.states.get(self.coordinator.weather_sensor_id)
                    if weather_state and weather_state.state not in ("unavailable", "unknown"):
                        try:
                            outdoor_temp = None
                            is_weather_domain = (
                                str(self.coordinator.weather_sensor_id).startswith("weather.")
                                or getattr(weather_state, "entity_id", "").startswith("weather.")
                            )
                            if is_weather_domain:
                                temp_attr = weather_state.attributes.get("temperature") if getattr(weather_state, "attributes", None) else None
                                if temp_attr is not None:
                                    outdoor_temp = float(temp_attr)
                            else:
                                outdoor_temp = float(weather_state.state)

                            if outdoor_temp is not None:
                                # Adaptive Curve Calculation (SAT Math)
                                curve_val = thermal_model.get_weather_multiplier(manual_base_curve=curve_val)

                                # (Target - OutdoorTemp) * Ke
                                delta_t = effective_target - outdoor_temp
                                if delta_t > 0.0 and curve_val > 0.0:
                                    ff_demand = delta_t * curve_val
                                    # Clamp the weather bonus to a max of +40% to avoid it dominating the PID
                                    ff_demand = min(40.0, ff_demand)
                                    
                                    # Scale down FF as we approach or exceed effective_target to prevent ghost heating
                                    overheat = current_temp - effective_target
                                    if overheat >= 0:
                                        ff_demand = 0.0
                                    elif overheat > -0.5:
                                        ff_factor = max(0.0, -overheat / 0.5)
                                        ff_demand *= ff_factor
                                        
                                    demand = min(100.0, max(0.0, demand + ff_demand))
                                    _LOGGER.debug(
                                        "[%s] SAT Weather Comp: Target=%.1f, Outdoor=%.1f, Ke=%.2f, FF=+%.1f%%, Final=%.1f%%",
                                        entity_id,
                                        effective_target,
                                        outdoor_temp,
                                        curve_val,
                                        ff_demand,
                                        demand,
                                    )
                        except (ValueError, TypeError):
                            pass
        else:
            demand = 0.0

        self.coordinator.demand_aggregator.set_zone_demand(entity_id, demand)

        tuner = self._autotuners[entity_id]
        thermal_model = self._thermal_models[entity_id]
        was_completed = tuner.state == tuner.STATE_COMPLETED
        prev_cycles = len(tuner.completed_cycles)
        tuner_update_fn = tuner.update
        try:
            t_params = inspect.signature(tuner_update_fn).parameters
            if "demand" in t_params or any(
                p.kind == inspect.Parameter.VAR_KEYWORD for p in t_params.values()
            ):
                tuner_update_fn(
                    current_temp,
                    demand > 0,
                    demand=demand,
                    cooling_rate=thermal_model.cooling_rate,
                )
            else:
                tuner_update_fn(current_temp, demand > 0)
        except (ValueError, TypeError):
            tuner_update_fn(current_temp, demand > 0)
        just_completed = not was_completed and tuner.state == tuner.STATE_COMPLETED
        if just_completed or getattr(tuner, "weekly_updated_last_tick", False):
            self._apply_tuner_pid_to_controller(entity_id)
            if callable(getattr(self.coordinator, "async_notify_pid_entities", None)):
                self.coordinator.async_notify_pid_entities()
            if just_completed:
                _LOGGER.info(
                    "Autotuning just completed for %s! Smart PID activated. Kp=%.1f, Ki=%.4f, Kd=%.1f",
                    entity_id,
                    tuner.kp,
                    tuner.ki,
                    tuner.kd,
                )
        if (
            len(tuner.completed_cycles) > prev_cycles
            or just_completed
            or getattr(tuner, "needs_save", False)
        ):
            if not just_completed and len(tuner.completed_cycles) > prev_cycles:
                _LOGGER.info(
                    "Autotuning cycle %d/%d recorded for %s. Saving progress.",
                    len(tuner.completed_cycles),
                    tuner.required_cycles,
                    entity_id,
                )
            await self.async_save_autotuner_states()

        # Feed Thermal Observer (with effective demand gating for heating_rate)
        model_update_fn = thermal_model.update
        try:
            m_params = inspect.signature(model_update_fn).parameters
            if "demand" in m_params or any(
                p.kind == inspect.Parameter.VAR_KEYWORD for p in m_params.values()
            ):
                model_update_fn(current_temp, demand > 0, demand=demand)
            else:
                model_update_fn(current_temp, demand > 0)
        except (ValueError, TypeError):
            model_update_fn(current_temp, demand > 0)
        # Debounced save: avoid writing to disk on every state change (SD card wear)
        if hasattr(self.coordinator, "storage"):
            self.coordinator.debounced_save_thermal_states(self._thermal_models)

        _LOGGER.debug(
            "Zone '%s' Demand updated: %.1f%% (Temp: %s, Target: %s, Mode: %s)",
            entity_id,
            demand,
            current_temp,
            target_temp,
            "PID" if tuner.state == tuner.STATE_COMPLETED else "Hysteresis",
        )
        return demand
