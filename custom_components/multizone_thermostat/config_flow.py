"""Config flow for Multizone Thermostat integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

from .const import (
    CONF_BOILER_SWITCH,
    CONF_GEOFENCING_ENABLED,
    CONF_PRESENCE_SENSOR,
    CONF_ZONE_NAME,
    CONF_ZONE_CLIMATES,
    CONF_ZONE_SWITCHES,
    CONF_ZONE_TEMP_SENSOR,
    CONF_ZONE_TARGET_TEMP,
    CONF_ZONE_TRV_SYNC,
    CONF_ZONE_WINDOW_SENSOR,
    CONF_ZONE_ANTI_SEIZE,
    CONF_ZONE_CALIBRATIONS,
    CONF_ZONES,
    CONF_WEATHER_SENSOR,
    DEFAULT_TRV_SYNC,
    DOMAIN,
    make_zone_entity_id,
)

_LOGGER = logging.getLogger(__name__)


def _get_switch_entities(hass: HomeAssistant) -> dict[str, str]:
    """Return all switch entities as {entity_id: friendly_name}."""
    entity_reg = er.async_get(hass)
    switches = {}
    for entry in entity_reg.entities.values():
        if entry.domain == SWITCH_DOMAIN and not entry.disabled:
            state = hass.states.get(entry.entity_id)
            name = state.attributes.get("friendly_name", entry.entity_id) if state else entry.entity_id
            switches[entry.entity_id] = name
    for state in hass.states.async_all(SWITCH_DOMAIN):
        if state.entity_id not in switches:
            switches[state.entity_id] = state.attributes.get("friendly_name", state.entity_id)
    return dict(sorted(switches.items(), key=lambda x: x[1]))


def _get_climate_entities(hass: HomeAssistant) -> dict[str, str]:
    """Return all climate entities as {entity_id: friendly_name}."""
    entity_reg = er.async_get(hass)
    climates = {}
    for entry in entity_reg.entities.values():
        if entry.domain == CLIMATE_DOMAIN and not entry.disabled:
            state = hass.states.get(entry.entity_id)
            name = state.attributes.get("friendly_name", entry.entity_id) if state else entry.entity_id
            climates[entry.entity_id] = name
    for state in hass.states.async_all(CLIMATE_DOMAIN):
        if state.entity_id not in climates:
            climates[state.entity_id] = state.attributes.get("friendly_name", state.entity_id)
    return dict(sorted(climates.items(), key=lambda x: x[1]))


def _get_binary_sensor_entities(hass: HomeAssistant) -> dict[str, str]:
    """Return all binary_sensor entities as {entity_id: friendly_name}."""
    entity_reg = er.async_get(hass)
    sensors = {"none": "None"}
    for entry in entity_reg.entities.values():
        if entry.domain == BINARY_SENSOR_DOMAIN and not entry.disabled:
            state = hass.states.get(entry.entity_id)
            name = state.attributes.get("friendly_name", entry.entity_id) if state else entry.entity_id
            sensors[entry.entity_id] = name
    for state in hass.states.async_all(BINARY_SENSOR_DOMAIN):
        if state.entity_id not in sensors:
            sensors[state.entity_id] = state.attributes.get("friendly_name", state.entity_id)
    return sensors


def _get_temperature_sensor_entities(hass: HomeAssistant) -> dict[str, str]:
    """Return all temperature sensor and weather entities as {entity_id: friendly_name}."""
    entity_reg = er.async_get(hass)
    sensors = {}
    
    # 1. Fetch from entity registry (for disabled/hidden checks if needed, but states is better)
    for state in hass.states.async_all():
        domain = state.domain
        if domain == "weather":
            name = state.attributes.get("friendly_name", state.entity_id)
            sensors[state.entity_id] = name
        elif domain == SENSOR_DOMAIN and state.attributes.get("device_class") == "temperature":
            name = state.attributes.get("friendly_name", state.entity_id)
            sensors[state.entity_id] = name
            
    return dict(sorted(sensors.items(), key=lambda x: x[1]))


def _remove_entity_from_registry(hass: HomeAssistant, entity_id: str) -> None:
    """Remove an entity from the entity registry."""
    ent_reg = er.async_get(hass)
    if ent_reg.async_get(entity_id):
        ent_reg.async_remove(entity_id)
        _LOGGER.debug("Removed %s from entity registry", entity_id)


class MultizoneConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Multizone Thermostat."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._boiler_switch: str | None = None
        self._zones: list[dict] = []
        self._geofencing_enabled: bool = True
        self._presence_sensor: str | None = None
        self._weather_sensor: str | None = None
        self._current_zone_data: dict[str, Any] | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step 1: Select boiler switch."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}
        switches = _get_switch_entities(self.hass)

        if not switches:
            return self.async_abort(reason="no_switches_found")

        if user_input is not None:
            self._boiler_switch = user_input[CONF_BOILER_SWITCH]
            return await self.async_step_add_zone()

        schema = vol.Schema({
            vol.Required(CONF_BOILER_SWITCH): selector.EntitySelector(selector.EntitySelectorConfig(domain=SWITCH_DOMAIN)),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            description_placeholders={
                "switch_count": str(len(switches)),
            },
        )

    async def async_step_add_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step 2: Add a zone (Virtual Zone)."""
        errors: dict[str, str] = {}
        already_added = [z[CONF_ZONE_NAME] for z in self._zones]

        if user_input is not None:
            zone_name = user_input[CONF_ZONE_NAME].strip()
            climates = user_input.get(CONF_ZONE_CLIMATES, [])
            switches = user_input.get(CONF_ZONE_SWITCHES, [])
            
            if not zone_name:
                errors[CONF_ZONE_NAME] = "zone_name_required"
            elif zone_name in already_added:
                errors[CONF_ZONE_NAME] = "zone_name_exists"
            elif not climates and not switches:
                errors["base"] = "no_actuators_selected"
            else:
                zone_data = {
                    CONF_ZONE_NAME: zone_name,
                    CONF_ZONE_CLIMATES: climates,
                    CONF_ZONE_SWITCHES: switches,
                    CONF_ZONE_TRV_SYNC: user_input.get(CONF_ZONE_TRV_SYNC, DEFAULT_TRV_SYNC),
                    CONF_ZONE_ANTI_SEIZE: user_input.get(CONF_ZONE_ANTI_SEIZE, True),
                    CONF_ZONE_TARGET_TEMP: user_input.get(CONF_ZONE_TARGET_TEMP, 20.0),
                    CONF_ZONE_CALIBRATIONS: {},
                }
                
                if user_input.get(CONF_ZONE_TEMP_SENSOR) and user_input[CONF_ZONE_TEMP_SENSOR] != "none":
                    zone_data[CONF_ZONE_TEMP_SENSOR] = user_input[CONF_ZONE_TEMP_SENSOR]
                    
                if user_input.get(CONF_ZONE_WINDOW_SENSOR) and user_input[CONF_ZONE_WINDOW_SENSOR] != "none":
                    zone_data[CONF_ZONE_WINDOW_SENSOR] = user_input[CONF_ZONE_WINDOW_SENSOR]
                    
                self._current_zone_data = zone_data
                
                # If they added an external temp sensor AND there are TRVs, ask for calibration entities
                if CONF_ZONE_TEMP_SENSOR in zone_data and climates:
                    return await self.async_step_trv_calibration()
                
                self._zones.append(zone_data)
                self._current_zone_data = None
                return await self.async_step_another_zone()

        schema = vol.Schema({
            vol.Required(CONF_ZONE_NAME): str,
            vol.Optional(CONF_ZONE_CLIMATES, default=[]): selector.EntitySelector(selector.EntitySelectorConfig(domain=CLIMATE_DOMAIN, multiple=True)),
            vol.Optional(CONF_ZONE_SWITCHES, default=[]): selector.EntitySelector(selector.EntitySelectorConfig(domain=SWITCH_DOMAIN, multiple=True)),
            vol.Optional(CONF_ZONE_TEMP_SENSOR): selector.EntitySelector(selector.EntitySelectorConfig(domain=SENSOR_DOMAIN, device_class="temperature")),
            vol.Optional(CONF_ZONE_TARGET_TEMP, default=20.0): vol.Coerce(float),
            vol.Optional(CONF_ZONE_TRV_SYNC, default=DEFAULT_TRV_SYNC): bool,
            vol.Optional(CONF_ZONE_ANTI_SEIZE, default=True): bool,
            vol.Optional(CONF_ZONE_WINDOW_SENSOR): selector.EntitySelector(selector.EntitySelectorConfig(domain=BINARY_SENSOR_DOMAIN)),
        })

        zones_added = len(self._zones)
        return self.async_show_form(
            step_id="add_zone",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "zones_added": str(zones_added),
                "zone_number": str(zones_added + 1),
            },
        )
        
    async def async_step_trv_calibration(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step 3: Map calibration entities for TRVs."""
        if user_input is not None:
            self._current_zone_data[CONF_ZONE_CALIBRATIONS] = user_input
            self._zones.append(self._current_zone_data)
            self._current_zone_data = None
            return await self.async_step_another_zone()
            
        schema_dict = {}
        climates = self._current_zone_data[CONF_ZONE_CLIMATES]
        for climate_id in climates:
            schema_dict[vol.Optional(climate_id)] = selector.EntitySelector(selector.EntitySelectorConfig(domain=["number", "input_number"]))
            
        schema = vol.Schema(schema_dict)
        return self.async_show_form(
            step_id="trv_calibration",
            data_schema=schema,
            description_placeholders={"zone_name": self._current_zone_data[CONF_ZONE_NAME]}
        )

    async def async_step_another_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Ask if user wants to add another zone."""
        if user_input is not None:
            if user_input.get("add_another", False):
                return await self.async_step_add_zone()
            else:
                return await self.async_step_weather()

        schema = vol.Schema({
            vol.Required("add_another", default=False): bool,
        })

        return self.async_show_form(
            step_id="another_zone",
            data_schema=schema,
            description_placeholders={
                "zones_added": str(len(self._zones)),
                "zones_list": ", ".join(z[CONF_ZONE_NAME] for z in self._zones),
            },
        )

    async def async_step_weather(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step: Weather Compensation Setup."""
        if user_input is not None:
            if user_input.get(CONF_WEATHER_SENSOR) and user_input[CONF_WEATHER_SENSOR] != "none":
                self._weather_sensor = user_input[CONF_WEATHER_SENSOR]
            return await self.async_step_geofencing()

        temp_sensors = _get_temperature_sensor_entities(self.hass)
        sensor_options = {"none": "None (Disable Weather Compensation)"}
        sensor_options.update(temp_sensors)

        schema = vol.Schema({
            vol.Optional(CONF_WEATHER_SENSOR, default="none"): vol.In(sensor_options),
        })

        return self.async_show_form(
            step_id="weather",
            data_schema=schema,
        )

    async def async_step_geofencing(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step: Geofencing Setup."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            self._geofencing_enabled = user_input.get(CONF_GEOFENCING_ENABLED, True)
            if self._geofencing_enabled:
                self._presence_sensor = user_input.get(CONF_PRESENCE_SENSOR)
                if not self._presence_sensor:
                    errors[CONF_PRESENCE_SENSOR] = "presence_sensor_required"
                else:
                    return await self.async_step_confirm()
            else:
                self._presence_sensor = None
                return await self.async_step_confirm()

        schema = vol.Schema({
            vol.Required(CONF_GEOFENCING_ENABLED, default=True): bool,
            vol.Optional(CONF_PRESENCE_SENSOR, default="zone.home"): selector.EntitySelector(selector.EntitySelectorConfig(domain=["person", "group", "zone", "input_boolean"])),
        })

        return self.async_show_form(
            step_id="geofencing",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step: Confirm configuration."""
        if not self._zones:
            return self.async_abort(reason="no_zones_configured")

        if user_input is not None:
            data = {
                CONF_BOILER_SWITCH: self._boiler_switch,
                CONF_ZONES: self._zones,
                CONF_GEOFENCING_ENABLED: self._geofencing_enabled,
            }
            if self._geofencing_enabled and self._presence_sensor:
                data[CONF_PRESENCE_SENSOR] = self._presence_sensor
            if self._weather_sensor:
                data[CONF_WEATHER_SENSOR] = self._weather_sensor
            return self.async_create_entry(
                title="Multizone Thermostat",
                data=data,
            )

        schema = vol.Schema({})

        return self.async_show_form(
            step_id="confirm",
            data_schema=schema,
            description_placeholders={
                "boiler_switch": self._boiler_switch,
                "zones_count": str(len(self._zones)),
                "zones_list": "\n".join(
                    f"- {z[CONF_ZONE_NAME]}"
                    for z in self._zones
                ),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> MultizoneOptionsFlow:
        """Get options flow."""
        return MultizoneOptionsFlow(config_entry)


class MultizoneOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Multizone Thermostat."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize."""
        self._config_entry = config_entry
        self._zones: list[dict[str, Any]] = list(config_entry.data.get(CONF_ZONES, []))
        self._boiler_switch: str = config_entry.data.get(CONF_BOILER_SWITCH, "")
        self._geofencing_enabled: bool = config_entry.data.get(CONF_GEOFENCING_ENABLED, False)
        self._presence_sensor: str | None = config_entry.data.get(CONF_PRESENCE_SENSOR)
        self._weather_sensor: str | None = config_entry.data.get(CONF_WEATHER_SENSOR)
        self._current_zone_name: str | None = None
        self._current_zone_data: dict[str, Any] | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Options menu: choose what to edit."""
        if user_input is not None:
            action = user_input.get("action")
            if action == "change_boiler":
                return await self.async_step_change_boiler()
            elif action == "add_zone":
                return await self.async_step_add_zone()
            elif action == "remove_zone":
                return await self.async_step_remove_zone()
            elif action == "edit_zone":
                return await self.async_step_edit_zone()
            elif action == "edit_geofencing":
                return await self.async_step_edit_geofencing()
            elif action == "edit_weather_comp":
                return await self.async_step_edit_weather_comp()

        menu_options = {
            "change_boiler": "Change boiler switch",
            "add_zone": "Add a zone",
            "edit_zone": "Edit a zone",
            "remove_zone": "Remove a zone",
            "edit_weather_comp": "Edit Weather Compensation",
            "edit_geofencing": "Edit Geofencing Settings",
        }

        schema = vol.Schema({
            vol.Required("action"): vol.In(menu_options),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders={
                "boiler_switch": self._boiler_switch,
                "zones_count": str(len(self._zones)),
            },
        )

    async def async_step_change_boiler(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Change the boiler switch."""
        if user_input is not None:
            self._boiler_switch = user_input[CONF_BOILER_SWITCH]
            return self._save_options()

        schema = vol.Schema({
            vol.Required(CONF_BOILER_SWITCH, default=self._boiler_switch): selector.EntitySelector(selector.EntitySelectorConfig(domain=SWITCH_DOMAIN)),
        })

        return self.async_show_form(step_id="change_boiler", data_schema=schema)

    async def async_step_add_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Add a new zone."""
        errors: dict[str, str] = {}
        already_added = [z[CONF_ZONE_NAME] for z in self._zones]

        if user_input is not None:
            name = user_input[CONF_ZONE_NAME].strip()
            climates = user_input.get(CONF_ZONE_CLIMATES, [])
            switches = user_input.get(CONF_ZONE_SWITCHES, [])
            
            if name in already_added:
                errors[CONF_ZONE_NAME] = "zone_name_exists"
            elif not name:
                errors[CONF_ZONE_NAME] = "zone_name_required"
            elif not climates and not switches:
                errors["base"] = "no_actuators_selected"
            else:
                zone_data = {
                    CONF_ZONE_NAME: name,
                    CONF_ZONE_CLIMATES: climates,
                    CONF_ZONE_SWITCHES: switches,
                    CONF_ZONE_TRV_SYNC: user_input.get(CONF_ZONE_TRV_SYNC, DEFAULT_TRV_SYNC),
                    CONF_ZONE_ANTI_SEIZE: user_input.get(CONF_ZONE_ANTI_SEIZE, True),
                    CONF_ZONE_TARGET_TEMP: user_input.get(CONF_ZONE_TARGET_TEMP, 20.0),
                    CONF_ZONE_CALIBRATIONS: {},
                }
                
                if user_input.get(CONF_ZONE_TEMP_SENSOR) and user_input[CONF_ZONE_TEMP_SENSOR] != "none":
                    zone_data[CONF_ZONE_TEMP_SENSOR] = user_input[CONF_ZONE_TEMP_SENSOR]
                    
                if user_input.get(CONF_ZONE_WINDOW_SENSOR) and user_input[CONF_ZONE_WINDOW_SENSOR] != "none":
                    zone_data[CONF_ZONE_WINDOW_SENSOR] = user_input[CONF_ZONE_WINDOW_SENSOR]
                    
                self._current_zone_data = zone_data
                if CONF_ZONE_TEMP_SENSOR in zone_data and climates:
                    return await self.async_step_trv_calibration_add()
                    
                self._zones.append(zone_data)
                self._current_zone_data = None
                return self._save_options()

        schema = vol.Schema({
            vol.Required(CONF_ZONE_NAME): str,
            vol.Optional(CONF_ZONE_CLIMATES, default=[]): selector.EntitySelector(selector.EntitySelectorConfig(domain=CLIMATE_DOMAIN, multiple=True)),
            vol.Optional(CONF_ZONE_SWITCHES, default=[]): selector.EntitySelector(selector.EntitySelectorConfig(domain=SWITCH_DOMAIN, multiple=True)),
            vol.Optional(CONF_ZONE_TEMP_SENSOR): selector.EntitySelector(selector.EntitySelectorConfig(domain=SENSOR_DOMAIN, device_class="temperature")),
            vol.Optional(CONF_ZONE_TARGET_TEMP, default=20.0): vol.Coerce(float),
            vol.Optional(CONF_ZONE_TRV_SYNC, default=DEFAULT_TRV_SYNC): bool,
            vol.Optional(CONF_ZONE_ANTI_SEIZE, default=True): bool,
            vol.Optional(CONF_ZONE_WINDOW_SENSOR): selector.EntitySelector(selector.EntitySelectorConfig(domain=BINARY_SENSOR_DOMAIN)),
        })

        return self.async_show_form(
            step_id="add_zone",
            data_schema=schema,
            errors=errors
        )

    async def async_step_trv_calibration_add(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Map calibration entities for TRVs (when adding a new zone)."""
        if user_input is not None:
            self._current_zone_data[CONF_ZONE_CALIBRATIONS] = user_input
            self._zones.append(self._current_zone_data)
            self._current_zone_data = None
            return self._save_options()
            
        schema_dict = {}
        climates = self._current_zone_data[CONF_ZONE_CLIMATES]
        for climate_id in climates:
            schema_dict[vol.Optional(climate_id)] = selector.EntitySelector(selector.EntitySelectorConfig(domain=["number", "input_number"]))
            
        schema = vol.Schema(schema_dict)
        return self.async_show_form(
            step_id="trv_calibration_add",
            data_schema=schema,
            description_placeholders={"zone_name": self._current_zone_data[CONF_ZONE_NAME]}
        )

    async def async_step_remove_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Remove a zone."""
        if not self._zones:
            return self.async_abort(reason="no_zones_configured")

        zone_options = {z[CONF_ZONE_NAME]: z[CONF_ZONE_NAME] for z in self._zones}

        if user_input is not None:
            zone_to_remove = user_input["zone_name"]
            self._zones = [z for z in self._zones if z[CONF_ZONE_NAME] != zone_to_remove]
            
            # Remove entities from registry associated with this zone
            ent_reg = er.async_get(self.hass)
            
            # Virtual Master Thermostat Entity
            vt_id = make_zone_entity_id(zone_to_remove)
            _remove_entity_from_registry(self.hass, vt_id)
            
            # Mode select Entity
            safe_name = zone_to_remove.lower().replace(" ", "_").replace("-", "_")
            safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
            unique_id = f"{DOMAIN}_{self._config_entry.entry_id}_zone_mode_{safe_name}"
            entity_id = ent_reg.async_get_entity_id("select", DOMAIN, unique_id)
            if entity_id:
                ent_reg.async_remove(entity_id)
                _LOGGER.debug("Removed orphaned select entity %s from registry", entity_id)
            
            return self._save_options()

        schema = vol.Schema({
            vol.Required("zone_name"): vol.In(zone_options),
        })

        return self.async_show_form(step_id="remove_zone", data_schema=schema)

    async def async_step_edit_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Edit zone settings."""
        if not self._zones:
            return self.async_abort(reason="no_zones_configured")
            
        errors: dict[str, str] = {}

        if user_input is not None:
            if self._current_zone_name is not None:
                climates = user_input.get(CONF_ZONE_CLIMATES, [])
                switches = user_input.get(CONF_ZONE_SWITCHES, [])
                if not climates and not switches:
                    errors["base"] = "no_actuators_selected"
                else:
                    for i, z in enumerate(self._zones):
                        if z[CONF_ZONE_NAME] == self._current_zone_name:
                            self._zones[i][CONF_ZONE_CLIMATES] = climates
                            self._zones[i][CONF_ZONE_SWITCHES] = switches
                            self._zones[i][CONF_ZONE_TRV_SYNC] = user_input.get(CONF_ZONE_TRV_SYNC, DEFAULT_TRV_SYNC)
                            self._zones[i][CONF_ZONE_ANTI_SEIZE] = user_input.get(CONF_ZONE_ANTI_SEIZE, True)
                            self._zones[i][CONF_ZONE_TARGET_TEMP] = user_input.get(CONF_ZONE_TARGET_TEMP, 20.0)
                            
                            if user_input.get(CONF_ZONE_TEMP_SENSOR) and user_input[CONF_ZONE_TEMP_SENSOR] != "none":
                                self._zones[i][CONF_ZONE_TEMP_SENSOR] = user_input[CONF_ZONE_TEMP_SENSOR]
                            else:
                                self._zones[i].pop(CONF_ZONE_TEMP_SENSOR, None)
                                
                            if user_input.get(CONF_ZONE_WINDOW_SENSOR) and user_input[CONF_ZONE_WINDOW_SENSOR] != "none":
                                self._zones[i][CONF_ZONE_WINDOW_SENSOR] = user_input[CONF_ZONE_WINDOW_SENSOR]
                            else:
                                self._zones[i].pop(CONF_ZONE_WINDOW_SENSOR, None)
                            
                            self._current_zone_data = self._zones[i]
                            break
                            
                    if CONF_ZONE_TEMP_SENSOR in self._current_zone_data and climates:
                        return await self.async_step_trv_calibration_edit()
                    
                    self._current_zone_name = None
                    self._current_zone_data = None
                    return self._save_options()
            else:
                # First step: select zone to edit
                self._current_zone_name = user_input["zone_name"]
                
        if self._current_zone_name is not None:
            zone_data = next((z for z in self._zones if z[CONF_ZONE_NAME] == self._current_zone_name), None)
            
            temp_sensor_val = zone_data.get(CONF_ZONE_TEMP_SENSOR)
            temp_desc = {"description": {"suggested_value": temp_sensor_val}} if temp_sensor_val and temp_sensor_val != "none" else {}
            
            window_sensor_val = zone_data.get(CONF_ZONE_WINDOW_SENSOR)
            window_desc = {"description": {"suggested_value": window_sensor_val}} if window_sensor_val and window_sensor_val != "none" else {}
            
            schema = vol.Schema({
                vol.Optional(CONF_ZONE_CLIMATES, default=zone_data.get(CONF_ZONE_CLIMATES, [])): selector.EntitySelector(selector.EntitySelectorConfig(domain=CLIMATE_DOMAIN, multiple=True)),
                vol.Optional(CONF_ZONE_SWITCHES, default=zone_data.get(CONF_ZONE_SWITCHES, [])): selector.EntitySelector(selector.EntitySelectorConfig(domain=SWITCH_DOMAIN, multiple=True)),
                vol.Optional(CONF_ZONE_TEMP_SENSOR, **temp_desc): selector.EntitySelector(selector.EntitySelectorConfig(domain=SENSOR_DOMAIN, device_class="temperature")),
                vol.Optional(CONF_ZONE_TARGET_TEMP, default=zone_data.get(CONF_ZONE_TARGET_TEMP, 20.0)): vol.Coerce(float),
                vol.Optional(CONF_ZONE_TRV_SYNC, default=zone_data.get(CONF_ZONE_TRV_SYNC, DEFAULT_TRV_SYNC)): bool,
                vol.Optional(CONF_ZONE_ANTI_SEIZE, default=zone_data.get(CONF_ZONE_ANTI_SEIZE, True)): bool,
                vol.Optional(CONF_ZONE_WINDOW_SENSOR, **window_desc): selector.EntitySelector(selector.EntitySelectorConfig(domain=BINARY_SENSOR_DOMAIN)),
            })
            return self.async_show_form(step_id="edit_zone", data_schema=schema, errors=errors)

        zone_options = {z[CONF_ZONE_NAME]: z[CONF_ZONE_NAME] for z in self._zones}
        schema = vol.Schema({
            vol.Required("zone_name"): vol.In(zone_options),
        })
        return self.async_show_form(step_id="edit_zone", data_schema=schema)
        
    async def async_step_trv_calibration_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Map calibration entities for TRVs (when editing a zone)."""
        if user_input is not None:
            self._current_zone_data[CONF_ZONE_CALIBRATIONS] = user_input
            self._current_zone_name = None
            self._current_zone_data = None
            return self._save_options()
            
        schema_dict = {}
        climates = self._current_zone_data[CONF_ZONE_CLIMATES]
        current_calibrations = self._current_zone_data.get(CONF_ZONE_CALIBRATIONS, {})
        for climate_id in climates:
            default_val = current_calibrations.get(climate_id)
            if default_val:
                schema_dict[vol.Optional(climate_id, description={"suggested_value": default_val})] = selector.EntitySelector(selector.EntitySelectorConfig(domain=["number", "input_number"]))
            else:
                schema_dict[vol.Optional(climate_id)] = selector.EntitySelector(selector.EntitySelectorConfig(domain=["number", "input_number"]))
            
        schema = vol.Schema(schema_dict)
        return self.async_show_form(
            step_id="trv_calibration_edit",
            data_schema=schema,
            description_placeholders={"zone_name": self._current_zone_data[CONF_ZONE_NAME]}
        )

    async def async_step_edit_geofencing(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Edit geofencing settings."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            self._geofencing_enabled = user_input.get(CONF_GEOFENCING_ENABLED, False)
            if self._geofencing_enabled:
                self._presence_sensor = user_input.get(CONF_PRESENCE_SENSOR)
                if not self._presence_sensor:
                    errors[CONF_PRESENCE_SENSOR] = "presence_sensor_required"
                else:
                    return self._save_options()
            else:
                self._presence_sensor = None
                return self._save_options()

        schema = vol.Schema({
            vol.Required(CONF_GEOFENCING_ENABLED, default=self._geofencing_enabled): bool,
            vol.Optional(CONF_PRESENCE_SENSOR, default=self._presence_sensor or "zone.home"): selector.EntitySelector(selector.EntitySelectorConfig(domain=["person", "group", "zone", "input_boolean"])),
        })

        return self.async_show_form(
            step_id="edit_geofencing",
            data_schema=schema,
            errors=errors,
        )

    @callback
    async def async_step_edit_weather_comp(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Edit weather compensation settings."""
        if user_input is not None:
            if user_input.get(CONF_WEATHER_SENSOR) and user_input[CONF_WEATHER_SENSOR] != "none":
                self._weather_sensor = user_input[CONF_WEATHER_SENSOR]
            else:
                self._weather_sensor = None
            return self._save_options()

        temp_sensors = _get_temperature_sensor_entities(self.hass)
        sensor_options = {"none": "None (Disable Weather Compensation)"}
        sensor_options.update(temp_sensors)

        schema = vol.Schema({
            vol.Optional(
                CONF_WEATHER_SENSOR, 
                default=self._weather_sensor or "none"
            ): vol.In(sensor_options),
        })

        return self.async_show_form(
            step_id="edit_weather_comp",
            data_schema=schema,
        )

    def _save_options(self) -> config_entries.FlowResult:
        """Save updated options into entry.data and reload entry."""
        data = {
            CONF_BOILER_SWITCH: self._boiler_switch,
            CONF_ZONES: self._zones,
            CONF_GEOFENCING_ENABLED: self._geofencing_enabled,
        }
        if self._geofencing_enabled and self._presence_sensor:
            data[CONF_PRESENCE_SENSOR] = self._presence_sensor
            
        if self._weather_sensor:
            data[CONF_WEATHER_SENSOR] = self._weather_sensor

        self.hass.config_entries.async_update_entry(
            self._config_entry, data=data
        )
        
        self.hass.async_create_task(
            self.hass.config_entries.async_reload(self._config_entry.entry_id)
        )
        
        return self.async_create_entry(title="", data={})
