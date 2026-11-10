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
    CONF_ZONE_EMITTER_TYPE,
    EMITTER_TYPE_RADIATOR,
    EMITTER_TYPE_UNDERFLOOR,
    EMITTER_TYPE_FANCOIL,
    DEFAULT_ZONE_EMITTER_TYPE,
    CONF_HAS_MIXING_VALVE,
    DEFAULT_HAS_MIXING_VALVE,
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
    CONF_ZONE_WEIGHT,
    DEFAULT_ZONE_WEIGHT,
    CONF_ZONE_AUTHORITATIVE_SYNC,
    DEFAULT_AUTHORITATIVE_SYNC,
    # Phase 11 — Central Heating Plants
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
    # Phase 11 — Zone Split Climate Actuators
    CONF_ZONE_SPLIT_CLIMATE,
    CONF_ZONE_SPLIT_ROLE,
    SPLIT_ROLE_HEAT_COOL,
    SPLIT_ROLE_HEATING_ONLY,
    SPLIT_ROLE_COOLING_ONLY,
    DEFAULT_SPLIT_ROLE,
    CONF_ZONE_SPLIT_SOLAR_PRIORITY,
    DEFAULT_SPLIT_SOLAR_PRIORITY,
    CONF_ZONE_SPLIT_QUICK_BOOST,
    DEFAULT_SPLIT_QUICK_BOOST,
    CONF_ZONE_SPLIT_BOOST_DELTA,
    DEFAULT_SPLIT_BOOST_DELTA,
    CONF_ZONE_SPLIT_SENSOR_INJECTION,
    DEFAULT_SPLIT_SENSOR_INJECTION,
    # Phase 11 — Energy Management & Solar
    CONF_ENERGY_MANAGEMENT_ENABLED,
    CONF_SOLAR_POWER_SENSOR,
    CONF_GRID_EXPORT_SENSOR,
    CONF_BATTERY_SOC_SENSOR,
    CONF_EXTERNAL_SOLAR_OVERRIDE_ENTITY,
    CONF_SOLAR_EXPORT_THRESHOLD,
    DEFAULT_SOLAR_EXPORT_THRESHOLD,
    CONF_BATTERY_MIN_RESERVE_SOC,
    DEFAULT_BATTERY_MIN_RESERVE_SOC,
    CONF_SOLAR_MIN_RUN_TIME,
    DEFAULT_SOLAR_MIN_RUN_TIME,
    CONF_SOLAR_OVERHEAT_OFFSET,
    DEFAULT_SOLAR_OVERHEAT_OFFSET,
    CONF_BATTERY_POWER_SENSOR,
    CONF_SOLAR_FORECAST_SENSOR,
    CONF_SOLAR_IRRADIANCE_SENSOR,
    CONF_BATTERY_MAX_DISCHARGE_TIME,
    DEFAULT_BATTERY_MAX_DISCHARGE_TIME,
    CONF_BATTERY_POWER_INVERTED,
    DEFAULT_BATTERY_POWER_INVERTED,
)


def get_plants_selection_schema(
    enable_gas: bool = True,
    enable_hp: bool = False,
) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_ENABLE_GAS_HEATER, default=enable_gas): bool,
        vol.Required(CONF_ENABLE_HEAT_PUMP, default=enable_hp): bool,
    })


