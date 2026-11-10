from typing import Any
import copy
from homeassistant import config_entries
from homeassistant.core import callback
from .schemas import *
from .validators import (
    validate_opentherm_temps,
    validate_zone_input,
    validate_geofencing,
    validate_plants_selection,
    validate_heat_pump_temps,
    validate_heat_pump_cool_temps,
)
from .helpers import (
    _get_temperature_sensor_entities,
    _remove_entity_from_registry,
    flatten_zone_user_input,
)
from ..plant_diagnostics.anomalies import find_suggested_dhw_sensor
from ..const import *
from ..const import (
    CONF_ZONE_WEIGHT,
    DEFAULT_ZONE_WEIGHT,
    CONF_ZONE_AUTHORITATIVE_SYNC,
    DEFAULT_AUTHORITATIVE_SYNC,
    # Phase 11
    CONF_ENABLE_GAS_HEATER,
    CONF_ENABLE_HEAT_PUMP,
    CONF_HEAT_PUMP_TYPE,
    HP_TYPE_CLIMATE,
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
import logging
from homeassistant.helpers import entity_registry as er

_LOGGER = logging.getLogger(__name__)


class MultizoneOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Multizone Thermostat."""

    def __init__(self) -> None:
        """Initialize."""
        self._zones: list[dict[str, Any]] = []
        self._enable_gas: bool = True
        self._enable_hp: bool = False
        self._boiler_mode: str = MODE_RELAY
        self._boiler_switch: str = ""
        self._opentherm_entity: str | None = None
        self._opentherm_min_temp: float = 35.0
        self._opentherm_max_temp: float = 75.0
        self._opentherm_ch_switch: str | None = None
        self._dhw_active_sensor: str | None = None
        self._has_mixing_valve: bool = DEFAULT_HAS_MIXING_VALVE
        # Heat pump
        self._hp_type: str = HP_TYPE_CLIMATE
        self._hp_entity: str | None = None
        self._hp_min_temp: float = 25.0
        self._hp_max_temp: float = 55.0
        self._hp_cooling: bool = DEFAULT_HEAT_PUMP_COOLING
        self._hp_cool_min_temp: float = DEFAULT_HP_COOL_MIN_TEMP
        self._hp_cool_max_temp: float = DEFAULT_HP_COOL_MAX_TEMP
        self._hp_ch_switch: str | None = None
        # Energy management
        self._energy_management_enabled: bool = False
        self._solar_power_sensor: str | None = None
        self._grid_export_sensor: str | None = None
        self._battery_soc_sensor: str | None = None
        self._external_solar_override_entity: str | None = None
        self._solar_export_threshold: float = DEFAULT_SOLAR_EXPORT_THRESHOLD
        self._battery_min_reserve_soc: float = DEFAULT_BATTERY_MIN_RESERVE_SOC
        self._solar_min_run_time: float = float(DEFAULT_SOLAR_MIN_RUN_TIME)
        self._solar_overheat_offset: float = float(DEFAULT_SOLAR_OVERHEAT_OFFSET)
        self._battery_power_sensor: str | None = None
        self._solar_forecast_sensor: str | None = None
        self._solar_irradiance_sensor: str | None = None
        self._battery_max_discharge_time: float = float(DEFAULT_BATTERY_MAX_DISCHARGE_TIME)
        self._battery_power_inverted: bool = DEFAULT_BATTERY_POWER_INVERTED
        # Extras
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
            self._enable_gas = cfg.get(CONF_ENABLE_GAS_HEATER, True)
            self._enable_hp = cfg.get(CONF_ENABLE_HEAT_PUMP, False)
            self._boiler_mode = cfg.get(CONF_BOILER_MODE, MODE_RELAY)
            self._boiler_switch = cfg.get(CONF_BOILER_SWITCH, "")
            self._opentherm_entity = cfg.get(CONF_OPENTHERM_ENTITY)
            self._opentherm_min_temp = cfg.get(CONF_OPENTHERM_MIN_TEMP, 35.0)
            self._opentherm_max_temp = cfg.get(CONF_OPENTHERM_MAX_TEMP, 75.0)
            self._opentherm_ch_switch = cfg.get(CONF_OPENTHERM_CH_SWITCH)
            self._dhw_active_sensor = cfg.get(CONF_DHW_ACTIVE_SENSOR)
            self._has_mixing_valve = cfg.get(CONF_HAS_MIXING_VALVE, DEFAULT_HAS_MIXING_VALVE)
            # HP
            self._hp_type = cfg.get(CONF_HEAT_PUMP_TYPE, HP_TYPE_CLIMATE)
            self._hp_entity = cfg.get(CONF_HEAT_PUMP_ENTITY)
            self._hp_min_temp = cfg.get(CONF_HEAT_PUMP_MIN_TEMP, 25.0)
            self._hp_max_temp = cfg.get(CONF_HEAT_PUMP_MAX_TEMP, 55.0)
            self._hp_cooling = cfg.get(CONF_HEAT_PUMP_COOLING, DEFAULT_HEAT_PUMP_COOLING)
            self._hp_cool_min_temp = cfg.get(CONF_HEAT_PUMP_COOL_MIN_TEMP, DEFAULT_HP_COOL_MIN_TEMP)
            self._hp_cool_max_temp = cfg.get(CONF_HEAT_PUMP_COOL_MAX_TEMP, DEFAULT_HP_COOL_MAX_TEMP)
            self._hp_ch_switch = cfg.get(CONF_HEAT_PUMP_CH_SWITCH)
            # Energy
            self._energy_management_enabled = cfg.get(CONF_ENERGY_MANAGEMENT_ENABLED, False)
            self._solar_power_sensor = cfg.get(CONF_SOLAR_POWER_SENSOR)
            self._grid_export_sensor = cfg.get(CONF_GRID_EXPORT_SENSOR)
            self._battery_soc_sensor = cfg.get(CONF_BATTERY_SOC_SENSOR)
            self._external_solar_override_entity = cfg.get(CONF_EXTERNAL_SOLAR_OVERRIDE_ENTITY)
            self._solar_export_threshold = float(cfg.get(CONF_SOLAR_EXPORT_THRESHOLD, DEFAULT_SOLAR_EXPORT_THRESHOLD))
            self._battery_min_reserve_soc = float(cfg.get(CONF_BATTERY_MIN_RESERVE_SOC, DEFAULT_BATTERY_MIN_RESERVE_SOC))
            self._solar_min_run_time = float(cfg.get(CONF_SOLAR_MIN_RUN_TIME, DEFAULT_SOLAR_MIN_RUN_TIME))
            self._solar_overheat_offset = float(cfg.get(CONF_SOLAR_OVERHEAT_OFFSET, DEFAULT_SOLAR_OVERHEAT_OFFSET))
            self._battery_power_sensor = cfg.get(CONF_BATTERY_POWER_SENSOR)
            self._solar_forecast_sensor = cfg.get(CONF_SOLAR_FORECAST_SENSOR)
            self._solar_irradiance_sensor = cfg.get(CONF_SOLAR_IRRADIANCE_SENSOR)
            self._battery_max_discharge_time = float(cfg.get(CONF_BATTERY_MAX_DISCHARGE_TIME, DEFAULT_BATTERY_MAX_DISCHARGE_TIME))
            self._battery_power_inverted = bool(cfg.get(CONF_BATTERY_POWER_INVERTED, DEFAULT_BATTERY_POWER_INVERTED))
            # Extras
            self._geofencing_enabled = cfg.get(CONF_GEOFENCING_ENABLED, False)
            self._presence_sensor = cfg.get(CONF_PRESENCE_SENSOR)
            self._weather_sensor = cfg.get(CONF_WEATHER_SENSOR)
            self._global_calendar = cfg.get(CONF_GLOBAL_CALENDAR)

        if user_input is not None:
            action = user_input.get("action")
            if action == "change_boiler":
                return await self.async_step_change_boiler()
            elif action == "edit_heat_pump":
                return await self.async_step_edit_heat_pump()
            elif action == "edit_energy_management":
                return await self.async_step_edit_energy_management()
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
            "change_boiler": "Change boiler / plant mode",
            "edit_heat_pump": "Edit Heat Pump (PDC)",
            "edit_energy_management": "Edit Solar & Energy Management",
            "add_zone": "Add a zone",
            "edit_zone": "Edit a zone",
            "remove_zone": "Remove a zone",
            "edit_weather_comp": "Edit Weather Compensation",
            "edit_geofencing": "Edit Geofencing Settings",
            "edit_calendar": "Edit Global Calendar",
        }

        schema = get_options_init_schema(menu_options)

        plant_summary = []
        if self._enable_gas:
            plant_summary.append(self._boiler_switch or self._opentherm_entity or "Gas")
        if self._enable_hp:
            plant_summary.append(self._hp_entity or "Heat Pump")

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders={
                "boiler_switch": ", ".join(plant_summary) if plant_summary else "N/A",
                "zones_count": str(len(self._zones)),
            },
        )

    async def async_step_change_boiler(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Change boiler mode (Relay vs OpenTherm) and enable/disable gas heater."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._enable_gas = user_input.get(CONF_ENABLE_GAS_HEATER, True)
            if not self._enable_gas:
                has_split = any(bool(z.get(CONF_ZONE_SPLIT_CLIMATE)) for z in self._zones)
                if not self._enable_hp and not has_split:
                    errors["base"] = "no_plants_selected"
                else:
                    return self._save_options()
            else:
                self._boiler_mode = user_input[CONF_BOILER_MODE]
                if self._boiler_mode == MODE_RELAY:
                    return await self.async_step_boiler_relay()
                else:
                    return await self.async_step_boiler_opentherm()

        import voluptuous as vol
        from homeassistant.helpers import selector
        schema = vol.Schema({
            vol.Required(CONF_ENABLE_GAS_HEATER, default=self._enable_gas): bool,
            vol.Required(CONF_BOILER_MODE, default=self._boiler_mode): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=MODE_RELAY, label="Relay (ON/OFF)"),
                        selector.SelectOptionDict(value=MODE_OPENTHERM, label="OpenTherm (Modulating)"),
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        })
        return self.async_show_form(step_id="change_boiler", data_schema=schema, errors=errors)

    async def async_step_boiler_relay(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step: Select boiler relay."""
        if user_input is not None:
            self._boiler_switch = user_input[CONF_BOILER_SWITCH]
            self._dhw_active_sensor = user_input.get(CONF_DHW_ACTIVE_SENSOR) or None
            return self._save_options()

        suggested_dhw = self._dhw_active_sensor or find_suggested_dhw_sensor(self.hass)
        schema = get_options_boiler_relay_schema(self._boiler_switch, suggested_dhw)
        return self.async_show_form(step_id="boiler_relay", data_schema=schema)

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
            self._has_mixing_valve = user_input.get(CONF_HAS_MIXING_VALVE, self._has_mixing_valve)
            errors.update(validate_opentherm_temps(self._opentherm_min_temp, self._opentherm_max_temp))
            if not errors:
                return self._save_options()

        suggested_dhw = self._dhw_active_sensor or find_suggested_dhw_sensor(self.hass, self._opentherm_entity)
        schema = get_options_boiler_opentherm_schema(
            self._opentherm_entity, self._opentherm_min_temp, self._opentherm_max_temp, self._opentherm_ch_switch, suggested_dhw, self._has_mixing_valve
        )
        return self.async_show_form(step_id="boiler_opentherm", data_schema=schema, errors=errors)

    async def async_step_edit_heat_pump(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Edit Heat Pump (PDC) parameters."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._enable_hp = user_input.get(CONF_ENABLE_HEAT_PUMP, False)
            self._hp_type = user_input.get(CONF_HEAT_PUMP_TYPE, HP_TYPE_CLIMATE)
            self._hp_entity = user_input.get(CONF_HEAT_PUMP_ENTITY)
            self._hp_cooling = user_input.get(CONF_HEAT_PUMP_COOLING, DEFAULT_HEAT_PUMP_COOLING)
            self._hp_min_temp = float(user_input.get(CONF_HEAT_PUMP_MIN_TEMP, 25.0))
            self._hp_max_temp = float(user_input.get(CONF_HEAT_PUMP_MAX_TEMP, 55.0))
            self._hp_cool_min_temp = float(user_input.get(CONF_HEAT_PUMP_COOL_MIN_TEMP, DEFAULT_HP_COOL_MIN_TEMP))
            self._hp_cool_max_temp = float(user_input.get(CONF_HEAT_PUMP_COOL_MAX_TEMP, DEFAULT_HP_COOL_MAX_TEMP))
            self._hp_ch_switch = user_input.get(CONF_HEAT_PUMP_CH_SWITCH) or None
            self._has_mixing_valve = user_input.get(CONF_HAS_MIXING_VALVE, self._has_mixing_valve)

            errors.update(validate_heat_pump_temps(self._hp_min_temp, self._hp_max_temp))
            errors.update(validate_heat_pump_cool_temps(self._hp_cool_min_temp, self._hp_cool_max_temp))

            if not self._enable_gas and not self._enable_hp:
                has_split = any(bool(z.get(CONF_ZONE_SPLIT_CLIMATE)) for z in self._zones)
                if not has_split:
                    errors["base"] = "no_plants_selected"

            if not errors:
                return self._save_options()

        current_data = {
            CONF_ENABLE_HEAT_PUMP: self._enable_hp,
            CONF_HEAT_PUMP_TYPE: self._hp_type,
            CONF_HEAT_PUMP_ENTITY: self._hp_entity,
            CONF_HEAT_PUMP_COOLING: self._hp_cooling,
            CONF_HEAT_PUMP_MIN_TEMP: self._hp_min_temp,
            CONF_HEAT_PUMP_MAX_TEMP: self._hp_max_temp,
            CONF_HEAT_PUMP_COOL_MIN_TEMP: self._hp_cool_min_temp,
            CONF_HEAT_PUMP_COOL_MAX_TEMP: self._hp_cool_max_temp,
            CONF_HEAT_PUMP_CH_SWITCH: self._hp_ch_switch,
            CONF_HAS_MIXING_VALVE: self._has_mixing_valve,
        }
        schema = get_options_heat_pump_schema(current_data)
        return self.async_show_form(
            step_id="edit_heat_pump",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_edit_energy_management(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Edit solar surplus & energy management options."""
        if user_input is not None:
            self._energy_management_enabled = user_input.get(CONF_ENERGY_MANAGEMENT_ENABLED, False)
            if self._energy_management_enabled:
                self._solar_power_sensor = user_input.get(CONF_SOLAR_POWER_SENSOR)
                self._grid_export_sensor = user_input.get(CONF_GRID_EXPORT_SENSOR)
                self._battery_soc_sensor = user_input.get(CONF_BATTERY_SOC_SENSOR)
                self._external_solar_override_entity = user_input.get(CONF_EXTERNAL_SOLAR_OVERRIDE_ENTITY)
                self._solar_export_threshold = float(user_input.get(CONF_SOLAR_EXPORT_THRESHOLD, DEFAULT_SOLAR_EXPORT_THRESHOLD))
                self._battery_min_reserve_soc = float(user_input.get(CONF_BATTERY_MIN_RESERVE_SOC, DEFAULT_BATTERY_MIN_RESERVE_SOC))
                self._solar_min_run_time = float(user_input.get(CONF_SOLAR_MIN_RUN_TIME, DEFAULT_SOLAR_MIN_RUN_TIME))
                self._solar_overheat_offset = float(user_input.get(CONF_SOLAR_OVERHEAT_OFFSET, DEFAULT_SOLAR_OVERHEAT_OFFSET))
                self._battery_power_sensor = user_input.get(CONF_BATTERY_POWER_SENSOR)
                self._solar_forecast_sensor = user_input.get(CONF_SOLAR_FORECAST_SENSOR)
                self._solar_irradiance_sensor = user_input.get(CONF_SOLAR_IRRADIANCE_SENSOR)
                self._battery_max_discharge_time = float(user_input.get(CONF_BATTERY_MAX_DISCHARGE_TIME, DEFAULT_BATTERY_MAX_DISCHARGE_TIME))
                self._battery_power_inverted = bool(user_input.get(CONF_BATTERY_POWER_INVERTED, DEFAULT_BATTERY_POWER_INVERTED))
            return self._save_options()

        schema = get_energy_management_schema(
            enabled=self._energy_management_enabled,
            solar_power_sensor=self._solar_power_sensor,
            grid_export_sensor=self._grid_export_sensor,
            battery_soc_sensor=self._battery_soc_sensor,
            external_override_entity=self._external_solar_override_entity,
            export_threshold=self._solar_export_threshold,
            min_reserve_soc=self._battery_min_reserve_soc,
            solar_min_run_time=self._solar_min_run_time,
            solar_overheat_offset=self._solar_overheat_offset,
            battery_power_sensor=self._battery_power_sensor,
            solar_forecast_sensor=self._solar_forecast_sensor,
            solar_irradiance_sensor=self._solar_irradiance_sensor,
            battery_max_discharge_time=self._battery_max_discharge_time,
            battery_power_inverted=self._battery_power_inverted,
        )
        return self.async_show_form(
            step_id="edit_energy_management",
            data_schema=schema,
        )

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
            split_climate = user_input.get(CONF_ZONE_SPLIT_CLIMATE)
            if split_climate == "none":
                split_climate = None
            
            errors.update(validate_zone_input(name, climates, switches, already_added, valves=valves, split_climate=split_climate))
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
                    CONF_ZONE_EMITTER_TYPE: user_input.get(CONF_ZONE_EMITTER_TYPE, DEFAULT_ZONE_EMITTER_TYPE),
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
                
                if CONF_ZONE_TEMP_SENSOR in zone_data and climates:
                    return await self.async_step_trv_calibration_add()
                
                self._zones.append(zone_data)
                self._current_zone_data = None
                return self._save_options()

        schema = get_add_zone_schema()
        return self.async_show_form(step_id="add_zone", data_schema=schema, errors=errors)

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
            
            ent_reg = er.async_get(self.hass)
            vt_id = make_zone_entity_id(zone_to_remove)
            _remove_entity_from_registry(self.hass, vt_id)
            
            safe_name = zone_to_remove.lower().replace(" ", "_").replace("-", "_")
            safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
            climate_id_for_unique = make_zone_entity_id(zone_to_remove)

            zone_unique_ids = [
                ("climate", f"{DOMAIN}_{self.config_entry.entry_id}_zone_{safe_name}"),
                ("climate", f"{DOMAIN}_{self.config_entry.entry_id}_zone_{climate_id_for_unique}"),
                ("select", f"{DOMAIN}_{self.config_entry.entry_id}_zone_mode_{climate_id_for_unique.replace('.', '_')}"),
                ("select", f"{DOMAIN}_{self.config_entry.entry_id}_zone_mode_{safe_name}"),
                ("switch", f"{DOMAIN}_{self.config_entry.entry_id}_physical_sync_{safe_name}"),
                ("switch", f"{DOMAIN}_{self.config_entry.entry_id}_physical_sync_{climate_id_for_unique}"),
                ("switch", f"{DOMAIN}_{self.config_entry.entry_id}_passive_heat_{safe_name}"),
                ("switch", f"{DOMAIN}_{self.config_entry.entry_id}_passive_heat_{climate_id_for_unique}"),
                ("binary_sensor", f"{DOMAIN}_{self.config_entry.entry_id}_anomaly_{safe_name}"),
                ("binary_sensor", f"{DOMAIN}_{self.config_entry.entry_id}_anomaly_{climate_id_for_unique}"),
                ("sensor", f"{DOMAIN}_{self.config_entry.entry_id}_demand_{safe_name}"),
                ("sensor", f"{DOMAIN}_{self.config_entry.entry_id}_demand_{climate_id_for_unique}"),
                ("sensor", f"{DOMAIN}_{self.config_entry.entry_id}_autotune_{safe_name}"),
                ("sensor", f"{DOMAIN}_{self.config_entry.entry_id}_autotune_{climate_id_for_unique}"),
                ("sensor", f"{DOMAIN}_{self.config_entry.entry_id}_heating_rate_{safe_name}"),
                ("sensor", f"{DOMAIN}_{self.config_entry.entry_id}_heating_rate_{climate_id_for_unique}"),
                ("sensor", f"{DOMAIN}_{self.config_entry.entry_id}_cooling_rate_{safe_name}"),
                ("sensor", f"{DOMAIN}_{self.config_entry.entry_id}_cooling_rate_{climate_id_for_unique}"),
                ("sensor", f"{DOMAIN}_{self.config_entry.entry_id}_thermal_inertia_{safe_name}"),
                ("sensor", f"{DOMAIN}_{self.config_entry.entry_id}_thermal_inertia_{climate_id_for_unique}"),
                ("sensor", f"{DOMAIN}_{self.config_entry.entry_id}_energy_class_{safe_name}"),
                ("sensor", f"{DOMAIN}_{self.config_entry.entry_id}_energy_class_{climate_id_for_unique}"),
                ("sensor", f"{DOMAIN}_{self.config_entry.entry_id}_thermal_retention_{safe_name}"),
                ("sensor", f"{DOMAIN}_{self.config_entry.entry_id}_thermal_retention_{climate_id_for_unique}"),
                ("sensor", f"{DOMAIN}_{self.config_entry.entry_id}_radiator_sizing_{safe_name}"),
                ("sensor", f"{DOMAIN}_{self.config_entry.entry_id}_radiator_sizing_{climate_id_for_unique}"),
            ]
            for domain_name, unique_id in zone_unique_ids:
                ent_id = ent_reg.async_get_entity_id(domain_name, DOMAIN, unique_id)
                if ent_id:
                    ent_reg.async_remove(ent_id)
                    _LOGGER.debug("Removed orphaned %s entity %s from registry", domain_name, ent_id)

            try:
                from homeassistant.helpers import device_registry as dr
                dev_reg = dr.async_get(self.hass)
                device = dev_reg.async_get_device(identifiers={(DOMAIN, f"{self.config_entry.entry_id}_zone_{safe_name}")})
                if device is not None:
                    dev_reg.async_remove_device(device.id)
                    _LOGGER.debug("Removed zone device %s from device registry", device.id)
            except Exception as ex:
                _LOGGER.debug("Error removing device from registry: %s", ex)
            
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
                split_climate = user_input.get(CONF_ZONE_SPLIT_CLIMATE)
                if split_climate == "none":
                    split_climate = None
                
                if not climates and not switches and not valves and not split_climate:
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
                            self._zones[i][CONF_ZONE_EMITTER_TYPE] = user_input.get(CONF_ZONE_EMITTER_TYPE, DEFAULT_ZONE_EMITTER_TYPE)
                            
                            # Phase 11 Split Settings
                            self._zones[i][CONF_ZONE_SPLIT_CLIMATE] = split_climate
                            self._zones[i][CONF_ZONE_SPLIT_ROLE] = user_input.get(CONF_ZONE_SPLIT_ROLE, DEFAULT_SPLIT_ROLE)
                            self._zones[i][CONF_ZONE_SPLIT_SOLAR_PRIORITY] = user_input.get(CONF_ZONE_SPLIT_SOLAR_PRIORITY, DEFAULT_SPLIT_SOLAR_PRIORITY)
                            self._zones[i][CONF_ZONE_SPLIT_QUICK_BOOST] = user_input.get(CONF_ZONE_SPLIT_QUICK_BOOST, DEFAULT_SPLIT_QUICK_BOOST)
                            self._zones[i][CONF_ZONE_SPLIT_BOOST_DELTA] = float(user_input.get(CONF_ZONE_SPLIT_BOOST_DELTA, DEFAULT_SPLIT_BOOST_DELTA))
                            self._zones[i][CONF_ZONE_SPLIT_SENSOR_INJECTION] = user_input.get(CONF_ZONE_SPLIT_SENSOR_INJECTION, DEFAULT_SPLIT_SENSOR_INJECTION)

                            if user_input.get(CONF_ZONE_TEMP_SENSOR) and user_input[CONF_ZONE_TEMP_SENSOR] != "none":
                                self._zones[i][CONF_ZONE_TEMP_SENSOR] = user_input[CONF_ZONE_TEMP_SENSOR]
                            elif CONF_ZONE_TEMP_SENSOR in self._zones[i]:
                                del self._zones[i][CONF_ZONE_TEMP_SENSOR]

                            if user_input.get(CONF_ZONE_WINDOW_SENSOR) and user_input[CONF_ZONE_WINDOW_SENSOR] != "none":
                                self._zones[i][CONF_ZONE_WINDOW_SENSOR] = user_input[CONF_ZONE_WINDOW_SENSOR]
                            elif CONF_ZONE_WINDOW_SENSOR in self._zones[i]:
                                del self._zones[i][CONF_ZONE_WINDOW_SENSOR]

                            break
                    
                    self._current_zone_name = None
                    return self._save_options()

        if self._current_zone_name is None:
            zone_options = {z.get(CONF_ZONE_NAME, 'Unnamed Zone'): z.get(CONF_ZONE_NAME, 'Unnamed Zone') for z in self._zones}
            if user_input is not None and "zone_name" in user_input:
                self._current_zone_name = user_input["zone_name"]
            else:
                schema = get_zone_select_schema(zone_options)
                return self.async_show_form(step_id="edit_zone", data_schema=schema)

        zone_data = next((z for z in self._zones if z.get(CONF_ZONE_NAME, 'Unnamed Zone') == self._current_zone_name), None)
        if not zone_data:
            return self.async_abort(reason="zone_not_found")

        temp_desc = {}
        if zone_data.get(CONF_ZONE_TEMP_SENSOR):
            temp_desc["description"] = {"suggested_value": zone_data[CONF_ZONE_TEMP_SENSOR]}
        window_desc = {}
        if zone_data.get(CONF_ZONE_WINDOW_SENSOR):
            window_desc["description"] = {"suggested_value": zone_data[CONF_ZONE_WINDOW_SENSOR]}

        schema = get_options_edit_zone_schema(zone_data, temp_desc, window_desc)
        return self.async_show_form(
            step_id="edit_zone",
            data_schema=schema,
            errors=errors,
            description_placeholders={"zone_name": self._current_zone_name}
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
        return self.async_show_form(step_id="edit_geofencing", data_schema=schema, errors=errors)

    async def async_step_edit_weather_comp(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Edit Weather Compensation sensor."""
        if user_input is not None:
            selected_sensor = user_input.get(CONF_WEATHER_SENSOR)
            if selected_sensor and selected_sensor != "none":
                self._weather_sensor = selected_sensor
            else:
                self._weather_sensor = None
            return self._save_options()

        temp_sensors = _get_temperature_sensor_entities(self.hass)
        sensor_options = {"none": "None (Disable Weather Compensation)"}
        sensor_options.update(temp_sensors)

        schema = get_options_edit_weather_comp_schema(self._weather_sensor, sensor_options)
        return self.async_show_form(step_id="edit_weather_comp", data_schema=schema)

    async def async_step_edit_calendar(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Edit Global Calendar entity."""
        if user_input is not None:
            selected_calendar = user_input.get(CONF_GLOBAL_CALENDAR)
            if selected_calendar and selected_calendar != "none":
                self._global_calendar = selected_calendar
            else:
                self._global_calendar = None
            return self._save_options()

        schema = get_options_edit_calendar_schema(self._global_calendar)
        return self.async_show_form(step_id="edit_calendar", data_schema=schema)

    def _save_options(self) -> config_entries.FlowResult:
        """Save updated options into entry.data and reload entry."""
        data: dict[str, Any] = {
            CONF_HAS_MIXING_VALVE: self._has_mixing_valve,
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
            if self._external_solar_override_entity:
                data[CONF_EXTERNAL_SOLAR_OVERRIDE_ENTITY] = self._external_solar_override_entity
            data[CONF_SOLAR_EXPORT_THRESHOLD] = self._solar_export_threshold
            data[CONF_BATTERY_MIN_RESERVE_SOC] = self._battery_min_reserve_soc
            data[CONF_SOLAR_MIN_RUN_TIME] = self._solar_min_run_time
            data[CONF_SOLAR_OVERHEAT_OFFSET] = self._solar_overheat_offset
            if self._battery_power_sensor:
                data[CONF_BATTERY_POWER_SENSOR] = self._battery_power_sensor
            if self._solar_forecast_sensor:
                data[CONF_SOLAR_FORECAST_SENSOR] = self._solar_forecast_sensor
            if self._solar_irradiance_sensor:
                data[CONF_SOLAR_IRRADIANCE_SENSOR] = self._solar_irradiance_sensor
            data[CONF_BATTERY_MAX_DISCHARGE_TIME] = self._battery_max_discharge_time
            data[CONF_BATTERY_POWER_INVERTED] = self._battery_power_inverted

        self.hass.config_entries.async_update_entry(
            self.config_entry, data=data, options=self.config_entry.options
        )
        
        has_listeners = bool(
            getattr(self.config_entry, "update_listeners", None)
            or getattr(self.config_entry, "_update_listeners", None)
        )
        if not has_listeners:
            self.hass.async_create_task(
                self.hass.config_entries.async_reload(self.config_entry.entry_id)
            )
        
        return self.async_create_entry(title="", data=self.config_entry.options)
