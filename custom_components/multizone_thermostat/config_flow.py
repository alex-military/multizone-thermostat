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
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_BOILER_SWITCH,
    CONF_VIRTUAL_THERMOSTATS,
    CONF_VT_HEATER_SWITCH,
    CONF_VT_NAME,
    CONF_VT_TARGET_TEMP,
    CONF_VT_TEMP_SENSOR,
    CONF_VT_TOLERANCE,
    CONF_GEOFENCING_ENABLED,
    CONF_PRESENCE_SENSOR,
    CONF_ZONE_CLIMATE,
    CONF_ZONE_NAME,
    CONF_ZONE_TRV_SYNC,
    CONF_ZONE_WINDOW_SENSOR,
    CONF_ZONE_ANTI_SEIZE,
    CONF_ZONES,
    CONF_ANTI_SEIZE_ENABLED,
    CONF_ANTI_SEIZE_IDLE_DAYS,
    CONF_ANTI_SEIZE_DURATION,
    CONF_ANTI_SEIZE_BOILER,
    DEFAULT_TRV_SYNC,
    DEFAULT_VT_TARGET_TEMP,
    DEFAULT_VT_TOLERANCE,
    DOMAIN,
    make_vt_entity_id,
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
    # Also include states not in registry
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
    """Return all temperature sensor entities as {entity_id: friendly_name}."""
    entity_reg = er.async_get(hass)
    sensors = {}
    for entry in entity_reg.entities.values():
        if entry.domain == SENSOR_DOMAIN and not entry.disabled:
            state = hass.states.get(entry.entity_id)
            if state and state.attributes.get("device_class") == "temperature":
                name = state.attributes.get("friendly_name", entry.entity_id)
                sensors[entry.entity_id] = name
    for state in hass.states.async_all(SENSOR_DOMAIN):
        if state.entity_id not in sensors:
            if state.attributes.get("device_class") == "temperature":
                sensors[state.entity_id] = state.attributes.get("friendly_name", state.entity_id)
    return dict(sorted(sensors.items(), key=lambda x: x[1]))



def _remove_entity_from_registry(hass: HomeAssistant, entity_id: str) -> None:
    """Remove an entity from the entity registry."""
    ent_reg = er.async_get(hass)
    if ent_reg.async_get(entity_id):
        ent_reg.async_remove(entity_id)
        _LOGGER.debug("Removed %s from entity registry", entity_id)


def _friendly_name_from_climate(hass: HomeAssistant, entity_id: str) -> str:
    """Get the friendly name of a climate entity."""
    state = hass.states.get(entity_id)
    if state:
        return state.attributes.get("friendly_name", entity_id)
    return entity_id


class MultizoneConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Multizone Thermostat."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._boiler_switch: str | None = None
        self._zones: list[dict] = []
        self._virtual_thermostats: list[dict] = []
        self._geofencing_enabled: bool = True
        self._presence_sensor: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step 1: Select boiler switch."""
        # Only allow one instance
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}
        switches = _get_switch_entities(self.hass)

        if not switches:
            return self.async_abort(reason="no_switches_found")

        if user_input is not None:
            self._boiler_switch = user_input[CONF_BOILER_SWITCH]
            return await self.async_step_choose_zone_type()

        schema = vol.Schema({
            vol.Required(CONF_BOILER_SWITCH): vol.In(switches),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            description_placeholders={
                "switch_count": str(len(switches)),
            },
        )

    async def async_step_choose_zone_type(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Choose between existing climate or virtual thermostat."""
        if user_input is not None:
            zone_type = user_input.get("zone_type", "existing")
            if zone_type == "virtual":
                return await self.async_step_create_virtual_thermostat()
            return await self.async_step_add_zone()

        schema = vol.Schema({
            vol.Required("zone_type", default="existing"): vol.In({
                "existing": "Use existing thermostat",
                "virtual": "Create virtual thermostat",
            }),
        })

        return self.async_show_form(
            step_id="choose_zone_type",
            data_schema=schema,
        )

    async def async_step_create_virtual_thermostat(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Create a virtual thermostat from a temp sensor + heater switch."""
        errors: dict[str, str] = {}

        if user_input is not None:
            vt_name = user_input[CONF_VT_NAME].strip()
            if not vt_name:
                errors[CONF_VT_NAME] = "zone_name_required"
            else:
                vt_config = {
                    CONF_VT_NAME: vt_name,
                    CONF_VT_TEMP_SENSOR: user_input[CONF_VT_TEMP_SENSOR],
                    CONF_VT_HEATER_SWITCH: user_input[CONF_VT_HEATER_SWITCH],
                    CONF_VT_TARGET_TEMP: user_input.get(CONF_VT_TARGET_TEMP, DEFAULT_VT_TARGET_TEMP),
                    CONF_VT_TOLERANCE: user_input.get(CONF_VT_TOLERANCE, DEFAULT_VT_TOLERANCE),
                }
                self._virtual_thermostats.append(vt_config)

                # Auto-add as zone
                vt_entity_id = make_vt_entity_id(vt_name)
                sensors = _get_binary_sensor_entities(self.hass)
                window_sensor = user_input.get(CONF_ZONE_WINDOW_SENSOR)

                zone_data = {
                    CONF_ZONE_NAME: vt_name,
                    CONF_ZONE_CLIMATE: vt_entity_id,
                    CONF_ZONE_TRV_SYNC: False,
                    CONF_ZONE_ANTI_SEIZE: user_input.get(CONF_ZONE_ANTI_SEIZE, True),
                }
                if window_sensor and window_sensor != "none":
                    zone_data[CONF_ZONE_WINDOW_SENSOR] = window_sensor

                self._zones.append(zone_data)
                return await self.async_step_another_zone()

        temp_sensors = _get_temperature_sensor_entities(self.hass)
        switches = _get_switch_entities(self.hass)
        window_sensors = _get_binary_sensor_entities(self.hass)

        if not temp_sensors:
            return self.async_abort(reason="no_temp_sensors_found")
        if not switches:
            return self.async_abort(reason="no_switches_found")

        schema = vol.Schema({
            vol.Required(CONF_VT_NAME): str,
            vol.Required(CONF_VT_TEMP_SENSOR): vol.In(temp_sensors),
            vol.Required(CONF_VT_HEATER_SWITCH): vol.In(switches),
            vol.Optional(CONF_VT_TARGET_TEMP, default=DEFAULT_VT_TARGET_TEMP): vol.Coerce(float),
            vol.Optional(CONF_VT_TOLERANCE, default=DEFAULT_VT_TOLERANCE): vol.Coerce(float),
            vol.Optional(CONF_ZONE_ANTI_SEIZE, default=True): bool,
            vol.Optional(CONF_ZONE_WINDOW_SENSOR, default="none"): vol.In(window_sensors),
        })

        return self.async_show_form(
            step_id="create_virtual_thermostat",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_add_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step 2: Add a zone (climate entity)."""
        errors: dict[str, str] = {}
        climates = _get_climate_entities(self.hass)

        # Filter out already-added climates
        already_added = {z[CONF_ZONE_CLIMATE] for z in self._zones}
        available_climates = {k: v for k, v in climates.items() if k not in already_added}

        if not available_climates:
            # No more climates to add, go to geofencing
            return await self.async_step_geofencing()
        if user_input is not None:
            climate_entity = user_input[CONF_ZONE_CLIMATE]
            zone_name = user_input[CONF_ZONE_NAME].strip()
            trv_sync = user_input.get(CONF_ZONE_TRV_SYNC, DEFAULT_TRV_SYNC)

            if not zone_name:
                errors[CONF_ZONE_NAME] = "zone_name_required"
            else:
                zone_data = {
                    CONF_ZONE_NAME: zone_name,
                    CONF_ZONE_CLIMATE: climate_entity,
                    CONF_ZONE_TRV_SYNC: trv_sync,
                    CONF_ZONE_ANTI_SEIZE: user_input.get(CONF_ZONE_ANTI_SEIZE, True),
                }
                if user_input.get(CONF_ZONE_WINDOW_SENSOR) and user_input[CONF_ZONE_WINDOW_SENSOR] != "none":
                    zone_data[CONF_ZONE_WINDOW_SENSOR] = user_input[CONF_ZONE_WINDOW_SENSOR]
                    
                self._zones.append(zone_data)

                # Ask if user wants to add another zone
                return await self.async_step_another_zone()

        # Pre-populate zone name with first available climate's friendly name
        first_climate_id = next(iter(available_climates))
        default_name = _friendly_name_from_climate(self.hass, first_climate_id)
        sensors = _get_binary_sensor_entities(self.hass)

        schema = vol.Schema({
            vol.Required(CONF_ZONE_CLIMATE): vol.In(available_climates),
            vol.Required(CONF_ZONE_NAME, default=default_name): str,
            vol.Optional(CONF_ZONE_TRV_SYNC, default=DEFAULT_TRV_SYNC): bool,
            vol.Optional(CONF_ZONE_ANTI_SEIZE, default=True): bool,
            vol.Optional(CONF_ZONE_WINDOW_SENSOR, default="none"): vol.In(sensors),
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

    async def async_step_another_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Ask if user wants to add another zone."""
        if user_input is not None:
            if user_input.get("add_another", False):
                return await self.async_step_choose_zone_type()
            else:
                return await self.async_step_geofencing()

        climates = _get_climate_entities(self.hass)
        already_added = {z[CONF_ZONE_CLIMATE] for z in self._zones}
        remaining = len(climates) - len(already_added)

        schema = vol.Schema({
            vol.Required("add_another", default=remaining > 0): bool,
        })

        return self.async_show_form(
            step_id="another_zone",
            data_schema=schema,
            description_placeholders={
                "zones_added": str(len(self._zones)),
                "zones_list": ", ".join(z[CONF_ZONE_NAME] for z in self._zones),
                "remaining": str(remaining),
            },
        )

    async def async_step_geofencing(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step: Geofencing Setup."""
        errors: dict[str, str] = {}
        
        # Get persons, zones, and groups for presence sensing
        entity_reg = er.async_get(self.hass)
        presence_entities = {}
        # Pre-populate with zone.home which always exists
        state = self.hass.states.get("zone.home")
        if state:
            presence_entities["zone.home"] = state.attributes.get("friendly_name", "Home")
            
        for entry in entity_reg.entities.values():
            if entry.domain in ("person", "group", "zone", "input_boolean") and not entry.disabled:
                st = self.hass.states.get(entry.entity_id)
                name = st.attributes.get("friendly_name", entry.entity_id) if st else entry.entity_id
                presence_entities[entry.entity_id] = name
        for st in self.hass.states.async_all(("person", "group", "zone", "input_boolean")):
            if st.entity_id not in presence_entities:
                presence_entities[st.entity_id] = st.attributes.get("friendly_name", st.entity_id)
                
        presence_entities = dict(sorted(presence_entities.items(), key=lambda x: x[1]))

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
            vol.Optional(CONF_PRESENCE_SENSOR, default="zone.home"): vol.In(presence_entities),
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
            if self._virtual_thermostats:
                data[CONF_VIRTUAL_THERMOSTATS] = self._virtual_thermostats
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
                    f"- {z[CONF_ZONE_NAME]} ({z[CONF_ZONE_CLIMATE]})"
                    + (" [TRV sync]" if z[CONF_ZONE_TRV_SYNC] else "")
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
        self._virtual_thermostats: list[dict] = list(config_entry.data.get(CONF_VIRTUAL_THERMOSTATS, []))
        self._geofencing_enabled: bool = config_entry.data.get(CONF_GEOFENCING_ENABLED, False)
        self._presence_sensor: str | None = config_entry.data.get(CONF_PRESENCE_SENSOR)
        self._current_zone_id: str | None = None
        self._current_zone_idx = 0

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
            elif action == "create_virtual":
                return await self.async_step_create_virtual_thermostat()
            elif action == "remove_virtual":
                return await self.async_step_remove_virtual_thermostat()

        menu_options = {
            "change_boiler": "Change boiler switch",
            "add_zone": "Add a zone (existing thermostat)",
            "edit_geofencing": "Edit Geofencing Settings",
            "create_virtual": "Create virtual thermostat",
            "remove_zone": "Remove a zone",
            "edit_zone": "Edit a zone",
        }
        if self._virtual_thermostats:
            menu_options["remove_virtual"] = "Remove virtual thermostat"

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
        switches = _get_switch_entities(self.hass)

        if user_input is not None:
            self._boiler_switch = user_input[CONF_BOILER_SWITCH]
            return self._save_options()

        schema = vol.Schema({
            vol.Required(CONF_BOILER_SWITCH, default=self._boiler_switch): vol.In(switches),
        })

        return self.async_show_form(step_id="change_boiler", data_schema=schema)

    async def async_step_add_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Add a new zone."""
        errors: dict[str, str] = {}
        climates = _get_climate_entities(self.hass)
        already_added = {z[CONF_ZONE_CLIMATE] for z in self._zones}
        available_climates = {k: v for k, v in climates.items() if k not in already_added}

        if not available_climates:
            return self.async_abort(reason="no_climates_available")

        if user_input is not None:
            climate_id = user_input[CONF_ZONE_CLIMATE]
            name = user_input[CONF_ZONE_NAME].strip()
            
            if not name:
                errors[CONF_ZONE_NAME] = "zone_name_required"
            else:
                zone_data = {
                    CONF_ZONE_CLIMATE: climate_id,
                    CONF_ZONE_NAME: name,
                    CONF_ZONE_TRV_SYNC: user_input.get(CONF_ZONE_TRV_SYNC, DEFAULT_TRV_SYNC),
                    CONF_ZONE_ANTI_SEIZE: user_input.get(CONF_ZONE_ANTI_SEIZE, True),
                }
                if user_input.get(CONF_ZONE_WINDOW_SENSOR) and user_input[CONF_ZONE_WINDOW_SENSOR] != "none":
                    zone_data[CONF_ZONE_WINDOW_SENSOR] = user_input[CONF_ZONE_WINDOW_SENSOR]
                    
                self._zones.append(zone_data)
                return self._save_options()

        sensors = _get_binary_sensor_entities(self.hass)

        schema = vol.Schema({
            vol.Required(CONF_ZONE_CLIMATE): vol.In(available_climates),
            vol.Required(CONF_ZONE_NAME): str,
            vol.Optional(CONF_ZONE_TRV_SYNC, default=DEFAULT_TRV_SYNC): bool,
            vol.Optional(CONF_ZONE_ANTI_SEIZE, default=True): bool,
            vol.Optional(CONF_ZONE_WINDOW_SENSOR, default="none"): vol.In(sensors),
        })

        return self.async_show_form(
            step_id="add_zone",
            data_schema=schema,
            errors=errors
        )

    async def async_step_remove_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Remove a zone."""
        if not self._zones:
            return self.async_abort(reason="no_zones_configured")

        zone_options = {z[CONF_ZONE_CLIMATE]: z[CONF_ZONE_NAME] for z in self._zones}

        if user_input is not None:
            climate_to_remove = user_input["zone_climate"]
            zone_name = zone_options[climate_to_remove]
            
            # Remove the zone config
            self._zones = [z for z in self._zones if z[CONF_ZONE_CLIMATE] != climate_to_remove]
            
            # Remove the associated select entity from registry
            ent_reg = er.async_get(self.hass)
            safe_climate = climate_to_remove.replace('.', '_').replace('-', '_')
            unique_id = f"{DOMAIN}_{self._config_entry.entry_id}_zone_mode_{safe_climate}"
            entity_id = ent_reg.async_get_entity_id("select", DOMAIN, unique_id)
            if entity_id:
                ent_reg.async_remove(entity_id)
                _LOGGER.debug("Removed orphaned select entity %s from registry", entity_id)
            
            return self._save_options()

        schema = vol.Schema({
            vol.Required("zone_climate"): vol.In(zone_options),
        })

        return self.async_show_form(step_id="remove_zone", data_schema=schema)

    async def async_step_create_virtual_thermostat(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Create a virtual thermostat."""
        errors: dict[str, str] = {}

        if user_input is not None:
            vt_name = user_input[CONF_VT_NAME].strip()
            if not vt_name:
                errors[CONF_VT_NAME] = "zone_name_required"
            else:
                vt_config = {
                    CONF_VT_NAME: vt_name,
                    CONF_VT_TEMP_SENSOR: user_input[CONF_VT_TEMP_SENSOR],
                    CONF_VT_HEATER_SWITCH: user_input[CONF_VT_HEATER_SWITCH],
                    CONF_VT_TARGET_TEMP: user_input.get(CONF_VT_TARGET_TEMP, DEFAULT_VT_TARGET_TEMP),
                    CONF_VT_TOLERANCE: user_input.get(CONF_VT_TOLERANCE, DEFAULT_VT_TOLERANCE),
                }
                self._virtual_thermostats.append(vt_config)

                # Auto-add as zone
                vt_entity_id = make_vt_entity_id(vt_name)
                window_sensor = user_input.get(CONF_ZONE_WINDOW_SENSOR)

                zone_data = {
                    CONF_ZONE_NAME: vt_name,
                    CONF_ZONE_CLIMATE: vt_entity_id,
                    CONF_ZONE_TRV_SYNC: False,
                    CONF_ZONE_ANTI_SEIZE: user_input.get(CONF_ZONE_ANTI_SEIZE, True),
                }
                if window_sensor and window_sensor != "none":
                    zone_data[CONF_ZONE_WINDOW_SENSOR] = window_sensor

                self._zones.append(zone_data)
                return self._save_options()

        temp_sensors = _get_temperature_sensor_entities(self.hass)
        switches = _get_switch_entities(self.hass)
        window_sensors = _get_binary_sensor_entities(self.hass)

        if not temp_sensors:
            return self.async_abort(reason="no_temp_sensors_found")
        if not switches:
            return self.async_abort(reason="no_switches_found")

        schema = vol.Schema({
            vol.Required(CONF_VT_NAME): str,
            vol.Required(CONF_VT_TEMP_SENSOR): vol.In(temp_sensors),
            vol.Required(CONF_VT_HEATER_SWITCH): vol.In(switches),
            vol.Optional(CONF_VT_TARGET_TEMP, default=DEFAULT_VT_TARGET_TEMP): vol.Coerce(float),
            vol.Optional(CONF_VT_TOLERANCE, default=DEFAULT_VT_TOLERANCE): vol.Coerce(float),
            vol.Optional(CONF_ZONE_ANTI_SEIZE, default=True): bool,
            vol.Optional(CONF_ZONE_WINDOW_SENSOR, default="none"): vol.In(window_sensors),
        })

        return self.async_show_form(
            step_id="create_virtual_thermostat",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_remove_virtual_thermostat(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Remove a virtual thermostat."""
        if not self._virtual_thermostats:
            return self.async_abort(reason="no_virtual_thermostats")

        vt_options = {
            make_vt_entity_id(vt[CONF_VT_NAME]): vt[CONF_VT_NAME]
            for vt in self._virtual_thermostats
        }

        if user_input is not None:
            vt_to_remove = user_input["virtual_thermostat"]
            
            # Find the VT config to get its name before removal
            vt_name = next((vt[CONF_VT_NAME] for vt in self._virtual_thermostats if make_vt_entity_id(vt[CONF_VT_NAME]) == vt_to_remove), None)
            
            # Remove the VT config
            self._virtual_thermostats = [
                vt for vt in self._virtual_thermostats
                if make_vt_entity_id(vt[CONF_VT_NAME]) != vt_to_remove
            ]
            # Remove the associated zone
            self._zones = [
                z for z in self._zones
                if z[CONF_ZONE_CLIMATE] != vt_to_remove
            ]
            
            if vt_name:
                # Remove VT entity from registry
                _remove_entity_from_registry(self.hass, vt_to_remove)
                # Remove associated zone select from registry
                ent_reg = er.async_get(self.hass)
                safe_vt = vt_to_remove.replace('.', '_').replace('-', '_')
                unique_id = f"{DOMAIN}_{self._config_entry.entry_id}_zone_mode_{safe_vt}"
                entity_id = ent_reg.async_get_entity_id("select", DOMAIN, unique_id)
                if entity_id:
                    ent_reg.async_remove(entity_id)
                    _LOGGER.debug("Removed orphaned VT select entity %s from registry", entity_id)
                
            return self._save_options()

        schema = vol.Schema({
            vol.Required("virtual_thermostat"): vol.In(vt_options),
        })

        return self.async_show_form(step_id="remove_virtual_thermostat", data_schema=schema)

    async def async_step_edit_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Edit zone settings."""
        if not self._zones:
            return self.async_abort(reason="no_zones_configured")

        if user_input is not None:
            if self._current_zone_id is not None:
                # Second step: edit the zone
                for i, z in enumerate(self._zones):
                    if z[CONF_ZONE_CLIMATE] == self._current_zone_id:
                        self._zones[i][CONF_ZONE_TRV_SYNC] = user_input[CONF_ZONE_TRV_SYNC]
                        self._zones[i][CONF_ZONE_ANTI_SEIZE] = user_input.get(CONF_ZONE_ANTI_SEIZE, True)
                        if user_input.get(CONF_ZONE_WINDOW_SENSOR) and user_input[CONF_ZONE_WINDOW_SENSOR] != "none":
                            self._zones[i][CONF_ZONE_WINDOW_SENSOR] = user_input[CONF_ZONE_WINDOW_SENSOR]
                        else:
                            self._zones[i].pop(CONF_ZONE_WINDOW_SENSOR, None)
                        break
                self._current_zone_id = None
                return self._save_options()

            # First step: select zone to edit
            self._current_zone_id = user_input["zone_climate"]
            zone_data = next((z for z in self._zones if z[CONF_ZONE_CLIMATE] == self._current_zone_id), None)
            
            sensors = _get_binary_sensor_entities(self.hass)
            current_sensor = zone_data.get(CONF_ZONE_WINDOW_SENSOR, "none") if zone_data else "none"
            if current_sensor not in sensors:
                current_sensor = "none"

            schema = vol.Schema({
                vol.Required(
                    CONF_ZONE_TRV_SYNC, 
                    default=zone_data.get(CONF_ZONE_TRV_SYNC, DEFAULT_TRV_SYNC) if zone_data else DEFAULT_TRV_SYNC
                ): bool,
                vol.Optional(
                    CONF_ZONE_ANTI_SEIZE,
                    default=zone_data.get(CONF_ZONE_ANTI_SEIZE, True) if zone_data else True
                ): bool,
                vol.Optional(CONF_ZONE_WINDOW_SENSOR, default=current_sensor): vol.In(sensors),
            })
            return self.async_show_form(step_id="edit_zone", data_schema=schema)

        zone_options = {z[CONF_ZONE_CLIMATE]: z[CONF_ZONE_NAME] for z in self._zones}
        schema = vol.Schema({
            vol.Required("zone_climate"): vol.In(zone_options),
        })
        return self.async_show_form(step_id="edit_zone", data_schema=schema)

    async def async_step_edit_geofencing(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Edit geofencing settings."""
        errors: dict[str, str] = {}
        
        entity_reg = er.async_get(self.hass)
        presence_entities = {}
        state = self.hass.states.get("zone.home")
        if state:
            presence_entities["zone.home"] = state.attributes.get("friendly_name", "Home")
            
        for entry in entity_reg.entities.values():
            if entry.domain in ("person", "group", "zone", "input_boolean") and not entry.disabled:
                st = self.hass.states.get(entry.entity_id)
                name = st.attributes.get("friendly_name", entry.entity_id) if st else entry.entity_id
                presence_entities[entry.entity_id] = name
        for st in self.hass.states.async_all(("person", "group", "zone", "input_boolean")):
            if st.entity_id not in presence_entities:
                presence_entities[st.entity_id] = st.attributes.get("friendly_name", st.entity_id)
                
        presence_entities = dict(sorted(presence_entities.items(), key=lambda x: x[1]))

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
            vol.Optional(CONF_PRESENCE_SENSOR, default=self._presence_sensor or "zone.home"): vol.In(presence_entities),
        })

        return self.async_show_form(
            step_id="edit_geofencing",
            data_schema=schema,
            errors=errors,
        )

    @callback
    def _save_options(self) -> config_entries.FlowResult:
        """Save updated options into entry.data and reload entry."""
        data = {
            CONF_BOILER_SWITCH: self._boiler_switch,
            CONF_ZONES: self._zones,
            CONF_GEOFENCING_ENABLED: self._geofencing_enabled,
        }
        if self._geofencing_enabled and self._presence_sensor:
            data[CONF_PRESENCE_SENSOR] = self._presence_sensor
            
        if self._virtual_thermostats:
            data[CONF_VIRTUAL_THERMOSTATS] = self._virtual_thermostats
        self.hass.config_entries.async_update_entry(
            self._config_entry, data=data
        )
        
        # Explicitly reload the entry since we updated data, not options
        self.hass.async_create_task(
            self.hass.config_entries.async_reload(self._config_entry.entry_id)
        )
        
        return self.async_create_entry(title="", data={})