def get_heat_pump_schema(
    hp_type: str = HP_TYPE_CLIMATE,
    hp_entity: str | None = None,
    hp_min_temp: float = 25.0,
    hp_max_temp: float = 55.0,
    hp_ch_switch: str | None = None,
    hp_cooling: bool = DEFAULT_HEAT_PUMP_COOLING,
    hp_cool_min_temp: float = DEFAULT_HP_COOL_MIN_TEMP,
    hp_cool_max_temp: float = DEFAULT_HP_COOL_MAX_TEMP,
    has_mixing_valve: bool = DEFAULT_HAS_MIXING_VALVE,
) -> vol.Schema:
    schema_dict: dict[Any, Any] = {
        vol.Required(CONF_HEAT_PUMP_TYPE, default=hp_type): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(value=HP_TYPE_CLIMATE, label="Climate Entity (HA Native Climate)"),
                    selector.SelectOptionDict(value=HP_TYPE_SWITCH, label="Switch / Relay / SG-Ready (ON/OFF)"),
                    selector.SelectOptionDict(value=HP_TYPE_OPENTHERM, label="OpenTherm (Modulating Gateway)"),
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
    }
    entity_key = (
        vol.Required(CONF_HEAT_PUMP_ENTITY, default=hp_entity)
        if hp_entity
        else vol.Required(CONF_HEAT_PUMP_ENTITY)
    )
    schema_dict[entity_key] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["climate", "switch", "number", "water_heater"])
    )
    schema_dict[vol.Required(CONF_HEAT_PUMP_COOLING, default=hp_cooling)] = bool
    schema_dict[vol.Required(CONF_HEAT_PUMP_MIN_TEMP, default=hp_min_temp)] = selector.NumberSelector(
        selector.NumberSelectorConfig(min=15, max=65, step=1, mode=selector.NumberSelectorMode.BOX)
    )
    schema_dict[vol.Required(CONF_HEAT_PUMP_MAX_TEMP, default=hp_max_temp)] = selector.NumberSelector(
        selector.NumberSelectorConfig(min=20, max=75, step=1, mode=selector.NumberSelectorMode.BOX)
    )
    schema_dict[vol.Required(CONF_HEAT_PUMP_COOL_MIN_TEMP, default=hp_cool_min_temp)] = selector.NumberSelector(
        selector.NumberSelectorConfig(min=5, max=25, step=1, mode=selector.NumberSelectorMode.BOX)
    )
    schema_dict[vol.Required(CONF_HEAT_PUMP_COOL_MAX_TEMP, default=hp_cool_max_temp)] = selector.NumberSelector(
        selector.NumberSelectorConfig(min=10, max=30, step=1, mode=selector.NumberSelectorMode.BOX)
    )
    ch_key = (
        vol.Optional(CONF_HEAT_PUMP_CH_SWITCH, description={"suggested_value": hp_ch_switch})
        if hp_ch_switch
        else vol.Optional(CONF_HEAT_PUMP_CH_SWITCH)
    )
    schema_dict[ch_key] = selector.EntitySelector(selector.EntitySelectorConfig(domain=SWITCH_DOMAIN))
    schema_dict[vol.Optional(CONF_HAS_MIXING_VALVE, default=has_mixing_valve)] = bool
    return vol.Schema(schema_dict)


