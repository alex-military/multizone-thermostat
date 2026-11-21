"""Multizone Thermostat integration setup."""
from __future__ import annotations

from collections.abc import Mapping
import inspect
import logging
import math
from typing import Any

import voluptuous as vol

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

try:
    from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
except ImportError:
    EVENT_HOMEASSISTANT_STARTED = "homeassistant_started"

from .const import (
    CONF_BOILER_SWITCH,
    CONF_BOILER_MODE,
    CONF_OPENTHERM_ENTITY,
    MODE_RELAY,
    MODE_OPENTHERM,
    CONF_ZONES,
    CONF_ZONE_NAME,
    DOMAIN,
    CONF_ENABLE_GAS_HEATER,
    CONF_ENABLE_HEAT_PUMP,
    CONF_HEAT_PUMP_ENTITY,
    CONF_ZONE_ANTI_SEIZE,
    CONF_ZONE_EMITTER_TYPE,
    DEFAULT_ZONE_EMITTER_TYPE,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    make_zone_entity_id,
    to_celsius,
)
from .coordinator import MultizoneCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["climate", "switch", "number", "select", "time", "sensor", "binary_sensor", "button"]


def _migrate_config_data(
    data: Mapping[str, Any], options: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    """Normalize legacy config entry schemas and populate new release defaults."""
    migrated = False
    new_data = dict(data)
    new_options = dict(options) if options else {}
    config = {**new_data, **new_options}
    zones = [dict(z) for z in list(config.get(CONF_ZONES, []))]

    # 1. Migrate old virtual thermostats to new zones (deduplicated by canonical slug)
    old_vts = new_data.pop("virtual_thermostats", [])
    if not old_vts and "virtual_thermostats" in new_options:
        old_vts = new_options.pop("virtual_thermostats", [])
    if old_vts:
        migrated = True
        existing_zone_ids = {
            make_zone_entity_id(z.get(CONF_ZONE_NAME, ""))
            for z in zones
            if isinstance(z, Mapping) and z.get(CONF_ZONE_NAME)
        }
        for vt in old_vts:
            vt_name = vt.get("name", "Unknown VT")
            vt_cid = make_zone_entity_id(vt_name)
            if vt_cid in existing_zone_ids:
                continue
            existing_zone_ids.add(vt_cid)
            vt_zone = {
                "name": vt_name,
                "climate_entities": [],
                "switch_entities": [vt.get("heater_switch")] if vt.get("heater_switch") else [],
                "temp_sensor": vt.get("temperature_sensor"),
                "target_temperature": vt.get("target_temperature", 20.0),
                "trv_preset_sync": False,
                CONF_ZONE_ANTI_SEIZE: True,
            }
            zones.append(vt_zone)

    # 2. Migrate old zones and populate per-zone defaults
    for zone in zones:
        if "climate_entity" in zone:
            migrated = True
            climate = zone.pop("climate_entity")
            zone["climate_entities"] = [climate] if isinstance(climate, str) and climate else []
            zone["switch_entities"] = []
            zone["target_temperature"] = 20.0
        if CONF_ZONE_ANTI_SEIZE not in zone:
            zone[CONF_ZONE_ANTI_SEIZE] = True
            migrated = True
        if CONF_ZONE_EMITTER_TYPE not in zone:
            zone[CONF_ZONE_EMITTER_TYPE] = "fancoil" if zone.get("is_fancoil") else DEFAULT_ZONE_EMITTER_TYPE
            migrated = True

    # 3. Migrate top-level defaults for pre-OpenTherm / pre-Hybrid installations
    if CONF_BOILER_MODE not in new_data and CONF_BOILER_MODE not in new_options:
        new_data[CONF_BOILER_MODE] = MODE_RELAY
        migrated = True
    if CONF_ENABLE_GAS_HEATER not in new_data and CONF_ENABLE_GAS_HEATER not in new_options:
        new_data[CONF_ENABLE_GAS_HEATER] = True
        migrated = True
    if CONF_ENABLE_HEAT_PUMP not in new_data and CONF_ENABLE_HEAT_PUMP not in new_options:
        new_data[CONF_ENABLE_HEAT_PUMP] = False
        migrated = True

    if migrated:
        new_data[CONF_ZONES] = zones
        if CONF_ZONES in new_options:
            new_options[CONF_ZONES] = zones

    return new_data, new_options, migrated


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config entries to version 2."""
    version = getattr(config_entry, "version", 1)
    if isinstance(version, int) and version >= 2:
        return True
    _LOGGER.info("Migrating Multizone Thermostat config entry from version %s to 2", version)
    new_data, new_options, _ = _migrate_config_data(config_entry.data, config_entry.options or {})
    try:
        hass.config_entries.async_update_entry(
            config_entry, data=new_data, options=new_options, version=2
        )
    except TypeError:
        config_entry.version = 2
        hass.config_entries.async_update_entry(
            config_entry, data=new_data, options=new_options
        )
    return True


async def _async_refresh_orchestrator(orch: Any) -> None:
    """Refresh plant orchestrator using public async_refresh (with mock fallback)."""
    if orch is None:
        return
    refresh_fn = getattr(orch, "async_refresh", None)
    if inspect.iscoroutinefunction(refresh_fn):
        await refresh_fn()
        return
    legacy_fn = getattr(orch, "_async_update_boiler", None)
    if inspect.iscoroutinefunction(legacy_fn):
        await legacy_fn()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Multizone Thermostat from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    config = {**entry.data, **entry.options}
    enable_gas = config.get(CONF_ENABLE_GAS_HEATER, True)
    enable_hp = config.get(CONF_ENABLE_HEAT_PUMP, False)
    boiler_mode = config.get(CONF_BOILER_MODE, MODE_RELAY)
    boiler_switch = config.get(CONF_BOILER_SWITCH)
    opentherm_entity = config.get(CONF_OPENTHERM_ENTITY)
    hp_entity = config.get(CONF_HEAT_PUMP_ENTITY)
    zones = [dict(z) for z in list(config.get(CONF_ZONES, []))]

    # Validate primary entity exists
    if enable_gas and boiler_mode == MODE_RELAY and boiler_switch:
        boiler_state = hass.states.get(boiler_switch)
        if boiler_state is None:
            if getattr(hass, "is_running", True):
                _LOGGER.warning(
                    "Boiler switch '%s' not found. The integration will load but boiler "
                    "control may not work until the entity is available.",
                    boiler_switch,
                )
            else:
                _LOGGER.debug(
                    "Boiler switch '%s' not yet available during Home Assistant startup; "
                    "will recheck once Home Assistant starts.",
                    boiler_switch,
                )
                if hasattr(hass, "bus") and hasattr(hass.bus, "async_listen_once"):
                    async def _check_boiler_started(_event) -> None:
                        if hass.states.get(boiler_switch) is None:
                            _LOGGER.warning(
                                "Boiler switch '%s' not found. The integration will load but boiler "
                                "control may not work until the entity is available.",
                                boiler_switch,
                            )
                    unsub = hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _check_boiler_started)
                    if callable(unsub) and callable(getattr(entry, "async_on_unload", None)):
                        entry.async_on_unload(unsub)
    elif enable_gas and boiler_mode == MODE_OPENTHERM and opentherm_entity:
        ot_state = hass.states.get(opentherm_entity)
        if ot_state is None:
            if getattr(hass, "is_running", True):
                _LOGGER.warning(
                    "OpenTherm entity '%s' not found. The integration will load but modulating "
                    "control may not work until the entity is available.",
                    opentherm_entity,
                )
            else:
                _LOGGER.debug(
                    "OpenTherm entity '%s' not yet available during Home Assistant startup; "
                    "will recheck once Home Assistant starts.",
                    opentherm_entity,
                )
                if hasattr(hass, "bus") and hasattr(hass.bus, "async_listen_once"):
                    async def _check_ot_started(_event) -> None:
                        if hass.states.get(opentherm_entity) is None:
                            _LOGGER.warning(
                                "OpenTherm entity '%s' not found. The integration will load but modulating "
                                "control may not work until the entity is available.",
                                opentherm_entity,
                            )
                    unsub = hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _check_ot_started)
                    if callable(unsub) and callable(getattr(entry, "async_on_unload", None)):
                        entry.async_on_unload(unsub)
    if enable_hp and hp_entity:
        hp_state = hass.states.get(hp_entity)
        if hp_state is None:
            _LOGGER.debug("Heat pump entity '%s' not yet available during startup.", hp_entity)

    # Migrate old config format to new Hybrid Zones format
    new_data, new_options, migrated = _migrate_config_data(entry.data, entry.options or {})
    if migrated:
        _LOGGER.info("Migrating Multizone Thermostat config to new Hybrid Zones format.")
        if CONF_ZONES in new_options:
            hass.config_entries.async_update_entry(entry, data=new_data, options=new_options)
        else:
            hass.config_entries.async_update_entry(entry, data=new_data)


    from homeassistant.helpers import device_registry as dr
    device_registry = dr.async_get(hass)
    master_device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name="Master Control",
        manufacturer="Custom Integration",
        model="Master Control",
    )

    # Create coordinator
    coordinator = MultizoneCoordinator(
        hass=hass,
        entry=entry,
    )
    coordinator.master_device_id = master_device.id

    # Load persistent data
    await coordinator.async_load_storage()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
    }

    # Set up platforms first so entities are registered before listeners/calendar fire
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Safely clean up legacy empty devices (_zones, _virtual_thermostats, _zone_modes)
    try:
        from homeassistant.helpers import entity_registry as er
        entity_registry = er.async_get(hass)
        legacy_suffixes = ["_zones", "_virtual_thermostats", "_zone_modes"]
        for suffix in legacy_suffixes:
            dev = device_registry.async_get_device(identifiers={(DOMAIN, f"{entry.entry_id}{suffix}")})
            if dev is not None:
                entries = er.async_entries_for_device(entity_registry, dev.id)
                if not entries:
                    _LOGGER.info("Cleaning up legacy empty device: %s (%s)", dev.name, dev.id)
                    device_registry.async_remove_device(dev.id)
    except Exception as cleanup_err:
        _LOGGER.debug("Legacy device cleanup skipped: %s", cleanup_err)

    # Set up state listeners
    coordinator.async_setup_listeners()

    # Proactively evaluate zone PID demands and aggregate immediately after setup
    # so Master Demand does not remain at 0% until the first manual change or periodic tick.
    orch = getattr(coordinator, "plant_orchestrator", None)
    if orch is not None:
        try:
            await _async_refresh_orchestrator(orch)
        except Exception as init_err:
            _LOGGER.debug("Initial boiler demand sync skipped: %s", init_err)

    # Register static path for Lovelace custom card once per HA instance
    import os
    www_path = hass.config.path("custom_components/multizone_thermostat/www")
    if not hass.data[DOMAIN].get("_static_path_registered") and await hass.async_add_executor_job(os.path.isdir, www_path):
        await hass.http.async_register_static_paths([
            StaticPathConfig(
                url_path="/multizone_thermostat_card",
                path=www_path,
                cache_headers=False,
            )
        ])
        hass.data[DOMAIN]["_static_path_registered"] = True

    # Register Lovelace custom card resource automatically
    try:
        if "lovelace" in hass.data:
            resources = hass.data["lovelace"].resources
            if hasattr(resources, "async_get_info") and hasattr(resources, "async_create_item"):
                await resources.async_get_info()
                
                from homeassistant.loader import async_get_integration
                integration = await async_get_integration(hass, DOMAIN)
                version = integration.version if integration else "unknown"
                
                js_path = os.path.join(www_path, "multizone-thermostat-card-v24.js")
                def _get_js_mtime(path: str) -> int:
                    return int(os.path.getmtime(path)) if os.path.exists(path) else 0
                mtime = await hass.async_add_executor_job(_get_js_mtime, js_path)
                base_url = "/multizone_thermostat_card/multizone-thermostat-card-v24.js"
                url = f"{base_url}?v={version}.{mtime}"
                
                existing_item = None
                for item in list(resources.async_items()):
                    item_url = item.get("url", "")
                    if "multizone-thermostat-card" in item_url:
                        if existing_item is None and item_url.startswith(base_url):
                            existing_item = item
                        else:
                            # Remove duplicate or legacy resources
                            if hasattr(resources, "async_delete_item"):
                                await resources.async_delete_item(item.get("id"))
                        
                if not existing_item:
                    await resources.async_create_item({
                        "res_type": "module",
                        "url": url,
                    })
                elif existing_item.get("url") != url:
                    await resources.async_update_item(existing_item.get("id"), {
                        "url": url,
                    })
    except Exception as err:
        _LOGGER.warning("Could not register or update Lovelace resource: %s", err)

    # Register update listener for options changes
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    # Register integration services
    await _async_register_services(hass)

    _LOGGER.info(
        "Multizone Thermostat loaded: mode=%s, entity=%s, zones=%d",
        boiler_mode,
        boiler_switch or opentherm_entity,
        len(zones),
    )
    return True


def _get_active_coordinators(hass: HomeAssistant) -> list[MultizoneCoordinator]:
    """Retrieve all active Multizone coordinator instances."""
    domain_data = hass.data.get(DOMAIN, {})
    coordinators: list[MultizoneCoordinator] = []
    if isinstance(domain_data, dict):
        for val in domain_data.values():
            if isinstance(val, dict) and "coordinator" in val:
                coordinators.append(val["coordinator"])
    return coordinators


def _extract_entity_ids(data: Mapping[str, Any]) -> list[str]:
    """Extract and validate a list of entity IDs from service call data."""
    raw = data.get("climate_entity")
    if raw is None:
        raw = data.get("entity_id")
    if raw is None:
        raise vol.Invalid("Missing required parameter: climate_entity or entity_id")
    if isinstance(raw, str):
        v = raw.strip()
        if not v:
            raise vol.Invalid("climate_entity or entity_id cannot be empty")
        return [v]
    if isinstance(raw, (list, tuple, set)):
        result = [str(x).strip() for x in raw if isinstance(x, str) and str(x).strip()]
        if not result:
            raise vol.Invalid("climate_entity or entity_id list contained no valid entity IDs")
        return result
    raise vol.Invalid(f"Invalid climate_entity or entity_id type: {type(raw)}")


def _validate_has_target_entity(data: Mapping[str, Any]) -> Mapping[str, Any]:
    """Validate that at least one of climate_entity or entity_id is specified."""
    if not data.get("climate_entity") and not data.get("entity_id"):
        raise vol.Invalid("Must specify either 'climate_entity' or 'entity_id'")
    return data


def _validate_has_profile_id(data: Mapping[str, Any]) -> Mapping[str, Any]:
    """Validate that profile_id is supplied either directly or inside a nested profile dict."""
    if data.get("profile_id"):
        return data
    profile = data.get("profile")
    if isinstance(profile, Mapping) and (profile.get("profile_id") or profile.get("id")):
        return data
    raise vol.Invalid("Must specify 'profile_id' directly or inside 'profile'")


def _validate_has_operation_mode(data: Mapping[str, Any]) -> Mapping[str, Any]:
    """Validate that at least one of operation_mode or hvac_mode is specified."""
    if not data.get("operation_mode") and not data.get("hvac_mode"):
        raise vol.Invalid("Must specify either 'operation_mode' or 'hvac_mode'")
    return data


def _finite_float(val: Any) -> float:
    """Validate that a value can be coerced to a finite float."""
    try:
        f = float(val)
    except (ValueError, TypeError):
        raise vol.Invalid(f"Value {val} cannot be converted to float")
    if not math.isfinite(f):
        raise vol.Invalid(f"Value {val} must be finite")
    return f


SERVICE_SAVE_SCHEDULE_PROFILE_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Optional("profile_id"): str,
            vol.Optional("name"): str,
            vol.Optional("baseline_preset"): vol.In(["comfort", "eco", "sleep", "away"]),
            vol.Optional("days"): dict,
            vol.Optional("profile"): dict,
        }
    ),
    _validate_has_profile_id,
)

SERVICE_ACTIVATE_SCHEDULE_PROFILE_SCHEMA = vol.Schema(
    {
        vol.Required("profile_id"): str,
        vol.Optional("expires_at"): vol.Any(None, str),
        vol.Optional("fallback_profile", default="standard"): str,
    }
)

SERVICE_DUPLICATE_SCHEDULE_PROFILE_SCHEMA = vol.Schema(
    {
        vol.Required("source_profile_id"): str,
        vol.Required("target_profile_id"): str,
        vol.Optional("target_name"): vol.Any(None, str),
    }
)

SERVICE_SET_SMART_RETURN_SCHEMA = vol.Schema(
    {
        vol.Required("arrival_time"): str,
        vol.Optional("preset", default="comfort"): vol.In(["comfort", "eco", "sleep", "away"]),
        vol.Optional("zones"): vol.Any(None, [str]),
    }
)

SERVICE_CANCEL_SMART_RETURN_SCHEMA = vol.Schema({})

SERVICE_CLEAR_ZONE_OVERRIDE_SCHEMA = vol.Schema(
    {
        vol.Optional("entity_id"): vol.Any(None, str),
    }
)

SERVICE_SET_PRESET_TEMPERATURE_SCHEMA = vol.Schema(
    {
        vol.Required("preset"): vol.In(["comfort", "eco", "sleep", "away", "manual"]),
        vol.Required("entity_id"): str,
        vol.Required("temperature"): vol.All(_finite_float, vol.Range(min=5.0, max=95.0)),
        vol.Optional("hvac_mode"): vol.Any(None, vol.In(["heat", "cool"])),
    }
)

SERVICE_SET_MASTER_OPERATION_MODE_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Optional("operation_mode"): vol.In([HVAC_MODE_HEAT, HVAC_MODE_COOL]),
            vol.Optional("hvac_mode"): vol.In([HVAC_MODE_HEAT, HVAC_MODE_COOL]),
        }
    ),
    _validate_has_operation_mode,
)

SERVICE_SET_PID_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Optional("climate_entity"): vol.Any(str, [str]),
            vol.Optional("entity_id"): vol.Any(str, [str]),
            vol.Optional("kp"): vol.All(_finite_float, vol.Range(min=0.1, max=500.0)),
            vol.Optional("ki"): vol.All(_finite_float, vol.Range(min=0.0, max=10.0)),
            vol.Optional("kd"): vol.All(_finite_float, vol.Range(min=0.0, max=50000.0)),
            vol.Optional("lock_parameter"): vol.In(["Kp", "Ki", "Kd", "kp", "ki", "kd", "all", "ALL"]),
            vol.Optional("unlock"): bool,
            vol.Optional("seed_autotuner"): bool,
            vol.Optional("mode"): vol.In(["heat", "cool"]),
        }
    ),
    _validate_has_target_entity,
)

SERVICE_RESET_AUTOTUNE_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Optional("climate_entity"): vol.Any(str, [str]),
            vol.Optional("entity_id"): vol.Any(str, [str]),
            vol.Optional("keep_manual_overrides"): bool,
            vol.Optional("mode"): vol.In(["heat", "cool"]),
        }
    ),
    _validate_has_target_entity,
)


async def _async_register_services(hass: HomeAssistant) -> None:
    """Register all Phase 6 schedule and profile services."""
    if hass.data[DOMAIN].get("_services_registered"):
        return

    from homeassistant.core import ServiceCall

    async def handle_save_schedule_profile(call: ServiceCall) -> None:
        profile_dict = call.data.get("profile") or {}
        if not isinstance(profile_dict, dict):
            profile_dict = {}
        profile_id = call.data.get("profile_id") or profile_dict.get("profile_id") or profile_dict.get("id")
        if not profile_id:
            _LOGGER.error("Cannot save schedule profile without profile_id")
            return
        profile_data = {
            "name": call.data.get("name") or profile_dict.get("name") or profile_id.capitalize(),
            "baseline_preset": call.data.get("baseline_preset") or profile_dict.get("baseline_preset") or "eco",
            "days": call.data.get("days") if call.data.get("days") is not None else profile_dict.get("days", {}),
        }
        for coord in _get_active_coordinators(hass):
            if hasattr(coord, "schedule_manager"):
                await coord.schedule_manager.async_save_profile(profile_id, profile_data)

    async def handle_activate_schedule_profile(call: ServiceCall) -> None:
        profile_id = call.data["profile_id"]
        expires_at = call.data.get("expires_at")
        fallback_profile = call.data.get("fallback_profile", "standard")
        for coord in _get_active_coordinators(hass):
            if hasattr(coord, "schedule_manager"):
                await coord.schedule_manager.async_activate_profile(
                    profile_id=profile_id,
                    expires_at=expires_at,
                    fallback_profile=fallback_profile,
                )

    async def handle_duplicate_schedule_profile(call: ServiceCall) -> None:
        source_id = call.data["source_profile_id"]
        target_id = call.data["target_profile_id"]
        target_name = call.data.get("target_name")
        for coord in _get_active_coordinators(hass):
            if hasattr(coord, "schedule_manager"):
                await coord.schedule_manager.async_duplicate_profile(
                    source_id=source_id,
                    target_id=target_id,
                    target_name=target_name,
                )

    async def handle_set_smart_return(call: ServiceCall) -> None:
        arrival_time = call.data["arrival_time"]
        preset = call.data.get("preset", "comfort")
        zones = call.data.get("zones")
        for coord in _get_active_coordinators(hass):
            if hasattr(coord, "schedule_manager"):
                await coord.schedule_manager.async_set_smart_return(
                    arrival_time=arrival_time,
                    preset=preset,
                    zones=zones,
                )

    async def handle_cancel_smart_return(call: ServiceCall) -> None:
        for coord in _get_active_coordinators(hass):
            if hasattr(coord, "schedule_manager"):
                await coord.schedule_manager.async_cancel_smart_return()

    async def handle_clear_zone_override(call: ServiceCall) -> None:
        entity_id = call.data.get("entity_id")
        for coord in _get_active_coordinators(hass):
            if hasattr(coord, "schedule_manager"):
                await coord.schedule_manager.async_clear_manual_override(entity_id)

    async def handle_set_preset_temperature(call: ServiceCall) -> None:
        preset = call.data["preset"]
        entity_id = call.data["entity_id"]
        temperature = to_celsius(float(call.data["temperature"]), None, hass)
        hvac_mode = call.data.get("hvac_mode")
        for coord in _get_active_coordinators(hass):
            if hasattr(coord, "zone_manager"):
                coord.zone_manager.update_preset_temperature(preset, entity_id, temperature, hvac_mode=hvac_mode)
            if hasattr(coord, "schedule_manager"):
                await coord.schedule_manager.async_evaluate_schedule()

    async def handle_set_master_operation_mode(call: ServiceCall) -> None:
        mode = call.data.get("operation_mode") or call.data.get("hvac_mode")
        if mode not in (HVAC_MODE_HEAT, HVAC_MODE_COOL):
            _LOGGER.warning("Invalid master operation mode: %s", mode)
            return
        for coord in _get_active_coordinators(hass):
            if hasattr(coord, "async_set_master_hvac_mode"):
                await coord.async_set_master_hvac_mode(mode)

    def _find_zone_name_for_entity(coord: MultizoneCoordinator, climate_entity: str) -> str | None:
        canon = coord.resolve_zone_id(climate_entity) if hasattr(coord, "resolve_zone_id") else climate_entity
        for zone in getattr(coord, "zones", []) or []:
            zname = zone.get(CONF_ZONE_NAME) if isinstance(zone, dict) else None
            if zname and make_zone_entity_id(zname) == canon:
                return zname
        return None

    async def handle_set_pid_parameters(call: ServiceCall) -> None:
        data = dict(call.data) if hasattr(call, "data") and isinstance(call.data, Mapping) else {}
        entity_ids = _extract_entity_ids(data)

        def _val_finite_range(v: Any, name: str, min_v: float, max_v: float) -> float | None:
            if v is None:
                return None
            try:
                f = float(v)
            except (ValueError, TypeError):
                raise vol.Invalid(f"Parameter '{name}' must be a float, got {v!r}")
            if not math.isfinite(f):
                raise vol.Invalid(f"Parameter '{name}' must be finite, got {f}")
            if not (min_v <= f <= max_v):
                raise vol.Invalid(f"Parameter '{name}' must be between {min_v} and {max_v}, got {f}")
            return f

        kp = _val_finite_range(data.get("kp"), "kp", 0.1, 500.0)
        ki = _val_finite_range(data.get("ki"), "ki", 0.0, 10.0)
        kd = _val_finite_range(data.get("kd"), "kd", 0.0, 50000.0)

        lock_param = data.get("lock_parameter")
        if lock_param is not None and lock_param not in ("Kp", "Ki", "Kd", "kp", "ki", "kd", "all", "ALL"):
            raise vol.Invalid(f"Invalid lock_parameter: {lock_param}")

        unlock_arg = data.get("unlock")
        if unlock_arg is not None and not isinstance(unlock_arg, bool):
            raise vol.Invalid(f"Parameter 'unlock' must be a boolean, got {unlock_arg!r}")

        raw_seed = data.get("seed_autotuner")
        if raw_seed is not None and not isinstance(raw_seed, bool):
            raise vol.Invalid(f"Parameter 'seed_autotuner' must be a boolean, got {raw_seed!r}")
        seed_autotuner = bool(raw_seed) if raw_seed is not None else False

        mode_arg = data.get("mode")
        if mode_arg is not None and mode_arg not in ("heat", "cool"):
            raise vol.Invalid(f"Invalid mode: {mode_arg}")

        for coord in _get_active_coordinators(hass):
            zc = getattr(coord, "zone_controller", None)
            if not zc or not hasattr(zc, "async_set_zone_pid"):
                continue
            for climate_entity in entity_ids:
                zname = _find_zone_name_for_entity(coord, climate_entity)
                if not seed_autotuner and unlock_arg is not None and zname and hasattr(coord, "async_set_pid_manual_unlock"):
                    await coord.async_set_pid_manual_unlock(zname, bool(unlock_arg))
                kwargs: dict[str, object] = {
                    "kp": kp,
                    "ki": ki,
                    "kd": kd,
                    "lock_param": lock_param,
                }
                if seed_autotuner:
                    kwargs["seed_autotuner"] = True
                if mode_arg is not None:
                    kwargs["mode"] = mode_arg
                updated = await zc.async_set_zone_pid(climate_entity, **kwargs)
                if updated:
                    if seed_autotuner and zname and hasattr(coord, "async_set_pid_manual_unlock"):
                        eff_track = mode_arg or (
                            "cool"
                            if str(getattr(coord, "master_hvac_mode", "heat")).lower() == "cool"
                            else "heat"
                        )
                        resolved_id = (
                            zc._resolve_zone_id(climate_entity)
                            if hasattr(zc, "_resolve_zone_id")
                            else climate_entity
                        )
                        if eff_track == "cool" and hasattr(zc, "_autotuners_cool"):
                            tuner = zc._autotuners_cool.get(resolved_id)
                        elif hasattr(zc, "_autotuners_heat"):
                            tuner = zc._autotuners_heat.get(resolved_id)
                        elif hasattr(zc, "get_autotuner"):
                            tuner = zc.get_autotuner(climate_entity)
                        else:
                            tuner = None
                        if not getattr(tuner, "manual_overrides", None):
                            await coord.async_set_pid_manual_unlock(zname, False)
                    if hasattr(coord, "async_notify_pid_entities"):
                        coord.async_notify_pid_entities()
                    await _async_refresh_orchestrator(getattr(coord, "plant_orchestrator", None))

    async def handle_reset_autotune(call: ServiceCall) -> None:
        data = dict(call.data) if hasattr(call, "data") and isinstance(call.data, Mapping) else {}
        entity_ids = _extract_entity_ids(data)
        raw_keep = data.get("keep_manual_overrides")
        if raw_keep is not None and not isinstance(raw_keep, bool):
            raise vol.Invalid(f"Parameter 'keep_manual_overrides' must be a boolean, got {raw_keep!r}")
        keep_manual = bool(raw_keep) if raw_keep is not None else False

        mode_arg = data.get("mode")
        if mode_arg is not None and mode_arg not in ("heat", "cool"):
            raise vol.Invalid(f"Invalid mode: {mode_arg}")

        for coord in _get_active_coordinators(hass):
            zc = getattr(coord, "zone_controller", None)
            if not zc or not hasattr(zc, "async_reset_zone_autotuner"):
                continue
            for climate_entity in entity_ids:
                kwargs: dict[str, object] = {"keep_manual_overrides": keep_manual}
                if mode_arg is not None:
                    kwargs["mode"] = mode_arg
                ok = await zc.async_reset_zone_autotuner(climate_entity, **kwargs)
                if ok:
                    zname = _find_zone_name_for_entity(coord, climate_entity)
                    if not keep_manual and zname and hasattr(coord, "async_set_pid_manual_unlock"):
                        await coord.async_set_pid_manual_unlock(zname, False)
                    if hasattr(coord, "async_notify_pid_entities"):
                        coord.async_notify_pid_entities()
                    await _async_refresh_orchestrator(getattr(coord, "plant_orchestrator", None))

    async def handle_restore_autotune(call: ServiceCall) -> None:
        data = dict(call.data) if hasattr(call, "data") and isinstance(call.data, Mapping) else {}
        entity_ids = _extract_entity_ids(data)
        raw_keep = data.get("keep_manual_overrides")
        if raw_keep is not None and not isinstance(raw_keep, bool):
            raise vol.Invalid(f"Parameter 'keep_manual_overrides' must be a boolean, got {raw_keep!r}")
        keep_manual = bool(raw_keep) if raw_keep is not None else False

        mode_arg = data.get("mode")
        if mode_arg is not None and mode_arg not in ("heat", "cool"):
            raise vol.Invalid(f"Invalid mode: {mode_arg}")

        for coord in _get_active_coordinators(hass):
            zc = getattr(coord, "zone_controller", None)
            if not zc or not hasattr(zc, "async_restore_zone_autotuner"):
                continue
            for climate_entity in entity_ids:
                kwargs: dict[str, object] = {"keep_manual_overrides": keep_manual}
                if mode_arg is not None:
                    kwargs["mode"] = mode_arg
                ok = await zc.async_restore_zone_autotuner(climate_entity, **kwargs)
                if ok:
                    zname = _find_zone_name_for_entity(coord, climate_entity)
                    if not keep_manual and zname and hasattr(coord, "async_set_pid_manual_unlock"):
                        await coord.async_set_pid_manual_unlock(zname, False)
                    if hasattr(coord, "async_notify_pid_entities"):
                        coord.async_notify_pid_entities()
                    await _async_refresh_orchestrator(getattr(coord, "plant_orchestrator", None))

    services = {
        "save_schedule_profile": (handle_save_schedule_profile, SERVICE_SAVE_SCHEDULE_PROFILE_SCHEMA),
        "activate_schedule_profile": (handle_activate_schedule_profile, SERVICE_ACTIVATE_SCHEDULE_PROFILE_SCHEMA),
        "duplicate_schedule_profile": (handle_duplicate_schedule_profile, SERVICE_DUPLICATE_SCHEDULE_PROFILE_SCHEMA),
        "set_smart_return": (handle_set_smart_return, SERVICE_SET_SMART_RETURN_SCHEMA),
        "cancel_smart_return": (handle_cancel_smart_return, SERVICE_CANCEL_SMART_RETURN_SCHEMA),
        "clear_zone_override": (handle_clear_zone_override, SERVICE_CLEAR_ZONE_OVERRIDE_SCHEMA),
        "set_preset_temperature": (handle_set_preset_temperature, SERVICE_SET_PRESET_TEMPERATURE_SCHEMA),
        "set_master_operation_mode": (handle_set_master_operation_mode, SERVICE_SET_MASTER_OPERATION_MODE_SCHEMA),
        "set_pid_parameters": (handle_set_pid_parameters, SERVICE_SET_PID_SCHEMA),
        "reset_autotune": (handle_reset_autotune, SERVICE_RESET_AUTOTUNE_SCHEMA),
        "restore_autotune": (handle_restore_autotune, SERVICE_RESET_AUTOTUNE_SCHEMA),
    }

    if hasattr(hass, "services") and hasattr(hass.services, "async_register"):
        for svc_name, (handler, schema) in services.items():
            if schema is not None:
                try:
                    hass.services.async_register(DOMAIN, svc_name, handler, schema=schema)
                except TypeError:
                    hass.services.async_register(DOMAIN, svc_name, handler)
            else:
                hass.services.async_register(DOMAIN, svc_name, handler)

    hass.data[DOMAIN]["_services_registered"] = True



async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator: MultizoneCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        try:
            await coordinator.async_save_storage()
        except Exception as err:
            _LOGGER.warning("Could not save storage on unload: %s", err)
        try:
            if hasattr(coordinator, "boiler_backend") and coordinator.boiler_backend:
                await coordinator.boiler_backend.async_emergency_off()
        except Exception as err:
            _LOGGER.warning("Could not turn off boiler on unload: %s", err)
        try:
            if hasattr(coordinator, "heat_pump_backend") and coordinator.heat_pump_backend:
                await coordinator.heat_pump_backend.async_emergency_off()
        except Exception as err:
            _LOGGER.warning("Could not turn off heat pump on unload: %s", err)
        coordinator.async_teardown_listeners()
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.info("Multizone Thermostat unloaded.")

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update — config_flow already triggers reload via async_reload,
    but this listener acts as a safety net to ensure any direct option changes are applied."""
    _LOGGER.info("Options updated for Multizone Thermostat, reloading integration...")
    await hass.config_entries.async_reload(entry.entry_id)
