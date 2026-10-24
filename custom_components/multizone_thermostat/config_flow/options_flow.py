from typing import Any
import copy
from homeassistant import config_entries
from homeassistant.core import callback
from .schemas import *
from .validators import validate_opentherm_temps, validate_zone_input, validate_geofencing
from .helpers import (
    _get_temperature_sensor_entities,
    _remove_entity_from_registry,
    flatten_zone_user_input,
)
from ..const import *
from ..const import (
    CONF_ZONE_WEIGHT,
    DEFAULT_ZONE_WEIGHT,
    CONF_ZONE_AUTHORITATIVE_SYNC,
    DEFAULT_AUTHORITATIVE_SYNC,
)
import logging
from homeassistant.helpers import entity_registry as er

_LOGGER = logging.getLogger(__name__)



class MultizoneOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Multizone Thermostat."""

    def __init__(self) -> None:
        """Initialize."""
        # self.config_entry is automatically set by Home Assistant 2024.12+
        self._zones: list[dict[str, Any]] = []
        self._boiler_mode: str = MODE_RELAY
        self._boiler_switch: str = ""
        self._opentherm_entity: str | None = None
        self._opentherm_min_temp: float = 35.0
        self._opentherm_max_temp: float = 75.0
        self._opentherm_ch_switch: str | None = None
        self._geofencing_enabled: bool = False
        self._presence_sensor: str | None = None
        self._weather_sensor: str | None = None
        self._global_calendar: str | None = None
        self._current_zone_name: str | None = None
        self._current_zone_data: dict[str, Any] | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Options menu: choose what to edit."""
        if not self._zones:
            cfg = {**self.config_entry.data, **self.config_entry.options}
            self._zones = copy.deepcopy(cfg.get(CONF_ZONES, []))
            self._boiler_mode = cfg.get(CONF_BOILER_MODE, MODE_RELAY)
            self._boiler_switch = cfg.get(CONF_BOILER_SWITCH, "")
            self._opentherm_entity = cfg.get(CONF_OPENTHERM_ENTITY)
            self._opentherm_min_temp = cfg.get(CONF_OPENTHERM_MIN_TEMP, 35.0)
            self._opentherm_max_temp = cfg.get(CONF_OPENTHERM_MAX_TEMP, 75.0)
            self._opentherm_ch_switch = cfg.get(CONF_OPENTHERM_CH_SWITCH)
            self._geofencing_enabled = cfg.get(CONF_GEOFENCING_ENABLED, False)
            self._presence_sensor = cfg.get(CONF_PRESENCE_SENSOR)
            self._weather_sensor = cfg.get(CONF_WEATHER_SENSOR)
            self._global_calendar = cfg.get(CONF_GLOBAL_CALENDAR)
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
            elif action == "edit_calendar":
                return await self.async_step_edit_calendar()

        menu_options = {
            "change_boiler": "Change boiler mode",
            "add_zone": "Add a zone",
            "edit_zone": "Edit a zone",
            "remove_zone": "Remove a zone",
            "edit_weather_comp": "Edit Weather Compensation",
            "edit_geofencing": "Edit Geofencing Settings",
            "edit_calendar": "Edit Global Calendar",
        }

        schema = get_options_init_schema(menu_options)

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders={
                "boiler_switch": self._boiler_switch or self._opentherm_entity or "N/A",
                "zones_count": str(len(self._zones)),
            },
        )

    async def async_step_change_boiler(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Change boiler mode."""
        if user_input is not None:
            self._boiler_mode = user_input[CONF_BOILER_MODE]
            if self._boiler_mode == MODE_RELAY:
                return await self.async_step_boiler_relay()
            else:
                return await self.async_step_boiler_opentherm()

        schema = get_options_change_boiler_schema(self._boiler_mode)

        return self.async_show_form(step_id="change_boiler", data_schema=schema)

    async def async_step_boiler_relay(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step 1a: Select boiler relay."""
        if user_input is not None:
            self._boiler_switch = user_input[CONF_BOILER_SWITCH]
            return self._save_options()

        schema = get_options_boiler_relay_schema(self._boiler_switch)
        return self.async_show_form(step_id="boiler_relay", data_schema=schema)

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
                return self._save_options()

        schema = get_options_boiler_opentherm_schema(
            self._opentherm_entity, self._opentherm_min_temp, self._opentherm_max_temp, self._opentherm_ch_switch
        )

        return self.async_show_form(step_id="boiler_opentherm", data_schema=schema, errors=errors)

    async def async_step_add_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Add a new zone."""
        errors: dict[str, str] = {}
        already_added = [z.get(CONF_ZONE_NAME, 'Unnamed Zone') for z in self._zones]

        if user_input is not None:
            user_input = flatten_zone_user_input(user_input)
            name = user_input[CONF_ZONE_NAME].strip()
            climates = user_input.get(CONF_ZONE_CLIMATES, [])
            switches = user_input.get(CONF_ZONE_SWITCHES, [])
            valves = user_input.get(CONF_ZONE_VALVES, [])
            
            errors.update(validate_zone_input(name, climates, switches, already_added, valves=valves))
            if not errors:
                zone_data = {
                    CONF_ZONE_NAME: name,
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
                if CONF_ZONE_TEMP_SENSOR in zone_data and climates:
                    return await self.async_step_trv_calibration_add()
                    
                self._zones.append(zone_data)
                self._current_zone_data = None
                return self._save_options()

        schema = get_add_zone_schema()

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
            
        schema = get_trv_calibration_schema(self._current_zone_data)
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

        zone_options = {z.get(CONF_ZONE_NAME, 'Unnamed Zone'): z.get(CONF_ZONE_NAME, 'Unnamed Zone') for z in self._zones}

        if user_input is not None:
            zone_to_remove = user_input["zone_name"]
            self._zones = [z for z in self._zones if z.get(CONF_ZONE_NAME, 'Unnamed Zone') != zone_to_remove]
            
            # Remove entities from registry associated with this zone
            ent_reg = er.async_get(self.hass)
            
            # Virtual Master Thermostat Entity
            vt_id = make_zone_entity_id(zone_to_remove)
            _remove_entity_from_registry(self.hass, vt_id)
            
            safe_name = zone_to_remove.lower().replace(" ", "_").replace("-", "_")
            safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
            climate_id_for_unique = make_zone_entity_id(zone_to_remove)

            zone_unique_ids = [
                ("climate", f"{DOMAIN}_{self.config_entry.entry_id}_zone_{safe_name}"),
                ("select", f"{DOMAIN}_{self.config_entry.entry_id}_zone_mode_{climate_id_for_unique.replace('.', '_')}"),
                ("switch", f"{DOMAIN}_{self.config_entry.entry_id}_physical_sync_{safe_name}"),
                ("switch", f"{DOMAIN}_{self.config_entry.entry_id}_passive_heat_{safe_name}"),
                ("binary_sensor", f"{DOMAIN}_{self.config_entry.entry_id}_anomaly_{safe_name}"),
                ("binary_sensor", f"{DOMAIN}_{self.config_entry.entry_id}_anomaly_{climate_id_for_unique}"),
                ("sensor", f"{DOMAIN}_{self.config_entry.entry_id}_demand_{safe_name}"),
                ("sensor", f"{DOMAIN}_{self.config_entry.entry_id}_autotune_{safe_name}"),
                ("sensor", f"{DOMAIN}_{self.config_entry.entry_id}_heating_rate_{safe_name}"),
                ("sensor", f"{DOMAIN}_{self.config_entry.entry_id}_cooling_rate_{safe_name}"),
                ("sensor", f"{DOMAIN}_{self.config_entry.entry_id}_thermal_inertia_{safe_name}"),
                ("sensor", f"{DOMAIN}_{self.config_entry.entry_id}_energy_class_{safe_name}"),
                ("sensor", f"{DOMAIN}_{self.config_entry.entry_id}_thermal_retention_{safe_name}"),
                ("sensor", f"{DOMAIN}_{self.config_entry.entry_id}_radiator_sizing_{safe_name}"),
            ]
            for domain_name, unique_id in zone_unique_ids:
                ent_id = ent_reg.async_get_entity_id(domain_name, DOMAIN, unique_id)
                if ent_id:
                    ent_reg.async_remove(ent_id)
                    _LOGGER.debug("Removed orphaned %s entity %s from registry", domain_name, ent_id)
            
            return self._save_options()

        schema = get_zone_select_schema(zone_options)

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
                user_input = flatten_zone_user_input(user_input)
                climates = user_input.get(CONF_ZONE_CLIMATES, [])
                switches = user_input.get(CONF_ZONE_SWITCHES, [])
                valves = user_input.get(CONF_ZONE_VALVES, [])
                if not climates and not switches and not valves:
                    errors["base"] = "no_actuators_selected"
                else:
                    for i, z in enumerate(self._zones):
                        if z.get(CONF_ZONE_NAME, 'Unnamed Zone') == self._current_zone_name:
                            self._zones[i][CONF_ZONE_CLIMATES] = climates
                            self._zones[i][CONF_ZONE_SWITCHES] = switches
                            self._zones[i][CONF_ZONE_VALVES] = valves
                            self._zones[i][CONF_VALVE_SCALE] = user_input.get(CONF_VALVE_SCALE, DEFAULT_VALVE_SCALE)
                            self._zones[i][CONF_ZONE_TRV_SYNC] = user_input.get(CONF_ZONE_TRV_SYNC, DEFAULT_TRV_SYNC)
                            self._zones[i][CONF_ZONE_AUTHORITATIVE_SYNC] = user_input.get(CONF_ZONE_AUTHORITATIVE_SYNC, DEFAULT_AUTHORITATIVE_SYNC)
                            self._zones[i][CONF_ZONE_WEIGHT] = float(user_input.get(CONF_ZONE_WEIGHT, DEFAULT_ZONE_WEIGHT))
                            self._zones[i][CONF_ZONE_ANTI_SEIZE] = user_input.get(CONF_ZONE_ANTI_SEIZE, True)
                            self._zones[i][CONF_ZONE_ALLOW_PASSIVE_HEAT] = user_input.get(CONF_ZONE_ALLOW_PASSIVE_HEAT, False)
                            self._zones[i][CONF_ZONE_SENSOR_TIMEOUT] = user_input.get(CONF_ZONE_SENSOR_TIMEOUT, DEFAULT_SENSOR_TIMEOUT_MIN)
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
                            
                    if self._current_zone_data and CONF_ZONE_TEMP_SENSOR in self._current_zone_data and climates:
                        return await self.async_step_trv_calibration_edit()
                    
                    self._current_zone_name = None
                    self._current_zone_data = None
                    return self._save_options()
            else:
                # First step: select zone to edit
                self._current_zone_name = user_input["zone_name"]
                
        if self._current_zone_name is not None:
            zone_data = next((z for z in self._zones if z.get(CONF_ZONE_NAME, 'Unnamed Zone') == self._current_zone_name), None)
            if zone_data is None: zone_data = {}
            if errors and user_input is not None:
                zone_data = {**zone_data, **user_input}
            
            temp_sensor_val = zone_data.get(CONF_ZONE_TEMP_SENSOR)
            temp_desc = {"description": {"suggested_value": temp_sensor_val}} if temp_sensor_val and temp_sensor_val != "none" else {}
            
            window_sensor_val = zone_data.get(CONF_ZONE_WINDOW_SENSOR)
            window_desc = {"description": {"suggested_value": window_sensor_val}} if window_sensor_val and window_sensor_val != "none" else {}
            
            schema = get_options_edit_zone_schema(zone_data, temp_desc, window_desc)
            return self.async_show_form(step_id="edit_zone", data_schema=schema, errors=errors)

        zone_options = {z.get(CONF_ZONE_NAME, 'Unnamed Zone'): z.get(CONF_ZONE_NAME, 'Unnamed Zone') for z in self._zones}
        schema = get_zone_select_schema(zone_options)
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
            
        schema = get_options_trv_calibration_edit_schema(self._current_zone_data)
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
                errors.update(validate_geofencing(self._geofencing_enabled, self._presence_sensor))
                if not errors:
                    return self._save_options()
            else:
                self._presence_sensor = None
                return self._save_options()

        schema = get_options_edit_geofencing_schema(self._geofencing_enabled, self._presence_sensor)

        return self.async_show_form(
            step_id="edit_geofencing",
            data_schema=schema,
            errors=errors,
        )

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

        schema = get_options_edit_weather_comp_schema(self._weather_sensor, sensor_options)

        return self.async_show_form(
            step_id="edit_weather_comp",
            data_schema=schema,
        )

    async def async_step_edit_calendar(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Edit global calendar settings."""
        if user_input is not None:
            if user_input.get(CONF_GLOBAL_CALENDAR) and user_input[CONF_GLOBAL_CALENDAR] != "none":
                self._global_calendar = user_input[CONF_GLOBAL_CALENDAR]
            else:
                self._global_calendar = None
            return self._save_options()

        schema = get_options_edit_calendar_schema(self._global_calendar)

        return self.async_show_form(
            step_id="edit_calendar",
            data_schema=schema,
        )

    def _save_options(self) -> config_entries.FlowResult:
        """Save updated options into entry.data and reload entry."""
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

        self.hass.config_entries.async_update_entry(
            self.config_entry, data=data
        )
        
        if not getattr(self.config_entry, "update_listeners", None):
            self.hass.async_create_task(
                self.hass.config_entries.async_reload(self.config_entry.entry_id)
            )
        
        return self.async_create_entry(title="", data={})