def get_options_heat_pump_schema(current_data: dict[str, Any] | None = None) -> vol.Schema:
    """Generate schema for editing Heat Pump settings in Options Flow."""
    data = current_data or {}
    enable_hp = data.get(CONF_ENABLE_HEAT_PUMP, False)
    hp_type = data.get(CONF_HEAT_PUMP_TYPE, HP_TYPE_CLIMATE)
    hp_entity = data.get(CONF_HEAT_PUMP_ENTITY)
    hp_cooling = data.get(CONF_HEAT_PUMP_COOLING, DEFAULT_HEAT_PUMP_COOLING)
    hp_min_temp = data.get(CONF_HEAT_PUMP_MIN_TEMP, 25.0)
    hp_max_temp = data.get(CONF_HEAT_PUMP_MAX_TEMP, 55.0)
    hp_cool_min_temp = data.get(CONF_HEAT_PUMP_COOL_MIN_TEMP, DEFAULT_HP_COOL_MIN_TEMP)
    hp_cool_max_temp = data.get(CONF_HEAT_PUMP_COOL_MAX_TEMP, DEFAULT_HP_COOL_MAX_TEMP)
    hp_ch_switch = data.get(CONF_HEAT_PUMP_CH_SWITCH)
    has_mixing_valve = data.get(CONF_HAS_MIXING_VALVE, DEFAULT_HAS_MIXING_VALVE)

    schema_dict: dict[Any, Any] = {
        vol.Required(CONF_ENABLE_HEAT_PUMP, default=enable_hp): bool,
        vol.Required(CONF_HEAT_PUMP_TYPE, default=hp_type): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(value=HP_TYPE_CLIMATE, label="Climate Entity (HA Native Climate)"),
                    selector.SelectOptionDict(value=HP_TYPE_SWITCH, label="Switch / Relay / SG-Ready (ON/OFF)"),
                    selector.SelectOptionDict(value=HP_TYPE_OPENTHERM, label="OpenTherm (Modulating Gateway)"),
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
    }
    entity_key = (
        vol.Optional(CONF_HEAT_PUMP_ENTITY, description={"suggested_value": hp_entity})
        if hp_entity
        else vol.Optional(CONF_HEAT_PUMP_ENTITY)
    )
    schema_dict[entity_key] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["climate", "switch", "number", "water_heater"])
    )
    schema_dict[vol.Required(CONF_HEAT_PUMP_COOLING, default=hp_cooling)] = bool
    schema_dict[vol.Required(CONF_HEAT_PUMP_MIN_TEMP, default=hp_min_temp)] = selector.NumberSelector(
        selector.NumberSelectorConfig(min=15, max=65, step=1, mode=selector.NumberSelectorMode.BOX)
    )
    schema_dict[vol.Required(CONF_HEAT_PUMP_MAX_TEMP, default=hp_max_temp)] = selector.NumberSelector(
        selector.NumberSelectorConfig(min=20, max=75, step=1, mode=selector.NumberSelectorMode.BOX)
    )
    schema_dict[vol.Required(CONF_HEAT_PUMP_COOL_MIN_TEMP, default=hp_cool_min_temp)] = selector.NumberSelector(
        selector.NumberSelectorConfig(min=5, max=25, step=1, mode=selector.NumberSelectorMode.BOX)
    )
    schema_dict[vol.Required(CONF_HEAT_PUMP_COOL_MAX_TEMP, default=hp_cool_max_temp)] = selector.NumberSelector(
        selector.NumberSelectorConfig(min=10, max=30, step=1, mode=selector.NumberSelectorMode.BOX)
    )
    ch_key = (
        vol.Optional(CONF_HEAT_PUMP_CH_SWITCH, description={"suggested_value": hp_ch_switch})
        if hp_ch_switch
        else vol.Optional(CONF_HEAT_PUMP_CH_SWITCH)
    )
    schema_dict[ch_key] = selector.EntitySelector(selector.EntitySelectorConfig(domain=SWITCH_DOMAIN))
    schema_dict[vol.Optional(CONF_HAS_MIXING_VALVE, default=has_mixing_valve)] = bool
    return vol.Schema(schema_dict)


