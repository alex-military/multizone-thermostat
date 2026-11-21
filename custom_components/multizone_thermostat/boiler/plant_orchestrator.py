from .plant_decision import (
    PlantInputs,
    decide_heating,
    AUTO,
)
from ..demand_aggregator import AggregatedDemand
from collections.abc import Mapping
from datetime import datetime
from types import SimpleNamespace
import asyncio
import inspect
import logging
from typing import Any

try:
    from homeassistant.const import UnitOfTemperature
except ImportError:
    UnitOfTemperature = None  # type: ignore[assignment]

from ..const import (
    CONF_ZONE_NAME,
    make_zone_entity_id,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    ZONE_MODE_BYPASS,
    ZONE_MODE_SECONDARY,
    SOURCE_PRIORITY_GAS_ONLY,
    SOURCE_PRIORITY_ELECTRIC_ONLY,
    SOURCE_PRIORITY_ELECTRIC,
    SOURCE_PRIORITY_COMBINED,
)
from ..protocols import BoilerBackendProtocol, CoordinatorProtocol

_LOGGER = logging.getLogger(__name__)


def _eval_energy_flag(energy_mgr: Any, method_name: str) -> bool:
    """Evaluate a boolean or callable energy manager flag safely."""
    if energy_mgr is None:
        return False
    flag = getattr(energy_mgr, method_name, None)
    if callable(flag):
        return flag() is True
    return flag is True


def _get_hvac_mode_str(ent: Any) -> str:
    """Extract normalized HVAC mode string from a climate entity or stub."""
    try:
        raw = ent.hvac_mode
    except AttributeError:
        return ""
    if raw is None:
        return ""
    try:
        return str(raw.value)
    except AttributeError:
        return str(raw)


def check_is_modulating_plant(coordinator: Any, boiler_backend: Any = None, heat_pump_backend: Any = None) -> bool:
    """Return True if the plant has a modulating generator (OpenTherm or Heat Pump)."""
    backend = boiler_backend if boiler_backend is not None else getattr(coordinator, "boiler_backend", None)
    if backend and getattr(backend, "is_modulating", False):
        return True
    hp_backend = heat_pump_backend if heat_pump_backend is not None else getattr(coordinator, "heat_pump_backend", None)
    if hp_backend and getattr(hp_backend, "is_modulating", False):
        return True
    if getattr(coordinator, "opentherm_entity", None):
        return True
    if getattr(coordinator, "enable_heat_pump", False) and getattr(coordinator, "heat_pump_entity", None):
        return True
    return False


def check_is_dhw_active(coordinator: Any, hass: Any = None) -> bool:
    """Return True if Domestic Hot Water (DHW) production is active."""
    hass = hass or getattr(coordinator, "hass", None)
    states = hass.states if hass is not None else None
    dhw_sensor = getattr(coordinator, "dhw_active_sensor", None)
    if dhw_sensor and isinstance(dhw_sensor, str) and states:
        st = states.get(dhw_sensor)
        st_val = getattr(st, "state", None) if st is not None else None
        if st_val not in ("unavailable", "unknown", None):
            if str(st_val).lower() in ("on", "true", "1", "charging", "heat", "heating", "active"):
                return True
            st_attrs = getattr(st, "attributes", None)
            if isinstance(st_attrs, Mapping):
                for ak in ("charging", "is_charging", "dhw_active", "active"):
                    av = st_attrs.get(ak)
                    if av is True or (isinstance(av, str) and av.lower() in ("true", "on", "1")):
                        return True
            return False

    plant_diag = getattr(coordinator, "plant_diagnostics", None)
    if plant_diag is not None:
        try:
            diag = plant_diag.get_opentherm_diagnostics()
            if isinstance(diag, dict) and diag.get("dhw_active", False):
                return True
        except (KeyError, AttributeError, ValueError, TypeError) as err:
            _LOGGER.debug("DHW OpenTherm diagnostics check skipped: %s", err)

    if states:
        for std_id in ("binary_sensor.boiler_dhw_charging", "binary_sensor.dhw_charging"):
            try:
                st = states.get(std_id)
                if st is not None and str(st.state).lower() in ("on", "true", "1", "charging", "heat", "heating"):
                    return True
            except (KeyError, AttributeError, ValueError, TypeError) as err:
                _LOGGER.debug("DHW sensor %s check skipped: %s", std_id, err)

    return False


