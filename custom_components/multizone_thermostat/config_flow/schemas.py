from typing import Any
import voluptuous as vol

from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.helpers import selector

from homeassistant import data_entry_flow

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
    VALVE_SCALE_PERCENT,
    VALVE_SCALE_VOLT,
    DEFAULT_VALVE_SCALE,
    CONF_ZONE_TEMP_SENSOR,
    CONF_ZONE_TARGET_TEMP,
    CONF_ZONE_TRV_SYNC,
    CONF_ZONE_WINDOW_SENSOR,
    CONF_ZONE_ANTI_SEIZE,
    CONF_ZONE_ALLOW_PASSIVE_HEAT,
    CONF_ZONE_SENSOR_TIMEOUT,
    DEFAULT_SENSOR_TIMEOUT_MIN,
    CONF_WEATHER_SENSOR,
    CONF_GLOBAL_CALENDAR,
    DEFAULT_TRV_SYNC,
    MODE_OPENTHERM,
    MODE_RELAY,
    CONF_ZONE_CALIBRATIONS,
)


def get_boiler_mode_schema() -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_BOILER_MODE, default=MODE_RELAY): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(value=MODE_RELAY, label="Relay (ON/OFF)"),
                    selector.SelectOptionDict(value=MODE_OPENTHERM, label="OpenTherm (Modulating)"),
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
    })


def get_boiler_relay_schema() -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_BOILER_SWITCH): selector.EntitySelector(selector.EntitySelectorConfig(domain=SWITCH_DOMAIN)),
    })


def get_boiler_opentherm_schema() -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_OPENTHERM_ENTITY): selector.EntitySelector(selector.EntitySelectorConfig(domain=["climate", "water_heater", "number"])),
        vol.Required(CONF_OPENTHERM_MIN_TEMP, default=35.0): selector.NumberSelector(
            selector.NumberSelectorConfig(min=20, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Required(CONF_OPENTHERM_MAX_TEMP, default=75.0): selector.NumberSelector(
            selector.NumberSelectorConfig(min=20, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_OPENTHERM_CH_SWITCH): selector.EntitySelector(selector.EntitySelectorConfig(domain=SWITCH_DOMAIN)),
    })


def get_add_zone_schema() -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_ZONE_NAME): str,
        vol.Optional(CONF_ZONE_TEMP_SENSOR): selector.EntitySelector(selector.EntitySelectorConfig(domain=SENSOR_DOMAIN, device_class="temperature")),
        vol.Optional(CONF_ZONE_TARGET_TEMP, default=20.0): selector.NumberSelector(selector.NumberSelectorConfig(min=5, max=35, step=0.5, mode=selector.NumberSelectorMode.BOX)),
        
        # Section 1: TRV Standard
        vol.Optional("trv_settings"): data_entry_flow.section(
            vol.Schema({
                vol.Optional(CONF_ZONE_CLIMATES, default=[]): selector.EntitySelector(selector.EntitySelectorConfig(domain=CLIMATE_DOMAIN, multiple=True)),
                vol.Optional(CONF_ZONE_TRV_SYNC, default=DEFAULT_TRV_SYNC): bool,
            }),
            {"collapsed": True},
        ),

        # Section 2: Valvole Proporzionali / 0-10V
        vol.Optional("valve_settings"): data_entry_flow.section(
            vol.Schema({
                vol.Optional(CONF_ZONE_VALVES, default=[]): selector.EntitySelector(selector.EntitySelectorConfig(domain=["number", "valve"], multiple=True)),
                vol.Optional(CONF_VALVE_SCALE, default=DEFAULT_VALVE_SCALE): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=VALVE_SCALE_PERCENT, label="Percentage (0 - 100%)"),
                            selector.SelectOptionDict(value=VALVE_SCALE_VOLT, label="Voltage (0.0 - 10.0 V)"),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }),
            {"collapsed": True},
        ),

        # Section 3: Attuatori a Relè (PWM)
        vol.Optional("relay_settings"): data_entry_flow.section(
            vol.Schema({
                vol.Optional(CONF_ZONE_SWITCHES, default=[]): selector.EntitySelector(selector.EntitySelectorConfig(domain=SWITCH_DOMAIN, multiple=True)),
            }),
            {"collapsed": True},
        ),

        # Section 4: Protezioni & Funzioni Avanzate
        vol.Optional("safety_settings"): data_entry_flow.section(
            vol.Schema({
                vol.Optional(CONF_ZONE_WINDOW_SENSOR): selector.EntitySelector(selector.EntitySelectorConfig(domain=BINARY_SENSOR_DOMAIN)),
                vol.Optional(CONF_ZONE_SENSOR_TIMEOUT, default=DEFAULT_SENSOR_TIMEOUT_MIN): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=10, max=720, step=5, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Optional(CONF_ZONE_ANTI_SEIZE, default=True): bool,
                vol.Optional(CONF_ZONE_ALLOW_PASSIVE_HEAT, default=False): bool,
            }),
            {"collapsed": True},
        ),
    })