def get_energy_management_schema(
    enabled: bool = False,
    solar_power_sensor: str | None = None,
    grid_export_sensor: str | None = None,
    battery_soc_sensor: str | None = None,
    battery_power_sensor: str | None = None,
    solar_forecast_sensor: str | None = None,
    solar_irradiance_sensor: str | None = None,
    external_override_entity: str | None = None,
    export_threshold: float = DEFAULT_SOLAR_EXPORT_THRESHOLD,
    min_reserve_soc: float = DEFAULT_BATTERY_MIN_RESERVE_SOC,
    solar_min_run_time: float = DEFAULT_SOLAR_MIN_RUN_TIME,
    solar_overheat_offset: float = DEFAULT_SOLAR_OVERHEAT_OFFSET,
    battery_max_discharge_time: float = DEFAULT_BATTERY_MAX_DISCHARGE_TIME,
    battery_power_inverted: bool = DEFAULT_BATTERY_POWER_INVERTED,
) -> vol.Schema:
    schema_dict: dict[Any, Any] = {
        vol.Required(CONF_ENERGY_MANAGEMENT_ENABLED, default=enabled): bool,
    }

    sp_key = (
        vol.Optional(CONF_SOLAR_POWER_SENSOR, description={"suggested_value": solar_power_sensor})
        if solar_power_sensor
        else vol.Optional(CONF_SOLAR_POWER_SENSOR)
    )
    schema_dict[sp_key] = selector.EntitySelector(selector.EntitySelectorConfig(domain=SENSOR_DOMAIN, device_class="power"))

    exp_key = (
        vol.Optional(CONF_GRID_EXPORT_SENSOR, description={"suggested_value": grid_export_sensor})
        if grid_export_sensor
        else vol.Optional(CONF_GRID_EXPORT_SENSOR)
    )
    schema_dict[exp_key] = selector.EntitySelector(selector.EntitySelectorConfig(domain=SENSOR_DOMAIN, device_class="power"))

    soc_key = (
        vol.Optional(CONF_BATTERY_SOC_SENSOR, description={"suggested_value": battery_soc_sensor})
        if battery_soc_sensor
        else vol.Optional(CONF_BATTERY_SOC_SENSOR)
    )
    schema_dict[soc_key] = selector.EntitySelector(selector.EntitySelectorConfig(domain=SENSOR_DOMAIN, device_class="battery"))

    bp_key = (
        vol.Optional(CONF_BATTERY_POWER_SENSOR, description={"suggested_value": battery_power_sensor})
        if battery_power_sensor
        else vol.Optional(CONF_BATTERY_POWER_SENSOR)
    )
    schema_dict[bp_key] = selector.EntitySelector(selector.EntitySelectorConfig(domain=SENSOR_DOMAIN, device_class="power"))

    fc_key = (
        vol.Optional(CONF_SOLAR_FORECAST_SENSOR, description={"suggested_value": solar_forecast_sensor})
        if solar_forecast_sensor
        else vol.Optional(CONF_SOLAR_FORECAST_SENSOR)
    )
    schema_dict[fc_key] = selector.EntitySelector(selector.EntitySelectorConfig(domain=SENSOR_DOMAIN))

    irr_key = (
        vol.Optional(CONF_SOLAR_IRRADIANCE_SENSOR, description={"suggested_value": solar_irradiance_sensor})
        if solar_irradiance_sensor
        else vol.Optional(CONF_SOLAR_IRRADIANCE_SENSOR)
    )
    schema_dict[irr_key] = selector.EntitySelector(selector.EntitySelectorConfig(domain=SENSOR_DOMAIN))

    ext_key = (
        vol.Optional(CONF_EXTERNAL_SOLAR_OVERRIDE_ENTITY, description={"suggested_value": external_override_entity})
        if external_override_entity
        else vol.Optional(CONF_EXTERNAL_SOLAR_OVERRIDE_ENTITY)
    )
    schema_dict[ext_key] = selector.EntitySelector(selector.EntitySelectorConfig(domain=["binary_sensor", "input_boolean", "switch", "sensor"]))

    schema_dict[vol.Required(CONF_SOLAR_EXPORT_THRESHOLD, default=export_threshold)] = selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=10000, step=50, mode=selector.NumberSelectorMode.BOX)
    )
    schema_dict[vol.Required(CONF_BATTERY_MIN_RESERVE_SOC, default=min_reserve_soc)] = selector.NumberSelector(
        selector.NumberSelectorConfig(min=5, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
    )
    schema_dict[vol.Optional(CONF_SOLAR_MIN_RUN_TIME, default=solar_min_run_time)] = selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=60, step=1, mode=selector.NumberSelectorMode.BOX)
    )
    schema_dict[vol.Optional(CONF_SOLAR_OVERHEAT_OFFSET, default=solar_overheat_offset)] = selector.NumberSelector(
        selector.NumberSelectorConfig(min=0.0, max=3.0, step=0.5, mode=selector.NumberSelectorMode.BOX)
    )
    schema_dict[vol.Optional(CONF_BATTERY_MAX_DISCHARGE_TIME, default=battery_max_discharge_time)] = selector.NumberSelector(
        selector.NumberSelectorConfig(min=1, max=30, step=1, mode=selector.NumberSelectorMode.BOX)
    )
    schema_dict[vol.Optional(CONF_BATTERY_POWER_INVERTED, default=battery_power_inverted)] = bool
    return vol.Schema(schema_dict)


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


