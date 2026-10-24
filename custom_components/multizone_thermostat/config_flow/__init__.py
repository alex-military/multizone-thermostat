"""Config flow for Multizone Thermostat integration."""
from __future__ import annotations

import copy
import logging
from typing import Any


from homeassistant import config_entries
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

from ..const import (
    CONF_BOILER_MODE,
    CONF_BOILER_SWITCH,
    CONF_GEOFENCING_ENABLED,
    CONF_OPENTHERM_ENTITY,
    CONF_OPENTHERM_MAX_TEMP,
    CONF_OPENTHERM_CH_SWITCH,
    CONF_OPENTHERM_MIN_TEMP,
    CONF_PRESENCE_SENSOR,
    CONF_ZONE_NAME,
    CONF_ZONE_CLIMATES,
    CONF_ZONE_SWITCHES,
    CONF_ZONE_VALVES,
    CONF_VALVE_SCALE,
    DEFAULT_VALVE_SCALE,
    CONF_ZONE_TEMP_SENSOR,
    CONF_ZONE_TARGET_TEMP,
    CONF_ZONE_TRV_SYNC,
    CONF_ZONE_WINDOW_SENSOR,
    CONF_ZONE_ANTI_SEIZE,
    CONF_ZONE_CALIBRATIONS,
    CONF_ZONE_ALLOW_PASSIVE_HEAT,
    CONF_ZONE_SENSOR_TIMEOUT,
    DEFAULT_SENSOR_TIMEOUT_MIN,
    CONF_ZONES,
    CONF_WEATHER_SENSOR,
    CONF_GLOBAL_CALENDAR,
    DEFAULT_TRV_SYNC,
    DOMAIN,
    MODE_OPENTHERM,
    MODE_RELAY,
    make_zone_entity_id,
    CONF_ZONE_WEIGHT,
    DEFAULT_ZONE_WEIGHT,
    CONF_ZONE_AUTHORITATIVE_SYNC,
    DEFAULT_AUTHORITATIVE_SYNC,
)

_LOGGER = logging.getLogger(__name__)


from .validators import validate_opentherm_temps, validate_zone_input, validate_geofencing
from .schemas import *
from .helpers import _get_switch_entities, _get_climate_entities, _get_binary_sensor_entities, _get_temperature_sensor_entities, _remove_entity_from_registry, flatten_zone_user_input


from .options_flow import MultizoneOptionsFlow

class MultizoneConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Multizone Thermostat."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._boiler_mode: str = MODE_RELAY
        self._boiler_switch: str | None = None
        self._opentherm_entity: str | None = None
        self._opentherm_min_temp: float = 35.0
        self._opentherm_max_temp: float = 75.0
        self._opentherm_ch_switch: str | None = None
        self._zones: list[dict] = []
        self._geofencing_enabled: bool = True
        self._presence_sensor: str | None = None
        self._weather_sensor: str | None = None
        self._global_calendar: str | None = None
        self._current_zone_data: dict[str, Any] | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step 1: Select boiler mode."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            self._boiler_mode = user_input[CONF_BOILER_MODE]
            if self._boiler_mode == MODE_RELAY:
                return await self.async_step_boiler_relay()
            else:
                return await self.async_step_boiler_opentherm()

        schema = get_boiler_mode_schema()

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
        )

    async def async_step_boiler_relay(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step 1a: Select boiler relay."""
        errors: dict[str, str] = {}
        switches = _get_switch_entities(self.hass)

        if not switches:
            return self.async_abort(reason="no_switches_found")

        if user_input is not None:
            self._boiler_switch = user_input[CONF_BOILER_SWITCH]
            return await self.async_step_add_zone()

        schema = get_boiler_relay_schema()

        return self.async_show_form(
            step_id="boiler_relay",
            data_schema=schema,
            description_placeholders={
                "switch_count": str(len(switches)),
            },
        )

    async def async_step_boiler_opentherm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step 1b: Select OpenTherm entity."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._opentherm_entity = user_input[CONF_OPENTHERM_ENTITY]
            self._opentherm_min_temp = user_input[CONF_OPENTHERM_MIN_TEMP]
            self._opentherm_max_temp = user_input[CONF_OPENTHERM_MAX_TEMP]
            self._opentherm_ch_switch = user_input.get(CONF_OPENTHERM_CH_SWITCH) or None
            errors.update(validate_opentherm_temps(self._opentherm_min_temp, self._opentherm_max_temp))
            if not errors:
                return await self.async_step_add_zone()

        schema = get_boiler_opentherm_schema()

        return self.async_show_form(
            step_id="boiler_opentherm",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_add_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step 2: Add a zone (Virtual Zone)."""
        errors: dict[str, str] = {}
        already_added = [z.get(CONF_ZONE_NAME, 'Unnamed Zone') for z in self._zones]

        if user_input is not None:
            user_input = flatten_zone_user_input(user_input)
            zone_name = user_input[CONF_ZONE_NAME].strip()
            climates = user_input.get(CONF_ZONE_CLIMATES, [])
            switches = user_input.get(CONF_ZONE_SWITCHES, [])
            valves = user_input.get(CONF_ZONE_VALVES, [])
            
            errors.update(validate_zone_input(zone_name, climates, switches, already_added, valves=valves))
            if not errors:
                zone_data = {
                    CONF_ZONE_NAME: zone_name,
                    CONF_ZONE_CLIMATES: climates,
                    CONF_ZONE_SWITCHES: switches,
                    CONF_ZONE_VALVES: valves,
                    CONF_VALVE_SCALE: user_input.get(CONF_VALVE_SCALE, DEFAULT_VALVE_SCALE),
                    CONF_ZONE_TRV_SYNC: user_input.get(CONF_ZONE_TRV_SYNC, DEFAULT_TRV_SYNC),
                    CONF_ZONE_AUTHORITATIVE_SYNC: user_input.get(CONF_ZONE_AUTHORITATIVE_SYNC, DEFAULT_AUTHORITATIVE_SYNC),
                    CONF_ZONE_WEIGHT: float(user_input.get(CONF_ZONE_WEIGHT, DEFAULT_ZONE_WEIGHT)),
                    CONF_ZONE_ANTI_SEIZE: user_input.get(CONF_ZONE_ANTI_SEIZE, True),
                    CONF_ZONE_ALLOW_PASSIVE_HEAT: user_input.get(CONF_ZONE_ALLOW_PASSIVE_HEAT, False),
                    CONF_ZONE_SENSOR_TIMEOUT: user_input.get(CONF_ZONE_SENSOR_TIMEOUT, DEFAULT_SENSOR_TIMEOUT_MIN),
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

        schema = get_add_zone_schema()

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
            
        schema = get_trv_calibration_schema(self._current_zone_data)
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
                return await self.async_step_calendar()

        schema = get_another_zone_schema()

        return self.async_show_form(
            step_id="another_zone",
            data_schema=schema,
            description_placeholders={
                "zones_added": str(len(self._zones)),
                "zones_list": ", ".join(z.get(CONF_ZONE_NAME, 'Unnamed Zone') for z in self._zones),
            },
        )

    async def async_step_calendar(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step: Calendar Setup."""
        if user_input is not None:
            if user_input.get(CONF_GLOBAL_CALENDAR) and user_input[CONF_GLOBAL_CALENDAR] != "none":
                self._global_calendar = user_input[CONF_GLOBAL_CALENDAR]
            else:
                self._global_calendar = None
            return await self.async_step_weather()

        schema = get_calendar_schema()

        return self.async_show_form(
            step_id="calendar",
            data_schema=schema,
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

        schema = get_weather_schema(sensor_options)

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
                errors.update(validate_geofencing(self._geofencing_enabled, self._presence_sensor))
                if not errors:
                    return await self.async_step_confirm()
            else:
                self._presence_sensor = None
                return await self.async_step_confirm()

        schema = get_geofencing_schema()

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
            if self._boiler_mode == MODE_RELAY:
                data = {
                    CONF_BOILER_MODE: self._boiler_mode,
                    CONF_BOILER_SWITCH: self._boiler_switch,
                    CONF_ZONES: self._zones,
                    CONF_GEOFENCING_ENABLED: self._geofencing_enabled,
                }
            else:
                data = {
                    CONF_BOILER_MODE: self._boiler_mode,
                    CONF_OPENTHERM_ENTITY: self._opentherm_entity,
                    CONF_OPENTHERM_MIN_TEMP: self._opentherm_min_temp,
                    CONF_OPENTHERM_MAX_TEMP: self._opentherm_max_temp,
                    CONF_ZONES: self._zones,
                    CONF_GEOFENCING_ENABLED: self._geofencing_enabled,
                }
                if self._opentherm_ch_switch:
                    data[CONF_OPENTHERM_CH_SWITCH] = self._opentherm_ch_switch
            if self._geofencing_enabled and self._presence_sensor:
                data[CONF_PRESENCE_SENSOR] = self._presence_sensor
            if self._weather_sensor:
                data[CONF_WEATHER_SENSOR] = self._weather_sensor
            if self._global_calendar:
                data[CONF_GLOBAL_CALENDAR] = self._global_calendar
            return self.async_create_entry(
                title="Multizone Thermostat",
                data=data,
            )

        schema = get_confirm_schema()

        return self.async_show_form(
            step_id="confirm",
            data_schema=schema,
            description_placeholders={
                "boiler_switch": self._boiler_switch or self._opentherm_entity or "N/A",
                "zones_count": str(len(self._zones)),
                "zones_list": "\n".join(
                    f"- {z.get(CONF_ZONE_NAME, 'Unnamed Zone')}"
                    for z in self._zones
                ),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get options flow."""
        return MultizoneOptionsFlow()


