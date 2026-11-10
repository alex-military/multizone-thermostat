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
    CONF_DHW_ACTIVE_SENSOR,
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
    # Phase 11
    CONF_ENABLE_GAS_HEATER,
    CONF_ENABLE_HEAT_PUMP,
    CONF_HEAT_PUMP_TYPE,
    HP_TYPE_CLIMATE,
    HP_TYPE_SWITCH,
    HP_TYPE_OPENTHERM,
    CONF_HEAT_PUMP_ENTITY,
    CONF_HEAT_PUMP_CH_SWITCH,
    CONF_HEAT_PUMP_MIN_TEMP,
    CONF_HEAT_PUMP_MAX_TEMP,
    CONF_HEAT_PUMP_COOLING,
    DEFAULT_HEAT_PUMP_COOLING,
    CONF_HEAT_PUMP_COOL_MIN_TEMP,
    CONF_HEAT_PUMP_COOL_MAX_TEMP,
    DEFAULT_HP_COOL_MIN_TEMP,
    DEFAULT_HP_COOL_MAX_TEMP,
    CONF_ZONE_SPLIT_CLIMATE,
    CONF_ZONE_SPLIT_ROLE,
    DEFAULT_SPLIT_ROLE,
    CONF_ZONE_SPLIT_SOLAR_PRIORITY,
    DEFAULT_SPLIT_SOLAR_PRIORITY,
    CONF_ZONE_SPLIT_QUICK_BOOST,
    DEFAULT_SPLIT_QUICK_BOOST,
    CONF_ZONE_SPLIT_BOOST_DELTA,
    DEFAULT_SPLIT_BOOST_DELTA,
    CONF_ZONE_SPLIT_SENSOR_INJECTION,
    DEFAULT_SPLIT_SENSOR_INJECTION,
    CONF_ENERGY_MANAGEMENT_ENABLED,
    CONF_SOLAR_POWER_SENSOR,
    CONF_GRID_EXPORT_SENSOR,
    CONF_BATTERY_SOC_SENSOR,
    CONF_EXTERNAL_SOLAR_OVERRIDE_ENTITY,
    CONF_SOLAR_EXPORT_THRESHOLD,
    DEFAULT_SOLAR_EXPORT_THRESHOLD,
    CONF_BATTERY_MIN_RESERVE_SOC,
    DEFAULT_BATTERY_MIN_RESERVE_SOC,
    CONF_BATTERY_POWER_SENSOR,
    CONF_SOLAR_FORECAST_SENSOR,
    CONF_SOLAR_IRRADIANCE_SENSOR,
    CONF_BATTERY_MAX_DISCHARGE_TIME,
    DEFAULT_BATTERY_MAX_DISCHARGE_TIME,
    CONF_BATTERY_POWER_INVERTED,
    DEFAULT_BATTERY_POWER_INVERTED,
    CONF_SOLAR_MIN_RUN_TIME,
    DEFAULT_SOLAR_MIN_RUN_TIME,
    CONF_SOLAR_OVERHEAT_OFFSET,
    DEFAULT_SOLAR_OVERHEAT_OFFSET,
)

_LOGGER = logging.getLogger(__name__)

from .validators import (
    validate_opentherm_temps,
    validate_zone_input,
    validate_geofencing,
    validate_plants_selection,
    validate_heat_pump_temps,
)
from ..plant_diagnostics.anomalies import find_suggested_dhw_sensor
from .schemas import *
from .helpers import (
    _get_switch_entities,
    _get_climate_entities,
    _get_binary_sensor_entities,
    _get_temperature_sensor_entities,
    _remove_entity_from_registry,
    flatten_zone_user_input,
)
from .options_flow import MultizoneOptionsFlow


class MultizoneConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Multizone Thermostat."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._enable_gas: bool = True
        self._enable_hp: bool = False
        self._boiler_mode: str = MODE_RELAY
        self._boiler_switch: str | None = None
        self._opentherm_entity: str | None = None
        self._opentherm_min_temp: float = 35.0
        self._opentherm_max_temp: float = 75.0
        self._opentherm_ch_switch: str | None = None
        self._dhw_active_sensor: str | None = None
        # Heat pump
        self._hp_type: str = HP_TYPE_CLIMATE
        self._hp_entity: str | None = None
        self._hp_min_temp: float = 25.0
        self._hp_max_temp: float = 55.0
        self._hp_ch_switch: str | None = None
        self._hp_cooling: bool = DEFAULT_HEAT_PUMP_COOLING
        self._hp_cool_min_temp: float = DEFAULT_HP_COOL_MIN_TEMP
        self._hp_cool_max_temp: float = DEFAULT_HP_COOL_MAX_TEMP
        # Energy management
        self._energy_management_enabled: bool = False
        self._solar_power_sensor: str | None = None
        self._grid_export_sensor: str | None = None
        self._battery_soc_sensor: str | None = None
        self._external_solar_override_entity: str | None = None
        self._solar_export_threshold: float = DEFAULT_SOLAR_EXPORT_THRESHOLD
        self._battery_min_reserve_soc: float = DEFAULT_BATTERY_MIN_RESERVE_SOC
        self._battery_power_sensor: str | None = None
        self._solar_forecast_sensor: str | None = None
        self._solar_irradiance_sensor: str | None = None
        self._battery_max_discharge_time: float = DEFAULT_BATTERY_MAX_DISCHARGE_TIME
        self._battery_power_inverted: bool = DEFAULT_BATTERY_POWER_INVERTED
        self._solar_min_run_time: float = DEFAULT_SOLAR_MIN_RUN_TIME
        self._solar_overheat_offset: float = DEFAULT_SOLAR_OVERHEAT_OFFSET
        # Zones & extras
        self._zones: list[dict] = []
        self._geofencing_enabled: bool = True
        self._presence_sensor: str | None = None
        self._weather_sensor: str | None = None
        self._global_calendar: str | None = None
        self._current_zone_data: dict[str, Any] | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step 1: Select Central Heating Plants (Gas and/or Heat Pump)."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}
        if user_input is not None:
            if CONF_BOILER_MODE in user_input and CONF_ENABLE_GAS_HEATER not in user_input:
                # Direct backward compatibility with boiler mode
                self._enable_gas = True
                self._enable_hp = False
                self._boiler_mode = user_input[CONF_BOILER_MODE]
                if self._boiler_mode == MODE_RELAY:
                    return await self.async_step_boiler_relay()
                else:
                    return await self.async_step_boiler_opentherm()

            self._enable_gas = user_input.get(CONF_ENABLE_GAS_HEATER, True)
            self._enable_hp = user_input.get(CONF_ENABLE_HEAT_PUMP, False)
            errors.update(validate_plants_selection(self._enable_gas, self._enable_hp))
            if not errors:
                if self._enable_gas:
                    return await self.async_step_boiler_mode()
                else:
                    return await self.async_step_heat_pump()

        schema = get_plants_selection_schema(self._enable_gas, self._enable_hp)
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_boiler_mode(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Select gas boiler mode (Relay vs OpenTherm)."""
        if user_input is not None:
            self._boiler_mode = user_input[CONF_BOILER_MODE]
            if self._boiler_mode == MODE_RELAY:
                return await self.async_step_boiler_relay()
            else:
                return await self.async_step_boiler_opentherm()

        schema = get_boiler_mode_schema()
        return self.async_show_form(
            step_id="boiler_mode",
            data_schema=schema,
        )

    async def async_step_boiler_relay(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step: Select boiler relay."""
        errors: dict[str, str] = {}
        switches = _get_switch_entities(self.hass)

        if not switches:
            return self.async_abort(reason="no_switches_found")

        if user_input is not None:
            self._boiler_switch = user_input[CONF_BOILER_SWITCH]
            self._dhw_active_sensor = user_input.get(CONF_DHW_ACTIVE_SENSOR) or None
            if self._enable_hp:
                return await self.async_step_heat_pump()
            return await self.async_step_add_zone()

        suggested_dhw = self._dhw_active_sensor or find_suggested_dhw_sensor(self.hass)
        schema = get_boiler_relay_schema(suggested_dhw)
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
        """Step: Select OpenTherm entity."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._opentherm_entity = user_input[CONF_OPENTHERM_ENTITY]
            self._opentherm_min_temp = user_input[CONF_OPENTHERM_MIN_TEMP]
            self._opentherm_max_temp = user_input[CONF_OPENTHERM_MAX_TEMP]
            self._opentherm_ch_switch = user_input.get(CONF_OPENTHERM_CH_SWITCH) or None
            self._dhw_active_sensor = user_input.get(CONF_DHW_ACTIVE_SENSOR) or None
            errors.update(validate_opentherm_temps(self._opentherm_min_temp, self._opentherm_max_temp))
            if not errors:
                if self._enable_hp:
                    return await self.async_step_heat_pump()
                return await self.async_step_add_zone()

        suggested_dhw = self._dhw_active_sensor or find_suggested_dhw_sensor(self.hass, self._opentherm_entity)
        schema = get_boiler_opentherm_schema(suggested_dhw)
        return self.async_show_form(
            step_id="boiler_opentherm",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_heat_pump(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step: Configure Heat Pump (PDC)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._hp_type = user_input[CONF_HEAT_PUMP_TYPE]
            self._hp_entity = user_input[CONF_HEAT_PUMP_ENTITY]
            self._hp_min_temp = user_input.get(CONF_HEAT_PUMP_MIN_TEMP, 25.0)
            self._hp_max_temp = user_input.get(CONF_HEAT_PUMP_MAX_TEMP, 55.0)
            self._hp_ch_switch = user_input.get(CONF_HEAT_PUMP_CH_SWITCH) or None
            self._hp_cooling = user_input.get(CONF_HEAT_PUMP_COOLING, DEFAULT_HEAT_PUMP_COOLING)
            self._hp_cool_min_temp = user_input.get(CONF_HEAT_PUMP_COOL_MIN_TEMP, DEFAULT_HP_COOL_MIN_TEMP)
            self._hp_cool_max_temp = user_input.get(CONF_HEAT_PUMP_COOL_MAX_TEMP, DEFAULT_HP_COOL_MAX_TEMP)
            errors.update(validate_heat_pump_temps(self._hp_min_temp, self._hp_max_temp))
            if not errors:
                return await self.async_step_add_zone()

        schema = get_heat_pump_schema(
            self._hp_type,
            self._hp_entity,
            self._hp_min_temp,
            self._hp_max_temp,
            self._hp_ch_switch,
            self._hp_cooling,
            self._hp_cool_min_temp,
            self._hp_cool_max_temp,
        )
        return self.async_show_form(
            step_id="heat_pump",
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
            split_climate = user_input.get(CONF_ZONE_SPLIT_CLIMATE)
            if split_climate == "none":
                split_climate = None
            
            errors.update(validate_zone_input(zone_name, climates, switches, already_added, valves=valves, split_climate=split_climate))
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
                    # Phase 11 Split Settings
                    CONF_ZONE_SPLIT_CLIMATE: split_climate,
                    CONF_ZONE_SPLIT_ROLE: user_input.get(CONF_ZONE_SPLIT_ROLE, DEFAULT_SPLIT_ROLE),
                    CONF_ZONE_SPLIT_SOLAR_PRIORITY: user_input.get(CONF_ZONE_SPLIT_SOLAR_PRIORITY, DEFAULT_SPLIT_SOLAR_PRIORITY),
                    CONF_ZONE_SPLIT_QUICK_BOOST: user_input.get(CONF_ZONE_SPLIT_QUICK_BOOST, DEFAULT_SPLIT_QUICK_BOOST),
                    CONF_ZONE_SPLIT_BOOST_DELTA: float(user_input.get(CONF_ZONE_SPLIT_BOOST_DELTA, DEFAULT_SPLIT_BOOST_DELTA)),
                    CONF_ZONE_SPLIT_SENSOR_INJECTION: user_input.get(CONF_ZONE_SPLIT_SENSOR_INJECTION, DEFAULT_SPLIT_SENSOR_INJECTION),
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
                    return await self.async_step_energy_management()
            else:
                self._presence_sensor = None
                return await self.async_step_energy_management()

        schema = get_geofencing_schema()
        return self.async_show_form(
            step_id="geofencing",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_energy_management(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step: Energy & Solar Surplus Setup (Phase 11)."""
        if user_input is not None:
            self._energy_management_enabled = user_input.get(CONF_ENERGY_MANAGEMENT_ENABLED, False)
            if self._energy_management_enabled:
                self._solar_power_sensor = user_input.get(CONF_SOLAR_POWER_SENSOR)
                self._grid_export_sensor = user_input.get(CONF_GRID_EXPORT_SENSOR)
                self._battery_soc_sensor = user_input.get(CONF_BATTERY_SOC_SENSOR)
                self._external_solar_override_entity = user_input.get(CONF_EXTERNAL_SOLAR_OVERRIDE_ENTITY)
                self._solar_export_threshold = float(user_input.get(CONF_SOLAR_EXPORT_THRESHOLD, DEFAULT_SOLAR_EXPORT_THRESHOLD))
                self._battery_min_reserve_soc = float(user_input.get(CONF_BATTERY_MIN_RESERVE_SOC, DEFAULT_BATTERY_MIN_RESERVE_SOC))
                self._battery_power_sensor = user_input.get(CONF_BATTERY_POWER_SENSOR)
                self._solar_forecast_sensor = user_input.get(CONF_SOLAR_FORECAST_SENSOR)
                self._solar_irradiance_sensor = user_input.get(CONF_SOLAR_IRRADIANCE_SENSOR)
                self._battery_max_discharge_time = float(user_input.get(CONF_BATTERY_MAX_DISCHARGE_TIME, DEFAULT_BATTERY_MAX_DISCHARGE_TIME))
                self._battery_power_inverted = bool(user_input.get(CONF_BATTERY_POWER_INVERTED, DEFAULT_BATTERY_POWER_INVERTED))
                self._solar_min_run_time = float(user_input.get(CONF_SOLAR_MIN_RUN_TIME, DEFAULT_SOLAR_MIN_RUN_TIME))
                self._solar_overheat_offset = float(user_input.get(CONF_SOLAR_OVERHEAT_OFFSET, DEFAULT_SOLAR_OVERHEAT_OFFSET))
            return await self.async_step_confirm()

        schema = get_energy_management_schema(
            enabled=self._energy_management_enabled,
            solar_power_sensor=self._solar_power_sensor,
            grid_export_sensor=self._grid_export_sensor,
            battery_soc_sensor=self._battery_soc_sensor,
            battery_power_sensor=self._battery_power_sensor,
            solar_forecast_sensor=self._solar_forecast_sensor,
            solar_irradiance_sensor=self._solar_irradiance_sensor,
            external_override_entity=self._external_solar_override_entity,
            export_threshold=self._solar_export_threshold,
            min_reserve_soc=self._battery_min_reserve_soc,
            solar_min_run_time=self._solar_min_run_time,
            solar_overheat_offset=self._solar_overheat_offset,
            battery_max_discharge_time=self._battery_max_discharge_time,
            battery_power_inverted=self._battery_power_inverted,
        )
        return self.async_show_form(
            step_id="energy_management",
            data_schema=schema,
        )

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step: Confirm configuration."""
        if not self._zones:
            return self.async_abort(reason="no_zones_configured")

        if user_input is not None:
            data: dict[str, Any] = {
                CONF_ENABLE_GAS_HEATER: self._enable_gas,
                CONF_ENABLE_HEAT_PUMP: self._enable_hp,
                CONF_ZONES: self._zones,
                CONF_GEOFENCING_ENABLED: self._geofencing_enabled,
            }
            if self._enable_gas:
                data[CONF_BOILER_MODE] = self._boiler_mode
                if self._boiler_mode == MODE_RELAY:
                    data[CONF_BOILER_SWITCH] = self._boiler_switch
                else:
                    data[CONF_OPENTHERM_ENTITY] = self._opentherm_entity
                    data[CONF_OPENTHERM_MIN_TEMP] = self._opentherm_min_temp
                    data[CONF_OPENTHERM_MAX_TEMP] = self._opentherm_max_temp
                    if self._opentherm_ch_switch:
                        data[CONF_OPENTHERM_CH_SWITCH] = self._opentherm_ch_switch
                if self._dhw_active_sensor:
                    data[CONF_DHW_ACTIVE_SENSOR] = self._dhw_active_sensor
            if self._enable_hp:
                data[CONF_HEAT_PUMP_TYPE] = self._hp_type
                data[CONF_HEAT_PUMP_ENTITY] = self._hp_entity
                data[CONF_HEAT_PUMP_MIN_TEMP] = self._hp_min_temp
                data[CONF_HEAT_PUMP_MAX_TEMP] = self._hp_max_temp
                data[CONF_HEAT_PUMP_COOLING] = self._hp_cooling
                data[CONF_HEAT_PUMP_COOL_MIN_TEMP] = self._hp_cool_min_temp
                data[CONF_HEAT_PUMP_COOL_MAX_TEMP] = self._hp_cool_max_temp
                if self._hp_ch_switch:
                    data[CONF_HEAT_PUMP_CH_SWITCH] = self._hp_ch_switch
            if self._geofencing_enabled and self._presence_sensor:
                data[CONF_PRESENCE_SENSOR] = self._presence_sensor
            if self._weather_sensor:
                data[CONF_WEATHER_SENSOR] = self._weather_sensor
            if self._global_calendar:
                data[CONF_GLOBAL_CALENDAR] = self._global_calendar
            if self._energy_management_enabled:
                data[CONF_ENERGY_MANAGEMENT_ENABLED] = True
                if self._solar_power_sensor:
                    data[CONF_SOLAR_POWER_SENSOR] = self._solar_power_sensor
                if self._grid_export_sensor:
                    data[CONF_GRID_EXPORT_SENSOR] = self._grid_export_sensor
                if self._battery_soc_sensor:
                    data[CONF_BATTERY_SOC_SENSOR] = self._battery_soc_sensor
                if self._battery_power_sensor:
                    data[CONF_BATTERY_POWER_SENSOR] = self._battery_power_sensor
                if self._solar_forecast_sensor:
                    data[CONF_SOLAR_FORECAST_SENSOR] = self._solar_forecast_sensor
                if self._solar_irradiance_sensor:
                    data[CONF_SOLAR_IRRADIANCE_SENSOR] = self._solar_irradiance_sensor
                if self._external_solar_override_entity:
                    data[CONF_EXTERNAL_SOLAR_OVERRIDE_ENTITY] = self._external_solar_override_entity
                data[CONF_SOLAR_EXPORT_THRESHOLD] = self._solar_export_threshold
                data[CONF_BATTERY_MIN_RESERVE_SOC] = self._battery_min_reserve_soc
                data[CONF_BATTERY_MAX_DISCHARGE_TIME] = self._battery_max_discharge_time
                data[CONF_BATTERY_POWER_INVERTED] = self._battery_power_inverted
                data[CONF_SOLAR_MIN_RUN_TIME] = self._solar_min_run_time
                data[CONF_SOLAR_OVERHEAT_OFFSET] = self._solar_overheat_offset

            return self.async_create_entry(
                title="Multizone Thermostat",
                data=data,
            )

        schema = get_confirm_schema()
        plant_desc = []
        if self._enable_gas:
            plant_desc.append(f"Gas: {self._boiler_switch or self._opentherm_entity or 'N/A'}")
        if self._enable_hp:
            plant_desc.append(f"Heat Pump: {self._hp_entity or 'N/A'} ({self._hp_type})")

        return self.async_show_form(
            step_id="confirm",
            data_schema=schema,
            description_placeholders={
                "boiler_switch": ", ".join(plant_desc) if plant_desc else "N/A",
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