def get_boiler_relay_schema(dhw_active_sensor: str | None = None) -> vol.Schema:
    schema_dict: dict[Any, Any] = {
        vol.Required(CONF_BOILER_SWITCH): selector.EntitySelector(selector.EntitySelectorConfig(domain=SWITCH_DOMAIN)),
    }
    dhw_key = (
        vol.Optional(CONF_DHW_ACTIVE_SENSOR, description={"suggested_value": dhw_active_sensor})
        if dhw_active_sensor
        else vol.Optional(CONF_DHW_ACTIVE_SENSOR)
    )
    schema_dict[dhw_key] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["binary_sensor", "sensor", "input_boolean"])
    )
    schema_dict[vol.Optional(CONF_HAS_MIXING_VALVE, default=has_mixing_valve)] = bool
    return vol.Schema(schema_dict)


def get_boiler_opentherm_schema(dhw_active_sensor: str | None = None, has_mixing_valve: bool = DEFAULT_HAS_MIXING_VALVE) -> vol.Schema:
    schema_dict: dict[Any, Any] = {
        vol.Required(CONF_OPENTHERM_ENTITY): selector.EntitySelector(selector.EntitySelectorConfig(domain=["climate", "water_heater", "number"])),
        vol.Required(CONF_OPENTHERM_MIN_TEMP, default=35.0): selector.NumberSelector(
            selector.NumberSelectorConfig(min=20, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Required(CONF_OPENTHERM_MAX_TEMP, default=75.0): selector.NumberSelector(
            selector.NumberSelectorConfig(min=20, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_OPENTHERM_CH_SWITCH): selector.EntitySelector(selector.EntitySelectorConfig(domain=SWITCH_DOMAIN)),
    }
    dhw_key = (
        vol.Optional(CONF_DHW_ACTIVE_SENSOR, description={"suggested_value": dhw_active_sensor})
        if dhw_active_sensor
        else vol.Optional(CONF_DHW_ACTIVE_SENSOR)
    )
    schema_dict[dhw_key] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["binary_sensor", "sensor", "input_boolean"])
    )
    schema_dict[vol.Optional(CONF_HAS_MIXING_VALVE, default=has_mixing_valve)] = bool
    return vol.Schema(schema_dict)


def get_add_zone_schema() -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_ZONE_NAME): str,
        vol.Optional(CONF_ZONE_TEMP_SENSOR): selector.EntitySelector(selector.EntitySelectorConfig(domain=SENSOR_DOMAIN, device_class="temperature")),
        vol.Optional(CONF_ZONE_TARGET_TEMP, default=20.0): selector.NumberSelector(selector.NumberSelectorConfig(min=5, max=35, step=0.5, mode=selector.NumberSelectorMode.BOX)),
        vol.Optional(CONF_ZONE_EMITTER_TYPE, default=DEFAULT_ZONE_EMITTER_TYPE): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(value=EMITTER_TYPE_RADIATOR, label="Radiators"),
                    selector.SelectOptionDict(value=EMITTER_TYPE_UNDERFLOOR, label="Underfloor Heating"),
                    selector.SelectOptionDict(value=EMITTER_TYPE_FANCOIL, label="Fan Coils"),
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
                translation_key="emitter_type",
            )
        ),
        
        # Section 1: TRV Standard
        vol.Optional("trv_settings"): data_entry_flow.section(
            vol.Schema({
                vol.Optional(CONF_ZONE_CLIMATES, default=[]): selector.EntitySelector(selector.EntitySelectorConfig(domain=CLIMATE_DOMAIN, multiple=True)),
                vol.Optional(CONF_ZONE_TRV_SYNC, default=DEFAULT_TRV_SYNC): bool,
                vol.Optional(CONF_ZONE_AUTHORITATIVE_SYNC, default=DEFAULT_AUTHORITATIVE_SYNC): bool,
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
                vol.Optional(CONF_ZONE_WEIGHT, default=DEFAULT_ZONE_WEIGHT): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0.1, max=10.0, step=0.1, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Optional(CONF_ZONE_ANTI_SEIZE, default=True): bool,
                vol.Optional(CONF_ZONE_ALLOW_PASSIVE_HEAT, default=False): bool,
            }),
            {"collapsed": True},
        ),

        # Section 5: Climatizzatori Split d'Ambiente
        vol.Optional("split_settings"): data_entry_flow.section(
            vol.Schema({
                vol.Optional(CONF_ZONE_SPLIT_CLIMATE): selector.EntitySelector(selector.EntitySelectorConfig(domain=CLIMATE_DOMAIN)),
                vol.Optional(CONF_ZONE_SPLIT_ROLE, default=DEFAULT_SPLIT_ROLE): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=SPLIT_ROLE_HEAT_COOL, label="Heating & Cooling (Both)"),
                            selector.SelectOptionDict(value=SPLIT_ROLE_HEATING_ONLY, label="Heating Only"),
                            selector.SelectOptionDict(value=SPLIT_ROLE_COOLING_ONLY, label="Cooling Only"),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_ZONE_SPLIT_SOLAR_PRIORITY, default=DEFAULT_SPLIT_SOLAR_PRIORITY): bool,
                vol.Optional(CONF_ZONE_SPLIT_QUICK_BOOST, default=DEFAULT_SPLIT_QUICK_BOOST): bool,
                vol.Optional(CONF_ZONE_SPLIT_BOOST_DELTA, default=DEFAULT_SPLIT_BOOST_DELTA): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0.5, max=5.0, step=0.5, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Optional(CONF_ZONE_SPLIT_SENSOR_INJECTION, default=DEFAULT_SPLIT_SENSOR_INJECTION): bool,
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


def get_options_boiler_relay_schema(boiler_switch: str, dhw_active_sensor: str | None = None) -> vol.Schema:
    schema_dict: dict[Any, Any] = {}
    if boiler_switch:
        schema_dict[vol.Required(CONF_BOILER_SWITCH, default=boiler_switch)] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=SWITCH_DOMAIN)
        )
    else:
        schema_dict[vol.Required(CONF_BOILER_SWITCH)] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=SWITCH_DOMAIN)
        )
    dhw_key = (
        vol.Optional(CONF_DHW_ACTIVE_SENSOR, description={"suggested_value": dhw_active_sensor})
        if dhw_active_sensor
        else vol.Optional(CONF_DHW_ACTIVE_SENSOR)
    )
    schema_dict[dhw_key] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["binary_sensor", "sensor", "input_boolean"])
    )
    schema_dict[vol.Optional(CONF_HAS_MIXING_VALVE, default=has_mixing_valve)] = bool
    return vol.Schema(schema_dict)