def check_boiler_status_reason(coordinator: Any, boiler_backend: Any = None, heat_pump_backend: Any = None) -> str:
    """Return human-readable explanation of why the boiler is currently in its state."""
    hp_backend = heat_pump_backend if heat_pump_backend is not None else getattr(coordinator, "heat_pump_backend", None)
    b_backend = boiler_backend if boiler_backend is not None else getattr(coordinator, "boiler_backend", None)
    if not getattr(coordinator, "enable_gas_heater", True) and getattr(coordinator, "enable_heat_pump", False) and hp_backend:
        return getattr(hp_backend, "status_reason", "unknown")
    return getattr(b_backend, "status_reason", "unknown")


class PlantOrchestrator:
    """Orchestrates the boiler and central heat pump PWM ticks and demand logic."""

    def __init__(
        self,
        hass: Any,
        demand_aggregator: Any,
        boiler_backend: BoilerBackendProtocol | None,
        coordinator: CoordinatorProtocol,
        heat_pump_backend: Any = None,
    ) -> None:
        self.hass = hass
        self.demand_aggregator = demand_aggregator
        self.boiler_backend: BoilerBackendProtocol | None = boiler_backend
        self.coordinator: CoordinatorProtocol = coordinator
        self.heat_pump_backend = heat_pump_backend
        self._last_plant_command = None
        self._master_off_logged = False
        self.last_aggregate = None

    async def _async_refresh_zones_proactively(self, force: bool = False) -> None:
        """Proactively re-evaluate zone PID demands before plant aggregation."""
        zone_ctrl = getattr(self.coordinator, "zone_controller", None)
        if zone_ctrl is None or not callable(getattr(zone_ctrl, "async_update_zone", None)):
            return

        states = self.hass.states if self.hass else None
        climates = getattr(self.coordinator, "_climate_entities", None)
        climates_map = climates if isinstance(climates, dict) else {}
        zones = getattr(self.coordinator, "zones", None)
        resolve_fn = getattr(self.coordinator, "resolve_zone_id", None)
        set_dem_fn = getattr(self.demand_aggregator, "set_zone_demand", None)
        existing_demands = getattr(self.demand_aggregator, "_zone_demands", None)

        ordered_cids: list[str] = []
        if isinstance(zones, list):
            for z in zones:
                if isinstance(z, dict) and z.get(CONF_ZONE_NAME):
                    ordered_cids.append(make_zone_entity_id(z[CONF_ZONE_NAME]))
        for raw_id in climates_map.keys():
            canon = resolve_fn(raw_id) if callable(resolve_fn) else raw_id
            ordered_cids.append(canon)
        unique_cids = list(dict.fromkeys(ordered_cids))

        for cid in unique_cids:
            if not force and isinstance(existing_demands, dict) and cid in existing_demands:
                pid_evaluated = False
                if hasattr(zone_ctrl, "get_pid") and callable(zone_ctrl.get_pid):
                    try:
                        pid_heat = zone_ctrl.get_pid(cid, "heat")
                    except TypeError:
                        try:
                            pid_heat = zone_ctrl.get_pid(cid)
                        except Exception:
                            pid_heat = None
                    except Exception:
                        pid_heat = None
                    try:
                        pid_cool = zone_ctrl.get_pid(cid, "cool")
                    except Exception:
                        pid_cool = None
                    has_eval_h = getattr(pid_heat, "has_evaluated", None)
                    has_eval_c = getattr(pid_cool, "has_evaluated", None)
                    if (
                        (isinstance(has_eval_h, bool) and has_eval_h)
                        or (isinstance(has_eval_c, bool) and has_eval_c)
                        or (not isinstance(has_eval_h, bool) and getattr(pid_heat, "_last_input_time", None) is not None)
                        or (not isinstance(has_eval_c, bool) and getattr(pid_cool, "_last_input_time", None) is not None)
                    ):
                        pid_evaluated = True

                if existing_demands[cid] > 0.0 or pid_evaluated:
                    continue

            ent = climates_map.get(cid)
            real_eid = getattr(ent, "entity_id", None) if ent is not None else None
            st = None
            if states:
                for lookup_id in dict.fromkeys(x for x in (real_eid, cid) if x):
                    cand = states.get(lookup_id)
                    if cand is not None:
                        st = cand
                        break

            state_obj = None
            if st is not None and isinstance(getattr(st, "attributes", None), Mapping) and isinstance(getattr(st, "state", None), str):
                state_obj = st
            elif ent is not None:
                mode_str = _get_hvac_mode_str(ent) or "off"
                attrs: dict[str, Any] = {}
                if st is not None and isinstance(getattr(st, "attributes", None), Mapping):
                    attrs.update(dict(st.attributes))
                for attr_name, key in (
                    ("current_temperature", "current_temperature"),
                    ("target_temperature", "temperature"),
                    ("preset_mode", "preset_mode"),
                ):
                    try:
                        val = getattr(ent, attr_name)
                    except AttributeError:
                        val = None
                    if val is not None:
                        attrs.setdefault(key, val)
                raw_tu = getattr(ent, "temperature_unit", None) or getattr(ent, "_attr_temperature_unit", None)
                ha_c = getattr(UnitOfTemperature, "CELSIUS", "°C") if UnitOfTemperature is not None else "°C"
                temp_unit = raw_tu if isinstance(raw_tu, str) and raw_tu else (ha_c if isinstance(ha_c, str) else "°C")
                attrs.setdefault("temperature_unit", temp_unit)
                state_obj = SimpleNamespace(state=mode_str, attributes=attrs)

            if state_obj is None:
                continue

            res = zone_ctrl.async_update_zone(cid, state_obj)
            dem = await res if inspect.iscoroutine(res) else res
            if isinstance(dem, (int, float)) and not isinstance(dem, bool) and callable(set_dem_fn):
                set_dem_fn(cid, float(dem))

    def _get_hp_backend(self):
        return self.heat_pump_backend or getattr(self.coordinator, "heat_pump_backend", None)

    @property
    def is_modulating_plant(self) -> bool:
        """Return True if the plant has a modulating generator (OpenTherm or Heat Pump)."""
        return check_is_modulating_plant(self.coordinator, self.boiler_backend, self._get_hp_backend())

    @property
    def is_dhw_active(self) -> bool:
        """Return True if Domestic Hot Water (DHW) production is active."""
        return check_is_dhw_active(self.coordinator, self.hass)

    @property
    def boiler_status_reason(self) -> str:
        """Return human-readable explanation of why the boiler is currently in its state."""
        return check_boiler_status_reason(self.coordinator, self.boiler_backend, self._get_hp_backend())

    async def async_refresh(self, force_refresh_zones: bool = False) -> None:
        """Refresh plant state by updating boiler and central heat pump."""
        await self._async_update_boiler(force_refresh_zones=force_refresh_zones)

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
        mode_fn = getattr(self.coordinator, "get_zone_mode", None)
        dem_fn = getattr(self.demand_aggregator, "get_zone_demand", None)

        diag = getattr(self.coordinator, "plant_diagnostics", None)
        for cid, ent in list(climate_entities.items()):
            if callable(mode_fn) and mode_fn(cid) == ZONE_MODE_BYPASS:
                continue
            if diag is not None and diag.has_critical_sensor_fault(cid) is True:
                continue

            if _get_hvac_mode_str(ent) != HVAC_MODE_COOL:
                continue

            # If a room split is actively cooling this zone, central hydronic cooling is only needed if no split
            if split_mgr is not None:
                try:
                    if split_mgr.has_split(cid) is True and split_mgr.is_split_active(cid) is True:
                        continue
                except AttributeError:
                    pass

            # Prioritize calculated zone cooling demand from demand_aggregator
            z_dem = float(dem_fn(cid) or 0.0) if callable(dem_fn) else 0.0

            if z_dem <= 0.0:
                try:
                    curr_t = ent.current_temperature
                    targ_t = ent.target_temperature
                except AttributeError:
                    curr_t = targ_t = None
                if isinstance(curr_t, (int, float)) and isinstance(targ_t, (int, float)):
                    delta = float(curr_t) - float(targ_t)
                    if delta > 0.2:
                        z_dem = min(100.0, max(20.0, delta * 50.0))

            if z_dem > max_cool_demand:
                max_cool_demand = z_dem
                peak_zone = cid

        return (max_cool_demand, peak_zone)

    def _is_gas_boiler_confirmed_on(self) -> bool:
        """Return True if the gas boiler backend entity is still confirmed ON/heating."""
        if self.boiler_backend is None or not hasattr(self.hass, "states") or not self.hass.states:
            return False
        b_switch = getattr(self.boiler_backend, "boiler_switch", None)
        if isinstance(b_switch, str) and b_switch:
            st = self.hass.states.get(b_switch)
            if st is not None and getattr(st, "state", None) == "on":
                return True
        ch_sw = getattr(self.boiler_backend, "ch_switch", None)
        if isinstance(ch_sw, str) and ch_sw:
            st = self.hass.states.get(ch_sw)
            if st is not None and getattr(st, "state", None) == "on":
                return True
        ot_ent = getattr(self.boiler_backend, "opentherm_entity", None)
        if isinstance(ot_ent, str) and ot_ent:
            st = self.hass.states.get(ot_ent)
            if st is not None and getattr(st, "state", None) == "heat":
                return True
        return False

    async def _check_frost_emergency_active(self) -> bool:
        """Evaluate frost manager and zone frost flags cleanly."""
        coord = self.coordinator
        frost_mgr = getattr(coord, "frost_manager", None)
        if frost_mgr is not None:
            try:
                res_frost = frost_mgr.async_handle_frost_emergencies()
                if inspect.isawaitable(res_frost) and bool(await res_frost):
                    return True
            except AttributeError:
                pass
        frost_check_fn = getattr(coord, "is_zone_in_frost_emergency", None)
        if callable(frost_check_fn):
            for climate_id in list(getattr(coord, "_climate_callbacks", {}).keys()):
                if frost_check_fn(climate_id) is True:
                    return True
        return False

    async def async_tick(self, now: datetime) -> None:
        """Periodic PWM tick for boiler and central heat pump."""
        try:
            anti_seize = getattr(self.coordinator, "anti_seize_manager", None)
            if anti_seize is not None and anti_seize.is_running is True:
                if not await self._check_frost_emergency_active():
                    return
                stop_fn = getattr(anti_seize, "stop", None)
                if callable(stop_fn):
                    stop_fn()

            await self._async_update_boiler()
        except Exception as err:
            _LOGGER.error("Error in PlantOrchestrator.async_tick: %s", err)

    async def _async_update_boiler(self, force_refresh_zones: bool = False) -> None:
        """Handle the logic for pushing demand to boiler and central heat pump backends."""
        coord = self.coordinator
        climate_entities = getattr(coord, "_climate_entities", None)
        if isinstance(climate_entities, dict):
            for ent in list(climate_entities.values()):
                try:
                    ent.check_sensor_staleness()
                except AttributeError:
                    pass

        frost_emergency = False
        frost_mgr = getattr(coord, "frost_manager", None)
        if frost_mgr is not None:
            try:
                res_frost = frost_mgr.async_handle_frost_emergencies()
                if inspect.isawaitable(res_frost):
                    frost_emergency = bool(await res_frost)
            except AttributeError:
                pass

        if not frost_emergency:
            frost_check_fn = getattr(coord, "is_zone_in_frost_emergency", None)
            if callable(frost_check_fn):
                for climate_id in list(getattr(coord, "_climate_callbacks", {}).keys()):
                    if frost_check_fn(climate_id):
                        frost_emergency = True
                        break

        hp_backend = self._get_hp_backend()

        # Hard stop if master switch is OFF
        if not coord.get_master_state() and not frost_emergency:
            if not self._master_off_logged:
                _LOGGER.info("Master switch is OFF (no frost emergency): stopping plant")
                self._master_off_logged = True
            self.last_aggregate = None
            if self.boiler_backend is not None:
                await self.boiler_backend.async_emergency_off()
            if hp_backend is not None:
                try:
                    await hp_backend.async_emergency_off()
                except AttributeError:
                    pass
            return
        self._master_off_logged = False

        await self._async_refresh_zones_proactively(force=force_refresh_zones)

        diag = getattr(coord, "plant_diagnostics", None)
        if diag is not None and callable(getattr(diag, "evaluate_zone_anomalies", None)):
            for z in getattr(coord, "zones", []) or []:
                z_cid = z.get("climate_id") or (make_zone_entity_id(z[CONF_ZONE_NAME]) if z.get(CONF_ZONE_NAME) else None)
                if z_cid:
                    try:
                        diag.evaluate_zone_anomalies(z_cid)
                    except (AttributeError, TypeError, ValueError):
                        pass

        master_mode = getattr(coord, "master_hvac_mode", HVAC_MODE_HEAT)
        energy_mgr = getattr(coord, "energy_manager", None)
        if master_mode == HVAC_MODE_COOL and not frost_emergency:
            # In cooling mode, command gas boiler OFF (0.0%) and escalate to emergency off if still firing
            if self.boiler_backend is not None:
                res_upd = self.boiler_backend.async_update(0.0, None, False)
                if inspect.isawaitable(res_upd):
                    await res_upd
                if self._is_gas_boiler_confirmed_on():
                    off_fn = getattr(self.boiler_backend, "async_emergency_off", None)
                    if callable(off_fn):
                        res_off = off_fn()
                        if inspect.isawaitable(res_off):
                            await res_off
            if (
                hp_backend is not None
                and getattr(coord, "enable_heat_pump", False) is True
                and getattr(coord, "heat_pump_cooling", True) is True
            ):
                solar_surplus = _eval_energy_flag(energy_mgr, "is_solar_surplus")
                solar_boost = _eval_energy_flag(energy_mgr, "is_external_override_active")

                cool_demand, cool_peak = self._calculate_cooling_demand()
                if (solar_surplus or solar_boost) and cool_demand > 0.0:
                    cool_demand = max(cool_demand, 100.0)
                if cool_demand > 0.0 and self._is_gas_boiler_confirmed_on():
                    _LOGGER.warning(
                        "Heat pump cooling blocked while gas boiler is still confirmed ON; forcing cool demand to 0%%"
                    )
                    cool_demand = 0.0
                    cool_peak = None

                self.last_aggregate = AggregatedDemand(
                    demand=cool_demand,
                    peak_zone=cool_peak,
                    strategy="cooling",
                )
                await hp_backend.async_update(cool_demand, cool_peak, False, hvac_mode=HVAC_MODE_COOL)
            elif hp_backend is not None:
                self.last_aggregate = AggregatedDemand(
                    demand=0.0,
                    peak_zone=None,
                    strategy="cooling",
                )
                await hp_backend.async_update(0.0, None, False, hvac_mode=HVAC_MODE_COOL)
            else:
                self.last_aggregate = AggregatedDemand(
                    demand=0.0,
                    peak_zone=None,
                    strategy="cooling",
                )
            return

        plant_diag = getattr(coord, "plant_diagnostics", None)
        zones = getattr(coord, "zones", None)
        if plant_diag is not None and isinstance(zones, list):
            for zone in zones:
                zone_name = zone.get(CONF_ZONE_NAME) if isinstance(zone, dict) else None
                if zone_name:
                    cid = make_zone_entity_id(zone_name)
                    try:
                        plant_diag.evaluate_zone_anomalies(cid)
                    except AttributeError:
                        pass
                    if not frost_emergency:
                        try:
                            if plant_diag.has_critical_sensor_fault(cid) is True:
                                self.demand_aggregator.set_zone_demand(cid, 0.0)
                        except AttributeError:
                            pass

        if not frost_emergency and isinstance(climate_entities, dict):
            for climate_id, ent in list(climate_entities.items()):
                if getattr(ent, "current_temperature", False) is None:
                    self.demand_aggregator.set_zone_demand(climate_id, 0.0)
                elif plant_diag is not None:
                    try:
                        if plant_diag.has_critical_sensor_fault(climate_id) is True:
                            self.demand_aggregator.set_zone_demand(climate_id, 0.0)
                    except AttributeError:
                        pass

        coord_dhw = getattr(coord, "is_dhw_active", None)
        if isinstance(coord_dhw, bool) and not isinstance(getattr(type(coord), "is_dhw_active", None), property):
            dhw_active = coord_dhw
        else:
            try:
                dhw_active = bool(self.is_dhw_active)
            except Exception:
                dhw_active = bool(coord_dhw) if isinstance(coord_dhw, bool) else False
            if not dhw_active and isinstance(coord_dhw, bool):
                dhw_active = coord_dhw
        agg = self.demand_aggregator.calculate(
            is_dhw_active=dhw_active,
            frost_emergency=frost_emergency,
        )
        self.last_aggregate = agg

        hp_enabled = bool(getattr(coord, "enable_heat_pump", False) is True and hp_backend is not None)
        gas_enabled = bool(getattr(coord, "enable_gas_heater", True) is not False)

        # Collect priority and solar surplus from energy manager if present
        priority = AUTO
        solar_surplus = _eval_energy_flag(energy_mgr, "is_solar_surplus")
        if energy_mgr is not None:
            prio_fn = getattr(energy_mgr, "get_heat_source_priority", None)
            if callable(prio_fn):
                res = prio_fn()
                if isinstance(res, str):
                    priority = res

        # Check heat pump availability (entity online and not unavailable/unknown)
        hp_available = True
        hp_ent = hp_backend.hp_entity if hp_backend is not None else None
        states = self.hass.states if self.hass else None
        if isinstance(hp_ent, str) and hp_ent and states:
            st = states.get(hp_ent)
            if st and st.state in ("unavailable", "unknown"):
                hp_available = False

        # Calculate max zone delta (for COMBINED boost mode) across active primary heating zones only
        max_delta = 0.0
        if isinstance(climate_entities, dict):
            mode_fn = getattr(coord, "get_zone_mode", None)
            split_mgr = getattr(coord, "split_manager", None)
            for cid, ent in climate_entities.items():
                try:
                    if callable(mode_fn) and mode_fn(cid) in (ZONE_MODE_BYPASS, ZONE_MODE_SECONDARY):
                        continue
                except AttributeError:
                    pass
                if plant_diag is not None:
                    try:
                        if plant_diag.has_critical_sensor_fault(cid) is True:
                            continue
                    except AttributeError:
                        pass
                if split_mgr is not None:
                    try:
                        if split_mgr.should_suppress_hydronic_demand(cid) is True:
                            continue
                    except AttributeError:
                        pass
                if _get_hvac_mode_str(ent).lower() in ("off", "cool"):
                    continue
                try:
                    c_t = ent.current_temperature
                    t_t = ent.target_temperature
                except AttributeError:
                    c_t = t_t = None
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

        if self.boiler_backend is not None:
            res_gas = self.boiler_backend.async_update(cmd.gas_demand, agg.peak_zone, frost_emergency)
            if inspect.isawaitable(res_gas):
                await res_gas

        if hp_backend is not None:
            if hp_enabled:
                res_hp = hp_backend.async_update(cmd.hp_demand, agg.peak_zone, frost_emergency, hvac_mode=HVAC_MODE_HEAT)
                if inspect.isawaitable(res_hp):
                    await res_hp
            elif getattr(hp_backend, "_current_running_state", False) is True and callable(
                getattr(hp_backend, "async_emergency_off", None)
            ):
                res_hp_off = hp_backend.async_emergency_off()
                if inspect.isawaitable(res_hp_off):
                    await res_hp_off
