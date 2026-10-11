from datetime import datetime
import asyncio
import logging

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
        if hasattr(self.coordinator, "anti_seize_manager") and self.coordinator.anti_seize_manager.is_running:
            return
            
        await self._async_update_boiler()

    async def _async_update_boiler(self) -> None:
        """Handle the logic for pushing demand to boiler backend."""
        frost_emergency = False
        for climate_id in list(self.coordinator._climate_callbacks.keys()):
            if hasattr(self.coordinator, "is_zone_in_frost_emergency") and self.coordinator.is_zone_in_frost_emergency(climate_id):
                frost_emergency = True
                break

        # Hard stop if master switch is OFF
        if not self.coordinator.get_master_state() and not frost_emergency:
            await self.boiler_backend.async_emergency_off()
            return
            
        dhw_active = getattr(self.coordinator, "is_dhw_active", False)
        agg = self.demand_aggregator.calculate(
            is_dhw_active=dhw_active,
            frost_emergency=frost_emergency,
        )
                
        await self.boiler_backend.async_update(agg.demand, agg.peak_zone, frost_emergency)