def get_options_boiler_opentherm_schema(
    opentherm_entity: str | None,
    opentherm_min_temp: float,
    opentherm_max_temp: float,
    opentherm_ch_switch: str | None = None,
    dhw_active_sensor: str | None = None,
    has_mixing_valve: bool = DEFAULT_HAS_MIXING_VALVE,
) -> vol.Schema:
    schema_dict: dict[Any, Any] = {}
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
    dhw_key = (
        vol.Optional(CONF_DHW_ACTIVE_SENSOR, description={"suggested_value": dhw_active_sensor})
        if dhw_active_sensor
        else vol.Optional(CONF_DHW_ACTIVE_SENSOR)
    )
    schema_dict[dhw_key] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["binary_sensor", "sensor", "input_boolean"])
    )
    schema_dict[vol.Optional(CONF_HAS_MIXING_VALVE, default=has_mixing_valve)] = bool
    return vol.Schema(schema_dict)


def get_zone_select_schema(zone_options: dict[str, str]) -> vol.Schema:
    return vol.Schema({
        vol.Required("zone_name"): vol.In(zone_options),
    })


def get_options_edit_zone_schema(zone_data: dict[str, Any], temp_desc: dict[str, Any], window_desc: dict[str, Any]) -> vol.Schema:
    split_climate = zone_data.get(CONF_ZONE_SPLIT_CLIMATE)
    split_role = zone_data.get(CONF_ZONE_SPLIT_ROLE, DEFAULT_SPLIT_ROLE)
    split_solar = zone_data.get(CONF_ZONE_SPLIT_SOLAR_PRIORITY, DEFAULT_SPLIT_SOLAR_PRIORITY)
    split_boost = zone_data.get(CONF_ZONE_SPLIT_QUICK_BOOST, DEFAULT_SPLIT_QUICK_BOOST)
    split_delta = zone_data.get(CONF_ZONE_SPLIT_BOOST_DELTA, DEFAULT_SPLIT_BOOST_DELTA)
    split_injection = zone_data.get(CONF_ZONE_SPLIT_SENSOR_INJECTION, DEFAULT_SPLIT_SENSOR_INJECTION)

    return vol.Schema({
        vol.Optional(CONF_ZONE_TEMP_SENSOR, **temp_desc): selector.EntitySelector(selector.EntitySelectorConfig(domain=SENSOR_DOMAIN, device_class="temperature")),
        vol.Optional(CONF_ZONE_TARGET_TEMP, default=zone_data.get(CONF_ZONE_TARGET_TEMP, 20.0)): selector.NumberSelector(selector.NumberSelectorConfig(min=5, max=35, step=0.5, mode=selector.NumberSelectorMode.BOX)),
        vol.Optional(CONF_ZONE_EMITTER_TYPE, default=zone_data.get(CONF_ZONE_EMITTER_TYPE, DEFAULT_ZONE_EMITTER_TYPE)): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(value=EMITTER_TYPE_RADIATOR, label="Radiators"),
                    selector.SelectOptionDict(value=EMITTER_TYPE_UNDERFLOOR, label="Underfloor Heating"),
                    selector.SelectOptionDict(value=EMITTER_TYPE_FANCOIL, label="Fan Coils"),
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
                translation_key="emitter_type",
            )
        ),

        # Section 1: TRV Standard
        vol.Optional("trv_settings"): data_entry_flow.section(
            vol.Schema({
                vol.Optional(CONF_ZONE_CLIMATES, default=zone_data.get(CONF_ZONE_CLIMATES, [])): selector.EntitySelector(selector.EntitySelectorConfig(domain=CLIMATE_DOMAIN, multiple=True)),
                vol.Optional(CONF_ZONE_TRV_SYNC, default=zone_data.get(CONF_ZONE_TRV_SYNC, DEFAULT_TRV_SYNC)): bool,
                vol.Optional(CONF_ZONE_AUTHORITATIVE_SYNC, default=zone_data.get(CONF_ZONE_AUTHORITATIVE_SYNC, DEFAULT_AUTHORITATIVE_SYNC)): bool,
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
                vol.Optional(CONF_ZONE_WEIGHT, default=zone_data.get(CONF_ZONE_WEIGHT, DEFAULT_ZONE_WEIGHT)): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0.1, max=10.0, step=0.1, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Optional(CONF_ZONE_ANTI_SEIZE, default=zone_data.get(CONF_ZONE_ANTI_SEIZE, True)): bool,
                vol.Optional(CONF_ZONE_ALLOW_PASSIVE_HEAT, default=zone_data.get(CONF_ZONE_ALLOW_PASSIVE_HEAT, False)): bool,
            }),
            {"collapsed": True},
        ),

        # Section 5: Climatizzatori Split d'Ambiente
        vol.Optional("split_settings"): data_entry_flow.section(
            vol.Schema({
                **(
                    {vol.Optional(CONF_ZONE_SPLIT_CLIMATE, description={"suggested_value": split_climate}): selector.EntitySelector(selector.EntitySelectorConfig(domain=CLIMATE_DOMAIN))}
                    if split_climate
                    else {vol.Optional(CONF_ZONE_SPLIT_CLIMATE): selector.EntitySelector(selector.EntitySelectorConfig(domain=CLIMATE_DOMAIN))}
                ),
                vol.Optional(CONF_ZONE_SPLIT_ROLE, default=split_role): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=SPLIT_ROLE_HEAT_COOL, label="Heating & Cooling (Both)"),
                            selector.SelectOptionDict(value=SPLIT_ROLE_HEATING_ONLY, label="Heating Only"),
                            selector.SelectOptionDict(value=SPLIT_ROLE_COOLING_ONLY, label="Cooling Only"),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_ZONE_SPLIT_SOLAR_PRIORITY, default=split_solar): bool,
                vol.Optional(CONF_ZONE_SPLIT_QUICK_BOOST, default=split_boost): bool,
                vol.Optional(CONF_ZONE_SPLIT_BOOST_DELTA, default=split_delta): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0.5, max=5.0, step=0.5, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Optional(CONF_ZONE_SPLIT_SENSOR_INJECTION, default=split_injection): bool,
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
