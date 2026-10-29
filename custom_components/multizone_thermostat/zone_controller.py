"""Zone Controller for Multizone Thermostat: orchestrates PID, autotuning, thermal model, and weather compensation."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from .const import (
    CONF_ZONE_NAME,
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

        for zone in self.zones:
            name = zone.get(CONF_ZONE_NAME)
            if not name:
                continue
            climate_id = make_zone_entity_id(name)
            # Default Kp=100, Ki=0, Kd=0 (will be overridden by Autolearning later)
            self._pids[climate_id] = MultizonePID(
                kp=100.0, ki=0.0, kd=0.0, out_min=0.0, out_max=100.0, sensor_timeout=7200.0
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

    def get_pid(self, climate_id: str) -> MultizonePID | None:
        """Get PID controller for a zone."""
        return self._pids.get(climate_id)

    def get_autotuner(self, climate_id: str) -> PassiveAutotuneObserver | None:
        """Get autotuner for a zone."""
        return self._autotuners.get(climate_id)

    def get_thermal_model(self, climate_id: str) -> ThermalObserver | None:
        """Get thermal model for a zone."""
        return self._thermal_models.get(climate_id)

    def load_state(self, autotune_data: dict[str, Any], thermal_data: dict[str, Any]) -> None:
        """Restore autotuner and thermal model states from persistent storage."""
        if autotune_data:
            for climate_id, tuner in self._autotuners.items():
                if climate_id in autotune_data:
                    tuner.load_state(autotune_data[climate_id])
                    if tuner.state == tuner.STATE_COMPLETED:
                        self._pids[climate_id].set_pid_param(kp=tuner.kp, ki=tuner.ki, kd=tuner.kd)
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

        # Update PID sensor timestamp when a new or changed temperature reading arrives
        if self._last_seen_temps.get(entity_id) != current_temp:
            self._last_seen_temps[entity_id] = current_temp
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
                            if getattr(weather_state, "domain", None) == "weather":
                                temp_attr = weather_state.attributes.get("temperature")
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
        if tuner.state != tuner.STATE_COMPLETED:
            tuner.update(current_temp, demand > 0)
            # Check if this update just completed the learning phase
            if tuner.state == tuner.STATE_COMPLETED:
                self._pids[entity_id].set_pid_param(kp=tuner.kp, ki=tuner.ki, kd=tuner.kd)
                _LOGGER.info(
                    "Autotuning just completed for %s! Smart PID activated. Kp=%.1f, Ki=%.4f, Kd=%.1f",
                    entity_id,
                    tuner.kp,
                    tuner.ki,
                    tuner.kd,
                )
                await self.async_save_autotuner_states()

        # Feed Thermal Observer
        self._thermal_models[entity_id].update(current_temp, demand > 0)
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