def get_trv_calibration_schema(current_zone_data: dict[str, Any] | None) -> vol.Schema:
    schema_dict = {}
    climates = current_zone_data.get(CONF_ZONE_CLIMATES, []) if current_zone_data else []
    for climate_id in climates:
        schema_dict[vol.Optional(climate_id)] = selector.EntitySelector(selector.EntitySelectorConfig(domain=["number", "input_number"]))
    return vol.Schema(schema_dict)


def get_another_zone_schema() -> vol.Schema:
    return vol.Schema({
        vol.Required("add_another", default=False): bool,
    })


def get_calendar_schema() -> vol.Schema:
    return vol.Schema({
        vol.Optional(CONF_GLOBAL_CALENDAR): selector.EntitySelector(selector.EntitySelectorConfig(domain="calendar")),
    })


def get_weather_schema(sensor_options: dict[str, str]) -> vol.Schema:
    return vol.Schema({
        vol.Optional(CONF_WEATHER_SENSOR, default="none"): vol.In(sensor_options),
    })


def get_geofencing_schema() -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_GEOFENCING_ENABLED, default=True): bool,
        vol.Optional(CONF_PRESENCE_SENSOR, default="zone.home"): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["person", "group", "zone", "device_tracker", "binary_sensor", "input_boolean"])
        ),
    })


def get_confirm_schema() -> vol.Schema:
    return vol.Schema({})


def get_options_init_schema(menu_options: dict[str, str]) -> vol.Schema:
    return vol.Schema({
        vol.Required("action"): vol.In(menu_options),
    })


def get_options_change_boiler_schema(boiler_mode: str) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_BOILER_MODE, default=boiler_mode): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(value=MODE_RELAY, label="Relay (ON/OFF)"),
                    selector.SelectOptionDict(value=MODE_OPENTHERM, label="OpenTherm (Modulating)"),
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
    })


def get_options_boiler_relay_schema(boiler_switch: str) -> vol.Schema:
    schema_dict = {}
    if boiler_switch:
        schema_dict[vol.Required(CONF_BOILER_SWITCH, default=boiler_switch)] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=SWITCH_DOMAIN)
        )
    else:
        schema_dict[vol.Required(CONF_BOILER_SWITCH)] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=SWITCH_DOMAIN)
        )
    return vol.Schema(schema_dict)


