from collections.abc import Mapping
from datetime import datetime
import asyncio
import inspect
import logging
from types import SimpleNamespace

from ..const import CONF_ZONE_NAME, make_zone_entity_id

_LOGGER = logging.getLogger(__name__)

class PlantOrchestrator:
    """Orchestrates the boiler PWM ticks and demand logic."""
    
    def __init__(self, hass, demand_aggregator, boiler_backend, coordinator) -> None:
        self.hass = hass
        self.demand_aggregator = demand_aggregator
        self.boiler_backend = boiler_backend
        self.coordinator = coordinator
        self._master_off_logged = False
        self.last_aggregate = None  # last AggregatedDemand sent to the boiler (None when Master OFF)
        
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
            if not self._master_off_logged:
                _LOGGER.info("Master switch is OFF: boiler forced OFF and heat demand ignored (frost emergency: %s)", frost_emergency)
                self._master_off_logged = True
            self.last_aggregate = None
            await self.boiler_backend.async_emergency_off()
            return
        self._master_off_logged = False

        plant_diag = getattr(self.coordinator, "plant_diagnostics", None)
        zones = getattr(self.coordinator, "zones", None)
        if plant_diag and isinstance(zones, list):
            for zone in zones:
                zone_name = zone.get(CONF_ZONE_NAME) if isinstance(zone, dict) else None
                if zone_name:
                    cid = make_zone_entity_id(zone_name)
                    if hasattr(plant_diag, "evaluate_zone_anomalies"):
                        plant_diag.evaluate_zone_anomalies(cid)

        zone_ctrl = getattr(self.coordinator, "zone_controller", None)
        if (
            inspect.iscoroutinefunction(getattr(zone_ctrl, "async_update_zone", None))
            and isinstance(zones, list)
            and getattr(self.hass, "states", None) is not None
        ):
            for zone in zones:
                zone_name = zone.get(CONF_ZONE_NAME) if isinstance(zone, dict) else None
                if not zone_name:
                    continue
                cid = make_zone_entity_id(zone_name)
                if (
                    not frost_emergency
                    and plant_diag
                    and hasattr(plant_diag, "has_critical_sensor_fault")
                    and plant_diag.has_critical_sensor_fault(cid) is True
                ):
                    self.demand_aggregator.set_zone_demand(cid, 0.0)
                    continue
                ent = climate_entities.get(cid) if isinstance(climate_entities, dict) else None
                actual_eid = getattr(ent, "entity_id", cid)
                state_obj = self.hass.states.get(actual_eid) or self.hass.states.get(cid)
                if state_obj is None or not isinstance(getattr(state_obj, "attributes", None), Mapping):
                    curr_t = getattr(ent, "current_temperature", None) if ent is not None else None
                    targ_t = getattr(ent, "target_temperature", None) if ent is not None else None
                    if isinstance(curr_t, (int, float)) and isinstance(targ_t, (int, float)):
                        state_obj = SimpleNamespace(
                            entity_id=actual_eid,
                            state=getattr(ent, "hvac_mode", "heat"),
                            attributes={
                                "current_temperature": curr_t,
                                "temperature": targ_t,
                            },
                            last_reported=None,
                            last_updated=None,
                        )
                    else:
                        state_obj = None
                if state_obj is not None:
                    await zone_ctrl.async_update_zone(cid, state_obj)

        if plant_diag and isinstance(zones, list):
            for zone in zones:
                zone_name = zone.get(CONF_ZONE_NAME) if isinstance(zone, dict) else None
                if zone_name:
                    cid = make_zone_entity_id(zone_name)
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
                
        self.last_aggregate = agg
        await self.boiler_backend.async_update(agg.demand, agg.peak_zone, frost_emergency)
