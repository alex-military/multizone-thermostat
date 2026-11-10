from .plant_decision import (
    PlantInputs,
    decide_heating,
    AUTO,
)
from datetime import datetime
import asyncio
import inspect
import logging

from ..const import (
    CONF_ZONE_NAME,
    make_zone_entity_id,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    ZONE_MODE_BYPASS,
    SOURCE_PRIORITY_GAS_ONLY,
    SOURCE_PRIORITY_ELECTRIC_ONLY,
    SOURCE_PRIORITY_ELECTRIC,
    SOURCE_PRIORITY_COMBINED,
)

_LOGGER = logging.getLogger(__name__)


class PlantOrchestrator:
    """Orchestrates the boiler and central heat pump PWM ticks and demand logic."""

    def __init__(self, hass, demand_aggregator, boiler_backend, coordinator, heat_pump_backend=None) -> None:
        self.hass = hass
        self.demand_aggregator = demand_aggregator
        self.boiler_backend = boiler_backend
        self.coordinator = coordinator
        self.heat_pump_backend = heat_pump_backend
        self._last_plant_command = None

    def _get_hp_backend(self):
        return self.heat_pump_backend or getattr(self.coordinator, "heat_pump_backend", None)

    @property
    def last_plant_command(self):
        """Return the last PlantCommand from decide_heating."""
        return self._last_plant_command

    def _calculate_cooling_demand(self) -> tuple[float, str | None]:
        """Calculate central cooling demand across active cooling zones."""
        climate_entities = getattr(self.coordinator, "_climate_entities", None)
        if not isinstance(climate_entities, dict):
            return (0.0, None)

        max_cool_demand = 0.0
        peak_zone = None
        split_mgr = getattr(self.coordinator, "split_manager", None)

        for cid, ent in list(climate_entities.items()):
            mode_fn = getattr(self.coordinator, "get_zone_mode", None)
            z_mode = mode_fn(cid) if callable(mode_fn) else "primary"
            if z_mode == ZONE_MODE_BYPASS:
                continue

            hvac_val = str(getattr(ent, "hvac_mode", "") or "")
            if hasattr(getattr(ent, "hvac_mode", None), "value"):
                hvac_val = str(ent.hvac_mode.value)
            if hvac_val != HVAC_MODE_COOL:
                continue

            # If a room split is actively cooling this zone, central hydronic cooling is only needed if no split
            if split_mgr and hasattr(split_mgr, "has_split") and split_mgr.has_split(cid) is True:
                if hasattr(split_mgr, "is_split_active") and split_mgr.is_split_active(cid) is True:
                    continue

            # Prioritize calculated zone cooling demand from demand_aggregator
            dem_fn = getattr(self.demand_aggregator, "get_zone_demand", None)
            z_dem = float(dem_fn(cid) or 0.0) if callable(dem_fn) else 0.0

            if z_dem <= 0.0:
                curr_t = getattr(ent, "current_temperature", None)
                targ_t = getattr(ent, "target_temperature", None)
                if isinstance(curr_t, (int, float)) and isinstance(targ_t, (int, float)):
                    delta = float(curr_t) - float(targ_t)
                    if delta > 0.2:
                        z_dem = min(100.0, max(20.0, delta * 50.0))

            if z_dem > max_cool_demand:
                max_cool_demand = z_dem
                peak_zone = cid

        return (max_cool_demand, peak_zone)

    async def async_tick(self, now: datetime) -> None:
        """Periodic PWM tick for boiler and central heat pump."""
        try:
            if hasattr(self.coordinator, "anti_seize_manager") and self.coordinator.anti_seize_manager.is_running:
                return

            await self._async_update_boiler()
        except Exception as err:
            _LOGGER.error("Error in PlantOrchestrator.async_tick: %s", err)

    async def _async_update_boiler(self) -> None:
        """Handle the logic for pushing demand to boiler and central heat pump backends."""
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

        hp_backend = self._get_hp_backend()

        # Hard stop if master switch is OFF
        if not self.coordinator.get_master_state() and not frost_emergency:
            await self.boiler_backend.async_emergency_off()
            if hp_backend is not None and hasattr(hp_backend, "async_emergency_off"):
                await hp_backend.async_emergency_off()
            return

        master_mode = getattr(self.coordinator, "master_hvac_mode", HVAC_MODE_HEAT)
        if master_mode == HVAC_MODE_COOL and not frost_emergency:
            # In cooling mode, gas boiler is strictly OFF (0.0% demand)
            await self.boiler_backend.async_update(0.0, None, False)
            if (
                hp_backend is not None
                and getattr(self.coordinator, "enable_heat_pump", False) is True
                and getattr(self.coordinator, "heat_pump_cooling", True) is True
            ):
                energy_mgr = getattr(self.coordinator, "energy_manager", None)
                solar_surplus = False
                solar_boost = False
                if energy_mgr is not None:
                    surp_fn = getattr(energy_mgr, "is_solar_surplus", None)
                    if callable(surp_fn):
                        res = surp_fn()
                        if res is True or (isinstance(res, bool) and res):
                            solar_surplus = True
                    elif surp_fn is True:
                        solar_surplus = True
                    boost_fn = getattr(energy_mgr, "is_external_override_active", None)
                    if callable(boost_fn):
                        res = boost_fn()
                        if res is True or (isinstance(res, bool) and res):
                            solar_boost = True
                    elif boost_fn is True:
                        solar_boost = True

                cool_demand, cool_peak = self._calculate_cooling_demand()
                if (solar_surplus or solar_boost) and cool_demand > 0.0:
                    cool_demand = max(cool_demand, 100.0)

                await hp_backend.async_update(cool_demand, cool_peak, False, hvac_mode=HVAC_MODE_COOL)
            elif hp_backend is not None:
                await hp_backend.async_update(0.0, None, False, hvac_mode=HVAC_MODE_COOL)
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

        hp_enabled = bool(getattr(self.coordinator, "enable_heat_pump", False) is True and hp_backend is not None)
        gas_enabled = bool(getattr(self.coordinator, "enable_gas_heater", True) is not False)

        # Collect priority and solar surplus from energy manager if present
        energy_mgr = getattr(self.coordinator, "energy_manager", None)
        priority = AUTO
        solar_surplus = False
        if energy_mgr is not None:
            prio_fn = getattr(energy_mgr, "get_heat_source_priority", None)
            if callable(prio_fn):
                res = prio_fn()
                if isinstance(res, str):
                    priority = res
            surp_fn = getattr(energy_mgr, "is_solar_surplus", None)
            if callable(surp_fn):
                solar_surplus = bool(surp_fn())
            elif surp_fn is True:
                solar_surplus = True

        # Check heat pump availability (entity online and not unavailable/unknown)
        hp_available = True
        if hp_backend is not None and getattr(hp_backend, "hp_entity", None) and isinstance(hp_backend.hp_entity, str):
            st = self.hass.states.get(hp_backend.hp_entity) if hasattr(self.hass, "states") and self.hass.states else None
            if st and st.state in ("unavailable", "unknown"):
                hp_available = False

        # Calculate max zone delta (for COMBINED boost mode)
        max_delta = 0.0
        if isinstance(climate_entities, dict):
            for ent in climate_entities.values():
                c_t = getattr(ent, "current_temperature", None)
                t_t = getattr(ent, "target_temperature", None)
                if isinstance(c_t, (int, float)) and isinstance(t_t, (int, float)):
                    diff = float(t_t) - float(c_t)
                    if diff > max_delta:
                        max_delta = diff

        # Build immutable inputs and invoke pure decide_heating logic
        inputs = PlantInputs(
            demand=agg.demand,
            priority=priority,
            gas_enabled=gas_enabled,
            hp_enabled=hp_enabled,
            hp_available=hp_available,
            solar_surplus=solar_surplus,
            max_zone_delta=max_delta,
            frost_emergency=frost_emergency,
        )

        cmd = decide_heating(inputs)
        self._last_plant_command = cmd
        _LOGGER.debug(
            "Plant Heating Arbitration: gas=%.1f%%, hp=%.1f%%, reason=%s",
            cmd.gas_demand,
            cmd.hp_demand,
            cmd.reason,
        )

        res_gas = self.boiler_backend.async_update(cmd.gas_demand, agg.peak_zone, frost_emergency)
        if inspect.isawaitable(res_gas):
            await res_gas

        if hp_backend is not None and hp_enabled:
            res_hp = hp_backend.async_update(cmd.hp_demand, agg.peak_zone, frost_emergency, hvac_mode=HVAC_MODE_HEAT)
            if inspect.isawaitable(res_hp):
                await res_hp
