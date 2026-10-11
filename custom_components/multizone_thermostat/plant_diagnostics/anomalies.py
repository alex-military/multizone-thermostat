"""Zone and Boiler Anomaly Evaluation rules."""
from __future__ import annotations

import logging
import time
from typing import Any
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import (
    ANOMALY_NONE,
    ANOMALY_VALVE_STUCK_CLOSED,
    ANOMALY_GHOST_HEATING,
    ANOMALY_STALE_SENSOR,
    ANOMALY_OVERSHOOT,
    ANOMALY_LOW_BATTERY,
    ANOMALY_SENSOR_FAULT,
    ANOMALY_SENSOR_TIMEOUT,
    ANOMALY_LABELS,
)

_LOGGER = logging.getLogger(__name__)

def get_battery_level(hass: HomeAssistant, entity_id: str) -> int | None:
    """Find battery level for an entity (attributes, device registry, or related sensor)."""
    if not entity_id:
        return None
        
    st = hass.states.get(entity_id)
    if not st:
        return None
        
    # 1. Check direct attributes on the entity
    for attr in ("battery", "battery_level", "battery_percent"):
        val = st.attributes.get(attr)
        if val is not None:
            try:
                return int(round(float(val)))
            except (ValueError, TypeError):
                pass
                
    # 2. Lookup related battery sensor by device_id in entity registry
    ent_reg = None
    try:
        ent_reg = er.async_get(hass)
    except Exception:
        ent_reg = hass.data.get("entity_registry")
        
    if ent_reg:
        entry = ent_reg.async_get(entity_id)
        if entry and entry.device_id:
            for ent in er.async_entries_for_device(ent_reg, entry.device_id):
                if ent.domain == "sensor":
                    # Check original_device_class, device_class or entity_id naming
                    is_battery = (
                        getattr(ent, "device_class", None) == "battery"
                        or getattr(ent, "original_device_class", None) == "battery"
                        or "battery" in ent.entity_id
                        or getattr(ent, "translation_key", None) == "battery"
                    )
                    if is_battery:
                        bat_st = hass.states.get(ent.entity_id)
                        if bat_st and bat_st.state not in ("unavailable", "unknown"):
                            try:
                                return int(round(float(bat_st.state)))
                            except (ValueError, TypeError):
                                pass

    # 3. Name-based matching heuristic (common in Zigbee2MQTT / ZHA)
    # E.g. sensor.camera_matrimoniale_temperature -> sensor.camera_matrimoniale_battery
    clean_id = entity_id.split(".", 1)[-1] if "." in entity_id else entity_id
    for suffix in ("_temperature", "_temp", "_current_temperature"):
        if clean_id.endswith(suffix):
            clean_id = clean_id[:-len(suffix)]
            break
            
    candidate_prefixes = [f"sensor.{clean_id}_battery", f"sensor.{clean_id}_battery_level"]
    for cand in candidate_prefixes:
        cand_st = hass.states.get(cand)
        if cand_st and cand_st.state not in ("unavailable", "unknown"):
            try:
                return int(round(float(cand_st.state)))
            except (ValueError, TypeError):
                pass

    return None

def get_zone_battery_level(coordinator: Any, hass: HomeAssistant, climate_id: str) -> int | None:
    """Find lowest battery level for a zone (checking external temp sensor, then TRVs)."""
    zone = coordinator.zone_manager.get_zone(climate_id)
    if not zone:
        return None
        
    batteries = []
    
    # Check external sensor
    sensor_id = zone.get("temp_sensor")
    if sensor_id:
        bat = get_battery_level(hass, sensor_id)
        if bat is not None:
            batteries.append(bat)
            
    # Check TRVs in the zone
    for trv in (zone.get("climate_entities") or []):
        bat = get_battery_level(hass, trv)
        if bat is not None:
            batteries.append(bat)
            
    if batteries:
        return min(batteries)
    return None

