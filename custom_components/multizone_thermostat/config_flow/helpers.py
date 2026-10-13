"""Helpers for Multizone Thermostat config flow."""
import logging
from typing import Any

from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

_LOGGER = logging.getLogger(__name__)


def _get_entities_by_domain(hass: HomeAssistant, domain: str, include_none: bool = False) -> dict[str, str]:
    """Return entities for a specific domain efficiently."""
    entity_reg = er.async_get(hass)
    entities = {"none": "None"} if include_none else {}
    
    for entry in er.async_entries_for_domain(entity_reg, domain):
        if not entry.disabled:
            state = hass.states.get(entry.entity_id)
            name = state.attributes.get("friendly_name", entry.entity_id) if state else entry.entity_id
            entities[entry.entity_id] = name
            
    for state in hass.states.async_all(domain):
        if state.entity_id not in entities:
            entities[state.entity_id] = state.attributes.get("friendly_name", state.entity_id)
            
    if include_none:
        sorted_entities = {"none": "None"}
        sorted_entities.update(dict(sorted({k: v for k, v in entities.items() if k != "none"}.items(), key=lambda x: x[1])))
        return sorted_entities
    return dict(sorted(entities.items(), key=lambda x: x[1]))


def _get_switch_entities(hass: HomeAssistant) -> dict[str, str]:
    return _get_entities_by_domain(hass, SWITCH_DOMAIN)


def _get_climate_entities(hass: HomeAssistant) -> dict[str, str]:
    return _get_entities_by_domain(hass, CLIMATE_DOMAIN)


def _get_binary_sensor_entities(hass: HomeAssistant) -> dict[str, str]:
    return _get_entities_by_domain(hass, BINARY_SENSOR_DOMAIN, include_none=True)


def _get_temperature_sensor_entities(hass: HomeAssistant) -> dict[str, str]:
    """Return all temperature sensor and weather entities as {entity_id: friendly_name}."""
    sensors = {}
    
    for state in hass.states.async_all("weather"):
        sensors[state.entity_id] = state.attributes.get("friendly_name", state.entity_id)
        
    for state in hass.states.async_all(SENSOR_DOMAIN):
        if state.attributes.get("device_class") == "temperature":
            sensors[state.entity_id] = state.attributes.get("friendly_name", state.entity_id)
            
    return dict(sorted(sensors.items(), key=lambda x: x[1]))


def _remove_entity_from_registry(hass: HomeAssistant, entity_id: str) -> None:
    """Remove an entity from the entity registry."""
    ent_reg = er.async_get(hass)
    if ent_reg.async_get(entity_id):
        ent_reg.async_remove(entity_id)
        _LOGGER.debug("Removed %s from entity registry", entity_id)


def flatten_zone_user_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """Flatten user_input dictionary across collapsible sections."""
    flattened = dict(user_input)
    for section_key in ("trv_settings", "valve_settings", "relay_settings", "safety_settings"):
        sec = flattened.pop(section_key, None)
        if isinstance(sec, dict):
            flattened.update(sec)
    return flattened