def get_options_boiler_opentherm_schema(
    opentherm_entity: str | None,
    opentherm_min_temp: float,
    opentherm_max_temp: float,
    opentherm_ch_switch: str | None = None,
) -> vol.Schema:
    schema_dict = {}
    if opentherm_entity:
        schema_dict[vol.Required(CONF_OPENTHERM_ENTITY, default=opentherm_entity)] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["climate", "water_heater", "number"])
        )
    else:
        schema_dict[vol.Required(CONF_OPENTHERM_ENTITY)] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["climate", "water_heater", "number"])
        )
    schema_dict[vol.Required(CONF_OPENTHERM_MIN_TEMP, default=opentherm_min_temp)] = selector.NumberSelector(
        selector.NumberSelectorConfig(min=20, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
    )
    schema_dict[vol.Required(CONF_OPENTHERM_MAX_TEMP, default=opentherm_max_temp)] = selector.NumberSelector(
        selector.NumberSelectorConfig(min=20, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
    )
    ch_key = (
        vol.Optional(CONF_OPENTHERM_CH_SWITCH, description={"suggested_value": opentherm_ch_switch})
        if opentherm_ch_switch
        else vol.Optional(CONF_OPENTHERM_CH_SWITCH)
    )
    schema_dict[ch_key] = selector.EntitySelector(selector.EntitySelectorConfig(domain=SWITCH_DOMAIN))
    return vol.Schema(schema_dict)


def get_zone_select_schema(zone_options: dict[str, str]) -> vol.Schema:
    return vol.Schema({
        vol.Required("zone_name"): vol.In(zone_options),
    })


def get_options_edit_zone_schema(zone_data: dict[str, Any], temp_desc: dict[str, Any], window_desc: dict[str, Any]) -> vol.Schema:
    return vol.Schema({
        vol.Optional(CONF_ZONE_TEMP_SENSOR, **temp_desc): selector.EntitySelector(selector.EntitySelectorConfig(domain=SENSOR_DOMAIN, device_class="temperature")),
        vol.Optional(CONF_ZONE_TARGET_TEMP, default=zone_data.get(CONF_ZONE_TARGET_TEMP, 20.0)): selector.NumberSelector(selector.NumberSelectorConfig(min=5, max=35, step=0.5, mode=selector.NumberSelectorMode.BOX)),

        # Section 1: TRV Standard
        vol.Optional("trv_settings"): data_entry_flow.section(
            vol.Schema({
                vol.Optional(CONF_ZONE_CLIMATES, default=zone_data.get(CONF_ZONE_CLIMATES, [])): selector.EntitySelector(selector.EntitySelectorConfig(domain=CLIMATE_DOMAIN, multiple=True)),
                vol.Optional(CONF_ZONE_TRV_SYNC, default=zone_data.get(CONF_ZONE_TRV_SYNC, DEFAULT_TRV_SYNC)): bool,
            }),
            {"collapsed": True},
        ),

        # Section 2: Valvole Proporzionali / 0-10V
        vol.Optional("valve_settings"): data_entry_flow.section(
            vol.Schema({
                vol.Optional(CONF_ZONE_VALVES, default=zone_data.get(CONF_ZONE_VALVES, [])): selector.EntitySelector(selector.EntitySelectorConfig(domain=["number", "valve"], multiple=True)),
                vol.Optional(CONF_VALVE_SCALE, default=zone_data.get(CONF_VALVE_SCALE, DEFAULT_VALVE_SCALE)): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=VALVE_SCALE_PERCENT, label="Percentage (0 - 100%)"),
                            selector.SelectOptionDict(value=VALVE_SCALE_VOLT, label="Voltage (0.0 - 10.0 V)"),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }),
            {"collapsed": True},
        ),

        # Section 3: Attuatori a Relè (PWM)
        vol.Optional("relay_settings"): data_entry_flow.section(
            vol.Schema({
                vol.Optional(CONF_ZONE_SWITCHES, default=zone_data.get(CONF_ZONE_SWITCHES, [])): selector.EntitySelector(selector.EntitySelectorConfig(domain=SWITCH_DOMAIN, multiple=True)),
            }),
            {"collapsed": True},
        ),

        # Section 4: Protezioni & Funzioni Avanzate
        vol.Optional("safety_settings"): data_entry_flow.section(
            vol.Schema({
                vol.Optional(CONF_ZONE_WINDOW_SENSOR, **window_desc): selector.EntitySelector(selector.EntitySelectorConfig(domain=BINARY_SENSOR_DOMAIN)),
                vol.Optional(CONF_ZONE_SENSOR_TIMEOUT, default=zone_data.get(CONF_ZONE_SENSOR_TIMEOUT, DEFAULT_SENSOR_TIMEOUT_MIN)): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=10, max=720, step=5, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Optional(CONF_ZONE_ANTI_SEIZE, default=zone_data.get(CONF_ZONE_ANTI_SEIZE, True)): bool,
                vol.Optional(CONF_ZONE_ALLOW_PASSIVE_HEAT, default=zone_data.get(CONF_ZONE_ALLOW_PASSIVE_HEAT, False)): bool,
            }),
            {"collapsed": True},
        ),
    })


def get_options_trv_calibration_edit_schema(current_zone_data: dict[str, Any] | None) -> vol.Schema:
    schema_dict = {}
    climates = current_zone_data.get(CONF_ZONE_CLIMATES, []) if current_zone_data else []
    current_calibrations = current_zone_data.get(CONF_ZONE_CALIBRATIONS, {}) if current_zone_data else {}
    for climate_id in climates:
        default_val = current_calibrations.get(climate_id)
        if default_val:
            schema_dict[vol.Optional(climate_id, description={"suggested_value": default_val})] = selector.EntitySelector(selector.EntitySelectorConfig(domain=["number", "input_number"]))
        else:
            schema_dict[vol.Optional(climate_id)] = selector.EntitySelector(selector.EntitySelectorConfig(domain=["number", "input_number"]))
        
    return vol.Schema(schema_dict)


def get_options_edit_geofencing_schema(geofencing_enabled: bool, presence_sensor: str | None) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_GEOFENCING_ENABLED, default=geofencing_enabled): bool,
        vol.Optional(CONF_PRESENCE_SENSOR, default=presence_sensor or "zone.home"): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["person", "group", "zone", "device_tracker", "binary_sensor", "input_boolean"])
        ),
    })


def get_options_edit_weather_comp_schema(weather_sensor: str | None, sensor_options: dict[str, str]) -> vol.Schema:
    return vol.Schema({
        vol.Optional(
            CONF_WEATHER_SENSOR, 
            default=weather_sensor or "none"
        ): vol.In(sensor_options),
    })


def get_options_edit_calendar_schema(global_calendar: str | None) -> vol.Schema:
    if global_calendar and global_calendar != "none":
        return vol.Schema({
            vol.Optional(
                CONF_GLOBAL_CALENDAR, 
                description={"suggested_value": global_calendar}
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="calendar")),
        })
    else:
        return vol.Schema({
            vol.Optional(CONF_GLOBAL_CALENDAR): selector.EntitySelector(selector.EntitySelectorConfig(domain="calendar")),
        })
