from datetime import datetime
import asyncio
import inspect
import logging

from ..const import CONF_ZONE_NAME, make_zone_entity_id

_LOGGER = logging.getLogger(__name__)

class PlantOrchestrator:
    """Orchestrates the boiler PWM ticks and demand logic."""
    
    def __init__(self, hass, demand_aggregator, boiler_backend, coordinator) -> None:
        self.hass = hass
        self.demand_aggregator = demand_aggregator
        self.boiler_backend = boiler_backend
        self.coordinator = coordinator
        
    async def async_tick(self, now: datetime) -> None:
        """Periodic PWM tick for boiler."""
        try:
            if hasattr(self.coordinator, "anti_seize_manager") and self.coordinator.anti_seize_manager.is_running:
                return
                
            await self._async_update_boiler()
        except Exception as err:
            _LOGGER.error("Error in PlantOrchestrator.async_tick: %s", err)

    async def _async_update_boiler(self) -> None:
        """Handle the logic for pushing demand to boiler backend."""
        climate_entities = getattr(self.coordinator, "_climate_entities", None)
        if isinstance(climate_entities, dict):
            for ent in list(climate_entities.values()):
                if hasattr(ent, "check_sensor_staleness"):
                    ent.check_sensor_staleness()

        frost_emergency = False
        frost_mgr = getattr(self.coordinator, "frost_manager", None)
        handle_fn = getattr(frost_mgr, "async_handle_frost_emergencies", None)
        if inspect.iscoroutinefunction(handle_fn):
            frost_emergency = bool(await handle_fn())

        if not frost_emergency:
            for climate_id in list(getattr(self.coordinator, "_climate_callbacks", {}).keys()):
                if hasattr(self.coordinator, "is_zone_in_frost_emergency") and self.coordinator.is_zone_in_frost_emergency(climate_id):
                    frost_emergency = True
                    break

        # Hard stop if master switch is OFF
        if not self.coordinator.get_master_state() and not frost_emergency:
            await self.boiler_backend.async_emergency_off()
            return

        plant_diag = getattr(self.coordinator, "plant_diagnostics", None)
        zones = getattr(self.coordinator, "zones", None)
        if plant_diag and isinstance(zones, list):
            for zone in zones:
                zone_name = zone.get(CONF_ZONE_NAME) if isinstance(zone, dict) else None
                if zone_name:
                    cid = make_zone_entity_id(zone_name)
                    if hasattr(plant_diag, "evaluate_zone_anomalies"):
                        plant_diag.evaluate_zone_anomalies(cid)
                    if not frost_emergency and hasattr(plant_diag, "has_critical_sensor_fault"):
                        if plant_diag.has_critical_sensor_fault(cid) is True:
                            self.demand_aggregator.set_zone_demand(cid, 0.0)

        if not frost_emergency and isinstance(climate_entities, dict):
            for climate_id, ent in list(climate_entities.items()):
                if getattr(ent, "current_temperature", False) is None:
                    self.demand_aggregator.set_zone_demand(climate_id, 0.0)
                elif (
                    plant_diag
                    and hasattr(plant_diag, "has_critical_sensor_fault")
                    and plant_diag.has_critical_sensor_fault(climate_id) is True
                ):
                    self.demand_aggregator.set_zone_demand(climate_id, 0.0)

        dhw_active = getattr(self.coordinator, "is_dhw_active", False)
        agg = self.demand_aggregator.calculate(
            is_dhw_active=dhw_active,
            frost_emergency=frost_emergency,
        )
                
        await self.boiler_backend.async_update(agg.demand, agg.peak_zone, frost_emergency)
