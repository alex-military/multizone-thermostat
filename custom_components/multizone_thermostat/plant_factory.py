"""Subsystem factory for Multizone Thermostat heating plant."""
from __future__ import annotations

from typing import Any

from .zone_manager import ZoneManager
from .demand_aggregator import DemandAggregator
from .zone_controller import ZoneController
from .split.split_controller import SplitZoneManager
from .energy.energy_manager import EnergyManager
from .storage.storage_manager import StorageManager
from .calendar_manager import CalendarManager
from .schedule_manager import ScheduleProfileManager
from .routine_manager import RoutineManager
from .safety.frost import FrostManager
from .safety.anti_seize import AntiSeizeManager
from .plant_diagnostics.engine import PlantDiagnosticsEngine
from .boiler.opentherm_backend import OpenThermBoilerBackend
from .boiler.relay_backend import RelayBoilerBackend
from .boiler.centralized_backend import CentralizedBoilerBackend
from .boiler.heat_pump_backend import CentralHeatPumpBackend
from .const import MODE_CENTRAL, MODE_NONE
from .boiler.plant_orchestrator import PlantOrchestrator
from .cooling_policy import CoolingPolicy
from .master_controller import MasterController
from .listener_manager import ListenerManager
from .plant_config import PlantConfig


def build_plant_subsystems(coordinator: Any, hass: Any, config: PlantConfig) -> None:
    """Instantiate and wire all plant managers and subsystems onto the coordinator."""
    coordinator.zone_manager = ZoneManager(hass, coordinator)

    coordinator.demand_aggregator = DemandAggregator(
        zones=coordinator.zones,
        mode_getter=lambda cid: coordinator.get_zone_mode(cid),
    )
    coordinator.demand_aggregator.coordinator = coordinator

    coordinator.zone_controller = ZoneController(hass, coordinator)
    coordinator.split_manager = SplitZoneManager(hass, coordinator)
    coordinator.energy_manager = EnergyManager(hass, coordinator, config.raw_config)

    coordinator.storage = StorageManager(hass, coordinator.entry_id)

    # Share Store instances and backing dicts with StorageManager to prevent split-brain overwrites
    coordinator._store = coordinator.storage._window_store
    coordinator._legacy_window_store = coordinator.storage._legacy_window_store
    coordinator._preset_store = coordinator.storage._preset_store
    coordinator._settings_store = coordinator.storage._settings_store

    coordinator.calendar_manager = CalendarManager(coordinator)
    coordinator.schedule_manager = ScheduleProfileManager(coordinator)

    coordinator.routine_manager = RoutineManager(
        hass,
        coordinator.presence_sensor,
        coordinator.get_persistent_data,
        coordinator.async_set_persistent_data,
        coordinator.get_global_preset,
        coordinator.async_set_global_preset,
    )

    coordinator.frost_manager = FrostManager(hass, coordinator)
    coordinator.anti_seize_manager = AntiSeizeManager(hass, coordinator)
    coordinator.plant_diagnostics = PlantDiagnosticsEngine(coordinator)

    if coordinator.boiler_mode in (MODE_CENTRAL, MODE_NONE) or (not getattr(coordinator, "enable_gas_heater", True) and not getattr(coordinator, "enable_heat_pump", False)):
        coordinator.boiler_backend = CentralizedBoilerBackend(hass, coordinator)
    elif coordinator.boiler_mode == "opentherm":
        coordinator.boiler_backend = OpenThermBoilerBackend(
            hass,
            coordinator,
            coordinator.opentherm_entity,
            coordinator.opentherm_min_temp,
            coordinator.opentherm_max_temp,
            coordinator.opentherm_ch_switch,
        )
    else:
        coordinator.boiler_backend = RelayBoilerBackend(
            hass,
            coordinator,
            coordinator.boiler_switch,
            coordinator._min_cycle_on,
            coordinator._min_cycle_off,
            coordinator._valve_delay,
        )

    # PID / autotune / thermal models are owned by ZoneController
    coordinator._pids = coordinator.zone_controller.pids
    coordinator._autotuners = coordinator.zone_controller.autotuners
    coordinator._thermal_models = coordinator.zone_controller.thermal_models

    coordinator._presets = coordinator.storage._presets
    coordinator._settings = coordinator.storage._settings

    coordinator.heat_pump_backend = (
        CentralHeatPumpBackend(
            hass,
            coordinator,
            coordinator.heat_pump_type,
            coordinator.heat_pump_entity,
            coordinator.heat_pump_min_temp,
            coordinator.heat_pump_max_temp,
            coordinator.heat_pump_ch_switch,
            coordinator.heat_pump_cooling,
            config.hp_cool_min_temp,
            config.hp_cool_max_temp,
            int(coordinator._valve_delay),
        )
        if coordinator.enable_heat_pump and coordinator.heat_pump_entity
        else None
    )

    coordinator.plant_orchestrator = PlantOrchestrator(
        hass,
        coordinator.demand_aggregator,
        coordinator.boiler_backend,
        coordinator,
        coordinator.heat_pump_backend,
    )

    coordinator.cooling_policy = CoolingPolicy(coordinator)
    coordinator.master_controller = MasterController(coordinator)
    coordinator.listener_manager = ListenerManager(coordinator)
