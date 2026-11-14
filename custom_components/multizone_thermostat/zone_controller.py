"""Zone Controller for Multizone Thermostat: orchestrates PID, autotuning, thermal model, and weather compensation."""
from __future__ import annotations

import logging
import inspect
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
    HVAC_MODE_COOL,
    ZONE_MODE_BYPASS,
    KEY_WEATHER_CURVE,
    SOURCE_PRIORITY_ELECTRIC_ONLY,
)
from .pid_wrapper import MultizonePID
from .autotune import PassiveAutotuneObserver
from .thermal_model import ThermalObserver

_LOGGER = logging.getLogger(__name__)


class ZoneController:
    """Orchestrates PID controllers, autotuning, and thermal models for all zones in heating and cooling modes."""

    def __init__(self, hass: HomeAssistant, coordinator: Any) -> None:
        """Initialize the Zone Controller."""
        self.hass = hass
        self.coordinator = coordinator
        self.zones = coordinator.zones

        # Dual-track PIDs and Autotuners for seasonal optimization (heat vs cool)
        self._pids_heat: dict[str, MultizonePID] = {}
        self._pids_cool: dict[str, MultizonePID] = {}
        self._autotuners_heat: dict[str, PassiveAutotuneObserver] = {}
        self._autotuners_cool: dict[str, PassiveAutotuneObserver] = {}

        self._thermal_models: dict[str, ThermalObserver] = {}
        self._last_seen_temps: dict[str, float] = {}
        self._last_sensor_reports: dict[str, Any] = {}

        for zone in self.zones:
            name = zone.get(CONF_ZONE_NAME)
            if not name:
                continue
            climate_id = make_zone_entity_id(name)
            # Heating PID & Autotuner
            self._pids_heat[climate_id] = MultizonePID(
                kp=100.0, ki=0.0, kd=0.0, out_min=0.0, out_max=100.0, sensor_timeout=7200.0, zone_id=climate_id, action="heat"
            )
            self._autotuners_heat[climate_id] = PassiveAutotuneObserver(climate_id, required_cycles=3, mode="heat")

            # Cooling PID & Autotuner
            self._pids_cool[climate_id] = MultizonePID(
                kp=100.0, ki=0.0, kd=0.0, out_min=0.0, out_max=100.0, sensor_timeout=7200.0, zone_id=climate_id, action="cool"
            )
            self._autotuners_cool[climate_id] = PassiveAutotuneObserver(climate_id, required_cycles=3, mode="cool")

            self._thermal_models[climate_id] = ThermalObserver(climate_id)

        # Backward compatibility aliases
        self._pids = self._pids_heat
        self._autotuners = self._autotuners_heat
        self._was_dhw_active: bool = False

    @property
    def pids(self) -> dict[str, MultizonePID]:
        """Return dict of zone heating PIDs (backward-compatible)."""
        return self._pids_heat

    @property
    def pids_cool(self) -> dict[str, MultizonePID]:
        """Return dict of zone cooling PIDs."""
        return self._pids_cool

    @property
    def autotuners(self) -> dict[str, PassiveAutotuneObserver]:
        """Return dict of zone heating autotuners (backward-compatible)."""
        return self._autotuners_heat

    @property
    def autotuners_cool(self) -> dict[str, PassiveAutotuneObserver]:
        """Return dict of zone cooling autotuners."""
        return self._autotuners_cool

    @property
    def thermal_models(self) -> dict[str, ThermalObserver]:
        """Return dict of zone thermal models."""
        return self._thermal_models

    def _resolve_zone_id(self, climate_id: str) -> str:
        """Resolve an entity ID alias to the canonical zone ID used internally."""
        if climate_id in self._pids_heat:
            return climate_id
        resolver = getattr(self.coordinator, "resolve_zone_id", None)
        if callable(resolver):
            resolved = resolver(climate_id)
            if isinstance(resolved, str) and resolved in self._pids_heat:
                return resolved
        return climate_id

    def get_pid(self, climate_id: str, mode: str = "heat") -> MultizonePID | None:
        """Get PID controller for a zone in specified mode."""
        resolved = self._resolve_zone_id(climate_id)
        if mode == "cool":
            return self._pids_cool.get(resolved)
        return self._pids_heat.get(resolved)

    def get_autotuner(self, climate_id: str, mode: str = "heat") -> PassiveAutotuneObserver | None:
        """Get autotuner for a zone in specified mode."""
        resolved = self._resolve_zone_id(climate_id)
        if mode == "cool":
            return self._autotuners_cool.get(resolved)
        return self._autotuners_heat.get(resolved)

    def get_thermal_model(self, climate_id: str) -> ThermalObserver | None:
        """Get thermal model for a zone."""
        return self._thermal_models.get(self._resolve_zone_id(climate_id))

    def _apply_tuner_pid_to_controller(self, climate_id: str, mode: str = "heat") -> None:
        """Push effective autotuner/manual PID gains to the active MultizonePID."""
        resolved_id = self._resolve_zone_id(climate_id)
        tuner = self._autotuners_cool.get(resolved_id) if mode == "cool" else self._autotuners_heat.get(resolved_id)
        pid = self._pids_cool.get(resolved_id) if mode == "cool" else self._pids_heat.get(resolved_id)
        if not tuner or not pid:
            return
        completed = tuner.state == tuner.STATE_COMPLETED
        overrides = getattr(tuner, "manual_overrides", {}) or {}
        default_kp = 100.0
        kp = tuner.kp if (completed or "Kp" in overrides) else default_kp
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
        mode: str | None = None,
    ) -> bool:
        """Update manual PID overrides or restore parameters to autotuner control."""
        resolved_id = self._resolve_zone_id(climate_id)
        track = mode or (
            "cool"
            if str(getattr(self.coordinator, "master_hvac_mode", "heat")).lower() == "cool"
            else "heat"
        )
        tuner = self._autotuners_cool.get(resolved_id) if track == "cool" else self._autotuners_heat.get(resolved_id)
        if not tuner:
            return False
        if lock_param is not None:
            tuner.lock_param(None if str(lock_param).lower() == "all" else str(lock_param))
        tuner.set_manual_pid(kp=kp, ki=ki, kd=kd)
        self._apply_tuner_pid_to_controller(resolved_id, mode=track)
        await self.async_save_autotuner_states()
        return True

    async def async_reset_zone_autotuner(
        self,
        climate_id: str,
        keep_manual_overrides: bool = False,
        mode: str | None = None,
    ) -> bool:
        """Reset autotuner cycles and learned PID parameters for a zone."""
        resolved_id = self._resolve_zone_id(climate_id)
        track = mode or (
            "cool"
            if str(getattr(self.coordinator, "master_hvac_mode", "heat")).lower() == "cool"
            else "heat"
        )
        tuner = self._autotuners_cool.get(resolved_id) if track == "cool" else self._autotuners_heat.get(resolved_id)
        pid = self._pids_cool.get(resolved_id) if track == "cool" else self._pids_heat.get(resolved_id)
        if not tuner:
            return False
        tuner.reset(keep_manual_overrides=keep_manual_overrides)
        self._apply_tuner_pid_to_controller(resolved_id, mode=track)
        if pid:
            pid.clear_samples()
        await self.async_save_autotuner_states()
        return True

    def load_state(self, autotune_data: dict[str, Any], thermal_data: dict[str, Any]) -> None:
        """Restore autotuner and thermal model states from persistent storage."""
        if autotune_data and isinstance(autotune_data, dict):
            # Check for dual-track seasonal format {"heat": {...}, "cool": {...}} vs legacy flat dict
            if "heat" in autotune_data or "cool" in autotune_data:
                heat_data = autotune_data.get("heat", {})
                cool_data = autotune_data.get("cool", {})
            else:
                heat_data = autotune_data
                cool_data = {}

            # Restore heating autotuners
            if isinstance(heat_data, dict):
                for climate_id, tuner in self._autotuners_heat.items():
                    if climate_id in heat_data:
                        tuner.load_state(heat_data[climate_id])
                        overrides = getattr(tuner, "manual_overrides", {}) or {}
                        if tuner.state == tuner.STATE_COMPLETED or overrides:
                            self._apply_tuner_pid_to_controller(climate_id, mode="heat")
                            _LOGGER.info(
                                "Restored Smart Heating PID for %s: Kp=%.1f, Ki=%.4f, Kd=%.1f",
                                climate_id, tuner.kp, tuner.ki, tuner.kd,
                            )

            # Restore cooling autotuners
            if isinstance(cool_data, dict):
                for climate_id, tuner in self._autotuners_cool.items():
                    if climate_id in cool_data:
                        tuner.load_state(cool_data[climate_id])
                        overrides = getattr(tuner, "manual_overrides", {}) or {}
                        if tuner.state == tuner.STATE_COMPLETED or overrides:
                            self._apply_tuner_pid_to_controller(climate_id, mode="cool")
                            _LOGGER.info(
                                "Restored Smart Cooling PID for %s: Kp=%.1f, Ki=%.4f, Kd=%.1f",
                                climate_id, tuner.kp, tuner.ki, tuner.kd,
                            )

        if thermal_data and isinstance(thermal_data, dict):
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
            await self.coordinator.storage.async_save_autotuner_states(self._autotuners_heat, self._autotuners_cool)

    async def async_save_thermal_states(self) -> None:
        """Save thermal model learning progress to storage."""
        if hasattr(self.coordinator, "storage"):
            await self.coordinator.storage.async_save_thermal_states(self._thermal_models)

    async def async_update_zone(self, entity_id: str, new_state: Any) -> float:
        """Calculate and update PID demand, autotuner and thermal model for a zone in HEAT or COOL mode."""
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

        if entity_id not in self._thermal_models or entity_id not in self._pids_heat:
            _LOGGER.warning(
                "Unknown zone entity '%s' not registered in thermal models or PIDs. Unable to calculate demand.",
                entity_id,
            )
            return 0.0

        # Update PID sensor timestamp when a new or fresh reading arrives
        sensor_fresh = False
        if self._last_seen_temps.get(entity_id) != current_temp:
            self._last_seen_temps[entity_id] = current_temp
            sensor_fresh = True
        else:
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
            self._pids_heat[entity_id].update_sensor_timestamp()
            self._pids_cool[entity_id].update_sensor_timestamp()

        # Check mode (don't calculate if off/bypass)
        hvac_mode = new_state.state
        zone_mode = self.coordinator.zone_manager.get_zone_mode(entity_id)

        demand = 0.0

        if zone_mode == ZONE_MODE_BYPASS or hvac_mode not in (HVAC_MODE_HEAT, HVAC_MODE_COOL):
            demand = 0.0
        elif hvac_mode == HVAC_MODE_HEAT:
            is_faulty = (
                self.coordinator.plant_diagnostics.has_critical_sensor_fault(entity_id)
                if hasattr(self.coordinator, "plant_diagnostics")
                else False
            )
            if is_faulty:
                _LOGGER.warning(
                    "Zone %s: Heating demand forced to 0%% due to critical sensor fault/low battery",
                    entity_id,
                )
                self.coordinator.demand_aggregator.set_zone_demand(entity_id, 0.0)
                return 0.0

            is_dhw = bool(getattr(self.coordinator, "is_dhw_active", False))
            if self._was_dhw_active and not is_dhw:
                _LOGGER.info(
                    "Domestic Hot Water (DHW) production ended: resetting PID integrals, dt and timestamps for all zones."
                )
                for p in self._pids_heat.values():
                    p.clear_samples()
            self._was_dhw_active = is_dhw

            if is_dhw:
                _LOGGER.debug(
                    "Zone %s: PID frozen, boiler is currently producing Domestic Hot Water (DHW Active).",
                    entity_id,
                )
                if entity_id in self._pids_heat:
                    self._pids_heat[entity_id].clear_samples()
                return self.coordinator.demand_aggregator.get_zone_demand(entity_id)

            # Smart Stop: Calculate Effective Target based on learned Inertia
            thermal_model = self._thermal_models[entity_id]
            target = target_temp
            c = self.coordinator
            is_solar_surplus = (
                getattr(c, "solar_surplus", False) is True
                or (
                    hasattr(c, "energy_manager")
                    and c.energy_manager is not None
                    and callable(getattr(c.energy_manager, "is_solar_surplus", None))
                    and getattr(c.energy_manager, "is_solar_surplus")() is True
                )
            )
            energy_mgmt = (
                getattr(c, "enable_energy_management", False) is True
                or getattr(c, "energy_management_enabled", False) is True
            )
            if is_solar_surplus and energy_mgmt:
                raw_offset = getattr(c, "solar_overheat_offset", None)
                if not isinstance(raw_offset, (int, float)) or isinstance(raw_offset, bool):
                    if hasattr(c, "energy_manager") and c.energy_manager is not None:
                        raw_offset = getattr(c.energy_manager, "solar_overheat_offset", None)
                solar_offset = (
                    float(raw_offset)
                    if isinstance(raw_offset, (int, float)) and not isinstance(raw_offset, bool)
                    else 0.0
                )
                if getattr(c, "enable_heat_pump", False) is True:
                    target += solar_offset

            effective_target = target
            if thermal_model.thermal_inertia > 0.05:
                effective_target = target - thermal_model.thermal_inertia
                effective_target = max(target - 1.0, effective_target)

            tuner = self._autotuners_heat[entity_id]

            if tuner.state != tuner.STATE_COMPLETED and not getattr(tuner, "manual_overrides", None):
                # Hysteresis Fallback Mode (Learning phase)
                tolerance = 0.3
                current_demand = self.coordinator.demand_aggregator.get_zone_demand(entity_id)
                if current_temp <= effective_target - tolerance:
                    demand = 100.0
                elif current_temp >= effective_target + tolerance:
                    demand = 0.0
                else:
                    demand = current_demand
            else:
                # Smart PID Mode
                demand = self._pids_heat[entity_id].calc(current_temp, effective_target)

                # Apply Weather Compensation (Feed Forward) ONLY for non-modulating plants (Relays)
                # For modulating plants (OpenTherm / Heat Pump), FlowCurve has exclusive ownership.
                if not (getattr(self.coordinator, "is_modulating_plant", False) is True):
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
                                    curve_val = thermal_model.get_weather_multiplier(manual_base_curve=curve_val)
                                    delta_t = effective_target - outdoor_temp
                                    if delta_t > 0.0 and curve_val > 0.0:
                                        ff_demand = delta_t * curve_val
                                        ff_demand = min(40.0, ff_demand)
                                        
                                        overheat = current_temp - effective_target
                                        if overheat >= 0:
                                            ff_demand = 0.0
                                        elif overheat > -0.5:
                                            ff_factor = max(0.0, -overheat / 0.5)
                                            ff_demand *= ff_factor
                                            
                                        demand = min(100.0, max(0.0, demand + ff_demand))
                            except (ValueError, TypeError):
                                pass

        elif hvac_mode == HVAC_MODE_COOL:
            is_faulty = (
                self.coordinator.plant_diagnostics.has_critical_sensor_fault(entity_id)
                if hasattr(self.coordinator, "plant_diagnostics")
                else False
            )
            if is_faulty:
                _LOGGER.warning(
                    "Zone %s: Cooling demand forced to 0%% due to critical sensor fault/low battery",
                    entity_id,
                )
                self.coordinator.demand_aggregator.set_zone_demand(entity_id, 0.0)
                return 0.0

            target = target_temp
            c = self.coordinator
            is_solar_surplus = (
                getattr(c, "solar_surplus", False) is True
                or (
                    hasattr(c, "energy_manager")
                    and c.energy_manager is not None
                    and callable(getattr(c.energy_manager, "is_solar_surplus", None))
                    and getattr(c.energy_manager, "is_solar_surplus")() is True
                )
            )
            energy_mgmt = (
                getattr(c, "enable_energy_management", False) is True
                or getattr(c, "energy_management_enabled", False) is True
            )
            if is_solar_surplus and energy_mgmt:
                raw_offset = getattr(c, "solar_overheat_offset", None)
                if not isinstance(raw_offset, (int, float)) or isinstance(raw_offset, bool):
                    if hasattr(c, "energy_manager") and c.energy_manager is not None:
                        raw_offset = getattr(c.energy_manager, "solar_overheat_offset", None)
                solar_offset = (
                    float(raw_offset)
                    if isinstance(raw_offset, (int, float)) and not isinstance(raw_offset, bool)
                    else 0.0
                )
                if (
                    getattr(c, "enable_heat_pump", False) is True
                    and getattr(c, "heat_pump_cooling", False) is True
                ):
                    target -= solar_offset

            effective_target = target
            tuner = self._autotuners_cool[entity_id]

            if tuner.state != tuner.STATE_COMPLETED and not getattr(tuner, "manual_overrides", None):
                # Hysteresis Cooling Fallback Mode (Learning phase)
                tolerance = 0.3
                current_demand = self.coordinator.demand_aggregator.get_zone_demand(entity_id)
                if current_temp >= effective_target + tolerance:
                    demand = 100.0
                elif current_temp <= effective_target - tolerance:
                    demand = 0.0
                else:
                    demand = current_demand
            else:
                # Smart PID Cooling Mode
                demand = self._pids_cool[entity_id].calc(current_temp, effective_target)

        # Evaluate and update secondary room split unit
        split_mgr = getattr(self.coordinator, 'split_manager', None)
        if split_mgr is not None and hasattr(split_mgr, 'has_split') and split_mgr.has_split(entity_id) is True:
            solar_surplus = False
            energy_mgr = getattr(self.coordinator, 'energy_manager', None)
            if energy_mgr is not None:
                surplus_fn = getattr(energy_mgr, 'is_solar_surplus', None)
                if callable(surplus_fn):
                    solar_surplus = bool(surplus_fn())
                elif surplus_fn is True:
                    solar_surplus = True
            
            update_fn = getattr(split_mgr, 'async_update_zone_split', None)
            if callable(update_fn):
                coro = update_fn(
                    climate_id=entity_id,
                    current_temp=current_temp,
                    target_temp=target_temp,
                    zone_hvac_mode=hvac_mode,
                    solar_surplus=solar_surplus,
                )
                if inspect.iscoroutine(coro):
                    await coro

            # Decouple hydronic demand if split is carrying the load in solar/electric mode
            if hasattr(split_mgr, 'should_suppress_hydronic_demand') and split_mgr.should_suppress_hydronic_demand(entity_id) is True:
                demand = 0.0
                _LOGGER.debug(
                    '[%s] Hydronic demand suppressed to 0.0%% (split is actively conditioning zone)',
                    entity_id,
                )

        # Electric Only priority: blocks hydronic demand only if NO central heat pump exists
        if hvac_mode == HVAC_MODE_HEAT:
            energy_mgr = getattr(self.coordinator, 'energy_manager', None)
            if energy_mgr is not None and getattr(energy_mgr, 'get_heat_source_priority', None):
                if energy_mgr.get_heat_source_priority() == SOURCE_PRIORITY_ELECTRIC_ONLY:
                    hp_enabled = bool(getattr(self.coordinator, "enable_heat_pump", False))
                    if not hp_enabled:
                        demand = 0.0
                        _LOGGER.debug(
                            '[%s] Hydronic boiler demand forced to 0.0%% (Heat source priority is electric_only and no central heat pump)',
                            entity_id,
                        )

        # Cooling validation: if no central Heat Pump with cooling enabled and no split, hydronic cooling demand is 0
        if hvac_mode == HVAC_MODE_COOL:
            hp_cooling = bool(
                getattr(self.coordinator, "enable_heat_pump", False)
                and getattr(self.coordinator, "heat_pump_cooling", True)
            )
            has_split = split_mgr and split_mgr.has_split(entity_id)
            if not hp_cooling and not has_split:
                demand = 0.0

        self.coordinator.demand_aggregator.set_zone_demand(entity_id, demand)

        # Learning update for the active seasonal track (initial + continuous weekly EMA)
        thermal_model = self._thermal_models[entity_id]
        if hvac_mode in (HVAC_MODE_HEAT, HVAC_MODE_COOL):
            track_mode = "cool" if hvac_mode == HVAC_MODE_COOL else "heat"
            tuner = self._autotuners_cool[entity_id] if track_mode == "cool" else self._autotuners_heat[entity_id]
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
                self._apply_tuner_pid_to_controller(entity_id, mode=track_mode)
                if callable(getattr(self.coordinator, "async_notify_pid_entities", None)):
                    self.coordinator.async_notify_pid_entities()
                if just_completed:
                    _LOGGER.info(
                        "%s Autotuning completed for %s! Smart PID activated. Kp=%.1f, Ki=%.4f, Kd=%.1f",
                        "Cooling" if track_mode == "cool" else "Heating",
                        entity_id, tuner.kp, tuner.ki, tuner.kd,
                    )
            if (
                len(tuner.completed_cycles) > prev_cycles
                or just_completed
                or getattr(tuner, "needs_save", False)
            ):
                if not just_completed and len(tuner.completed_cycles) > prev_cycles:
                    _LOGGER.info(
                        "%s Autotuning cycle %d/%d recorded for %s. Saving progress.",
                        "Cooling" if track_mode == "cool" else "Heating",
                        len(tuner.completed_cycles), tuner.required_cycles, entity_id,
                    )
                await self.async_save_autotuner_states()

        # Feed Thermal Observer (with effective demand gating for heating_rate)
        if hvac_mode != HVAC_MODE_COOL and hvac_mode != "cool":
            model_update_fn = thermal_model.update
            try:
                m_params = inspect.signature(model_update_fn).parameters
                if "demand" in m_params or any(
                    p.kind == inspect.Parameter.VAR_KEYWORD for p in m_params.values()
                ):
                    model_update_fn(current_temp, demand > 0, hvac_mode=hvac_mode, demand=demand)
                else:
                    model_update_fn(current_temp, demand > 0, hvac_mode=hvac_mode)
            except (ValueError, TypeError):
                model_update_fn(current_temp, demand > 0, hvac_mode=hvac_mode)
            if hasattr(self.coordinator, "storage"):
                self.coordinator.debounced_save_thermal_states(self._thermal_models)

        active_tuner = self._autotuners_cool[entity_id] if hvac_mode == HVAC_MODE_COOL else self._autotuners_heat[entity_id]
        _LOGGER.debug(
            "Zone '%s' Demand updated: %.1f%% (Temp: %s, Target: %s, Mode: %s, Track: %s)",
            entity_id,
            demand,
            current_temp,
            target_temp,
            "PID" if active_tuner.state == active_tuner.STATE_COMPLETED else "Hysteresis",
            hvac_mode,
        )
        return demand