def get_opentherm_diagnostics(coordinator: Any, hass: HomeAssistant) -> dict[str, Any]:
    """Auto-discover and read OpenTherm telemetry, registers and error flags."""
    ot_entity = getattr(coordinator, "opentherm_entity", None)
    if not ot_entity:
        return {"enabled": False}

    result: dict[str, Any] = {
        "enabled": True,
        "entity_id": ot_entity,
        "water_pressure": None,
        "return_temperature": None,
        "flow_temperature": None,
        "flame_active": None,
        "modulation_level": None,
        "fault_code": None,
        "fault_active": False,
        "dhw_active": False,
        "condensing_optimal": None,
    }

    # 1. Inspect direct attributes of opentherm_entity
    st = hass.states.get(ot_entity)
    if st and st.attributes:
        attrs = st.attributes
        # Current / Flow temp
        for k in ("current_temperature", "flow_temperature", "boiler_temperature", "ch_flow_temperature"):
            if k in attrs and attrs[k] is not None:
                try:
                    result["flow_temperature"] = float(attrs[k])
                    break
                except (ValueError, TypeError):
                    pass

        # Return temp
        for k in ("return_temperature", "return_water_temperature", "ch_return_temperature", "boiler_return_temperature"):
            if k in attrs and attrs[k] is not None:
                try:
                    result["return_temperature"] = float(attrs[k])
                    break
                except (ValueError, TypeError):
                    pass

        # Water Pressure
        for k in ("pressure", "water_pressure", "ch_water_pressure", "boiler_pressure"):
            if k in attrs and attrs[k] is not None:
                try:
                    result["water_pressure"] = round(float(attrs[k]), 2)
                    break
                except (ValueError, TypeError):
                    pass

        # Modulation level
        for k in ("modulation", "modulation_level", "relative_modulation_level", "relative_mod_level"):
            if k in attrs and attrs[k] is not None:
                try:
                    result["modulation_level"] = round(float(attrs[k]), 1)
                    break
                except (ValueError, TypeError):
                    pass

        # Flame status
        for k in ("flame", "flame_active", "flame_on", "flame_status"):
            if k in attrs:
                v = attrs[k]
                result["flame_active"] = bool(v) if not isinstance(v, str) else v.lower() in ("true", "on", "1")
                break

        # Fault
        for k in ("fault", "fault_code", "oem_fault_code", "error_code", "fault_flags"):
            if k in attrs and attrs[k] not in (None, 0, "0", "", "none", "ok", False):
                result["fault_code"] = str(attrs[k])
                result["fault_active"] = True
                break

        # DHW Active
        for k in ("dhw_active", "dhw_state", "dhw_mode", "hot_water_active"):
            if k in attrs:
                v = attrs[k]
                result["dhw_active"] = bool(v) if not isinstance(v, str) else v.lower() in ("true", "on", "1")
                break

    # 2. Check Device Registry for companion sensor entities (OpenTherm Gateway / ESPHome)
    try:
        ent_reg = er.async_get(hass)
    except Exception:
        ent_reg = hass.data.get("entity_registry")

    if ent_reg:
        entry = ent_reg.async_get(ot_entity)
        if entry and entry.device_id:
            for ent in er.async_entries_for_device(ent_reg, entry.device_id):
                if ent.entity_id != ot_entity:
                    s_st = hass.states.get(ent.entity_id)
                    if not s_st or s_st.state in ("unavailable", "unknown"):
                        continue
                    
                    eid = ent.entity_id.lower()
                    dev_cls = getattr(ent, "original_device_class", None) or getattr(ent, "device_class", None)
                    
                    # Pressure sensor
                    if (dev_cls == "pressure" or "pressure" in eid) and result["water_pressure"] is None:
                        try:
                            result["water_pressure"] = round(float(s_st.state), 2)
                        except (ValueError, TypeError):
                            pass

                    # Return temp sensor
                    if ("return" in eid and ("temp" in eid or dev_cls == "temperature")) and result["return_temperature"] is None:
                        try:
                            result["return_temperature"] = round(float(s_st.state), 1)
                        except (ValueError, TypeError):
                            pass

                    # Modulation
                    if ("modulation" in eid or "mod_level" in eid) and result["modulation_level"] is None:
                        try:
                            result["modulation_level"] = round(float(s_st.state), 1)
                        except (ValueError, TypeError):
                            pass

                    # Flame
                    if ("flame" in eid) and result["flame_active"] is None:
                        result["flame_active"] = s_st.state.lower() in ("on", "true", "1")

                    # Fault / Error
                    if ("fault" in eid or "error" in eid):
                        if s_st.state.lower() not in ("off", "none", "0", "ok", "false", "unavailable"):
                            result["fault_active"] = True
                            result["fault_code"] = str(s_st.state)

                    # DHW Active
                    if ("dhw" in eid or "hot_water" in eid):
                        if s_st.state.lower() in ("on", "true", "1"):
                            result["dhw_active"] = True

    # Compute condensing optimization metric (condenses when return water < 54°C)
    if result["return_temperature"] is not None:
        result["condensing_optimal"] = result["return_temperature"] < 54.0

    return result

def evaluate_zone_anomalies(
    coordinator: Any, 
    hass: HomeAssistant, 
    climate_id: str, 
    state: dict[str, Any], 
    boiler_on: bool
) -> tuple[str, str]:
    """
    Evaluate if a zone exhibits mechanical, hydraulic or sensor anomalies.
    Updates the `state` dict in-place and returns (anomaly_type, human_readable_description).
    """
    try:
        now_wall = time.time()
        now_mono = time.monotonic()
        st = hass.states.get(climate_id)
        if not st:
            return ANOMALY_NONE, "Zona non pronta"

        current_temp = st.attributes.get("current_temperature")
        target_temp = st.attributes.get("temperature")
        demand = coordinator.get_zone_demand(climate_id)

        if current_temp is None:
            return ANOMALY_NONE, "In attesa lettura temperatura"

        current_temp = float(current_temp)

        # 0.a Battery Check (Main Sensor)
        zone = coordinator.zone_manager.get_zone(climate_id)
        if zone:
            sensor_id = zone.get("temp_sensor")
            if sensor_id:
                bat = get_battery_level(hass, sensor_id)
                if bat is not None and bat <= 10:
                    state["active_anomaly"] = ANOMALY_LOW_BATTERY
                    state["anomaly_details"] = f"Batteria sensore {sensor_id} in esaurimento ({bat}%)"
                    return ANOMALY_LOW_BATTERY, state["anomaly_details"]

        # 0.b Sanity Check (Plausibility)
        # Only physically impossible values are flagged: cold rooms (garage,
        # unheated houses) legitimately read below 4°C.
        is_insane = False
        if current_temp < -30.0 or current_temp > 60.0:
            is_insane = True
        if state["last_temp_seen"] is not None and state["last_temp_time"] is not None:
            if abs(state["last_temp_seen"] - current_temp) > 4.0 and (now_mono - state["last_temp_time"]) < 600:
                is_insane = True
                
        if is_insane:
            state["active_anomaly"] = ANOMALY_SENSOR_FAULT
            state["anomaly_details"] = f"Lettura temperatura non plausibile o sbalzo anomalo ({current_temp}°C)"
            return ANOMALY_SENSOR_FAULT, state["anomaly_details"]

        # 0.c Watchdog Sensor Timeout Check
        state["fallback_ok"] = False
        timeout_min = zone.get("sensor_timeout_min", 60) if zone else 60
        sensor_entity = zone.get("temp_sensor") if zone else None
        if sensor_entity:
            s_state = hass.states.get(sensor_entity)
            if s_state:
                s_reported = s_state.last_reported if hasattr(s_state, "last_reported") else s_state.last_updated
                if s_reported:
                    elapsed_sec = now_wall - s_reported.timestamp()
                    if elapsed_sec > (timeout_min * 60):
                        # Degraded (not critical) if a valid TRV temperature is available as fallback
                        for trv in (zone.get("climate_entities") or []):
                            trv_st = hass.states.get(trv)
                            if trv_st and trv_st.attributes.get("current_temperature") is not None:
                                state["fallback_ok"] = True
                                break
                        state["active_anomaly"] = ANOMALY_SENSOR_TIMEOUT
                        suffix = " - fallback sui TRV attivo" if state["fallback_ok"] else ""
                        state["anomaly_details"] = f"Sonda {sensor_entity} non aggiornata da oltre {int(elapsed_sec / 60)} min (limite: {timeout_min} min){suffix}"
                        return ANOMALY_SENSOR_TIMEOUT, state["anomaly_details"]

        # If the zone is Bypassed, it is intentionally excluded from heating
        zone_mode = coordinator.get_zone_mode(climate_id)
        if zone_mode == "bypass":
            state["active_anomaly"] = ANOMALY_NONE
            state["anomaly_details"] = "Zona bypassata (Esclusa dal riscaldamento)"
            return ANOMALY_NONE, state["anomaly_details"]

        # 1. Staleness Check: Has the temperature sensor not updated in > 2 hours?
        if state["last_temp_seen"] is None or state["last_temp_seen"] != current_temp:
            state["last_temp_seen"] = current_temp
            state["last_temp_time"] = now_mono
            
        if state["last_temp_time"] is not None and (now_mono - state["last_temp_time"]) > 7200:
            # Same exact float value for > 2 hours
            state["active_anomaly"] = ANOMALY_STALE_SENSOR
            state["anomaly_details"] = ANOMALY_LABELS[ANOMALY_STALE_SENSOR]
            return ANOMALY_STALE_SENSOR, state["anomaly_details"]

        # Update last heating time
        if boiler_on and demand > 0.0:
            state["last_heating_time"] = now_mono

        # 2. Overshoot Check: Only if heating was active recently (within the last 2 ore)
        # If the heating wasn't active recently, warm room temperature is natural ambient/solar heat.
        heated_recently = state["last_heating_time"] is not None and (now_mono - state["last_heating_time"]) < 7200
        if heated_recently and target_temp is not None and current_temp > (float(target_temp) + 1.5):
            state["active_anomaly"] = ANOMALY_OVERSHOOT
            state["anomaly_details"] = f"Temperatura attuale ({current_temp}°C) supera il target ({target_temp}°C) di oltre 1.5°C per calore residuo"
            return ANOMALY_OVERSHOOT, state["anomaly_details"]

        # 3. Stuck Closed Valve: Demand == 100% for > 75 min, but temperature did not rise >= 0.2°C
        if demand >= 99.0 and boiler_on:
            if state["high_demand_start_time"] is None:
                state["high_demand_start_time"] = now_mono
                state["high_demand_start_temp"] = current_temp
            elif (now_mono - state["high_demand_start_time"]) > 4500:  # 75 minutes
                start_t = state["high_demand_start_temp"]
                if start_t is not None and (current_temp - start_t) < 0.2:
                    state["active_anomaly"] = ANOMALY_VALVE_STUCK_CLOSED
                    state["anomaly_details"] = f"Riscaldamento attivo al 100% da oltre 75 min ma la temperatura non sale ({start_t}°C → {current_temp}°C)"
                    return ANOMALY_VALVE_STUCK_CLOSED, state["anomaly_details"]
        elif demand < 80.0:
            # Reset stuck-closed tracker if demand dropped below 80%
            state["high_demand_start_time"] = None
            state["high_demand_start_temp"] = None

        # Check if passive heat is allowed (via dynamic switch or zone config)
        allow_passive_heat = coordinator.zone_manager.is_passive_heat_allowed(climate_id)

        # 4. Ghost Heating / Stuck Open: Zone is OFF or demand is 0, but room temp rose > 0.8°C while boiler running
        if demand <= 0.0 and boiler_on:
            if allow_passive_heat:
                # Passive heat allowed (fan coil without shut-off valve, open mezzanine, etc.)
                state["ghost_heat_start_temp"] = None
            elif state["ghost_heat_start_temp"] is None:
                state["ghost_heat_start_temp"] = current_temp
            elif (current_temp - state["ghost_heat_start_temp"]) > 0.8:
                state["active_anomaly"] = ANOMALY_GHOST_HEATING
                state["anomaly_details"] = f"Temperatura salita da {state['ghost_heat_start_temp']}°C a {current_temp}°C con zona a 0% richiesta"
                return ANOMALY_GHOST_HEATING, state["anomaly_details"]
        else:
            state["ghost_heat_start_temp"] = None

        # No active anomaly
        state["active_anomaly"] = ANOMALY_NONE
        state["anomaly_details"] = ANOMALY_LABELS[ANOMALY_NONE]
        return ANOMALY_NONE, state["anomaly_details"]

    except Exception as err:
        _LOGGER.debug("Error in evaluate_zone_anomalies for %s: %s", climate_id, err)
        return ANOMALY_NONE, "Errore valutazione"
