"""Typed configuration for Multizone Thermostat heating plant."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .const import (
    CONF_ZONE_NAME,
    CONF_ZONE_CLIMATES,
    CONF_ZONE_SWITCHES,
    CONF_ZONE_VALVES,
    CONF_BOILER_MODE,
    CONF_BOILER_SWITCH,
    CONF_OPENTHERM_ENTITY,
    CONF_OPENTHERM_MIN_TEMP,
    CONF_OPENTHERM_MAX_TEMP,
    CONF_OPENTHERM_CH_SWITCH,
    CONF_DHW_ACTIVE_SENSOR,
    CONF_HAS_MIXING_VALVE,
    DEFAULT_HAS_MIXING_VALVE,
    CONF_ZONES,
    CONF_PRESENCE_SENSOR,
    CONF_WEATHER_SENSOR,
    CONF_GLOBAL_CALENDAR,
    CONF_ENABLE_GAS_HEATER,
    CONF_ENABLE_HEAT_PUMP,
    CONF_HEAT_PUMP_TYPE,
    HP_TYPE_CLIMATE,
    CONF_HEAT_PUMP_ENTITY,
    CONF_HEAT_PUMP_MIN_TEMP,
    CONF_HEAT_PUMP_MAX_TEMP,
    CONF_HEAT_PUMP_CH_SWITCH,
    CONF_HEAT_PUMP_COOLING,
    DEFAULT_HEAT_PUMP_COOLING,
    DEFAULT_HP_COOL_MIN_TEMP,
    DEFAULT_HP_COOL_MAX_TEMP,
    CONF_ENERGY_MANAGEMENT_ENABLED,
    CONF_SOLAR_POWER_SENSOR,
    CONF_GRID_EXPORT_SENSOR,
    CONF_BATTERY_SOC_SENSOR,
    CONF_EXTERNAL_SOLAR_OVERRIDE_ENTITY,
    CONF_SOLAR_EXPORT_THRESHOLD,
    DEFAULT_SOLAR_EXPORT_THRESHOLD,
    CONF_BATTERY_MIN_RESERVE_SOC,
    DEFAULT_BATTERY_MIN_RESERVE_SOC,
    CONF_MIN_CYCLE_ON,
    DEFAULT_MIN_CYCLE_ON,
    CONF_MIN_CYCLE_OFF,
    DEFAULT_MIN_CYCLE_OFF,
    CONF_VALVE_DELAY,
    DEFAULT_VALVE_DELAY,
    MODE_RELAY,
    DEFAULT_MASTER_OPERATION_MODE,
)


@dataclass
class PlantConfig:
    """Typed plant configuration container."""

    raw_config: dict[str, Any] = field(default_factory=dict)
    boiler_mode: str = MODE_RELAY
    boiler_switch: str | None = None
    opentherm_entity: str | None = None
    opentherm_min_temp: float = 35.0
    opentherm_max_temp: float = 75.0
    opentherm_ch_switch: str | None = None
    dhw_active_sensor: str | None = None
    has_mixing_valve: bool = DEFAULT_HAS_MIXING_VALVE
    zones: list[dict[str, Any]] = field(default_factory=list)
    presence_sensor: str | None = None
    weather_sensor_id: str | None = None
    global_calendar_id: str | None = None

    # Multi-generator
    enable_gas_heater: bool = True
    enable_heat_pump: bool = False
    heat_pump_type: str = HP_TYPE_CLIMATE
    heat_pump_entity: str | None = None
    heat_pump_min_temp: float = 25.0
    heat_pump_max_temp: float = 55.0
    heat_pump_ch_switch: str | None = None
    heat_pump_cooling: bool = DEFAULT_HEAT_PUMP_COOLING
    hp_cool_min_temp: float = DEFAULT_HP_COOL_MIN_TEMP
    hp_cool_max_temp: float = DEFAULT_HP_COOL_MAX_TEMP
    master_hvac_mode: str = DEFAULT_MASTER_OPERATION_MODE

    # Energy management
    energy_management_enabled: bool = False
    solar_power_sensor: str | None = None
    grid_export_sensor: str | None = None
    battery_soc_sensor: str | None = None
    external_solar_override_entity: str | None = None
    solar_export_threshold: float = DEFAULT_SOLAR_EXPORT_THRESHOLD
    battery_min_reserve_soc: float = DEFAULT_BATTERY_MIN_RESERVE_SOC

    # Safety timings
    min_cycle_on: float = float(DEFAULT_MIN_CYCLE_ON)
    min_cycle_off: float = float(DEFAULT_MIN_CYCLE_OFF)
    valve_delay: float = float(DEFAULT_VALVE_DELAY)

    @classmethod
    def from_entry(cls, entry: Any) -> PlantConfig:
        """Construct PlantConfig from Home Assistant ConfigEntry data and options."""
        options = getattr(entry, "options", None) or {}
        raw = {**(getattr(entry, "data", None) or {}), **(options if isinstance(options, dict) else {})}

        return cls(
            raw_config=raw,
            boiler_mode=raw.get(CONF_BOILER_MODE, MODE_RELAY),
            boiler_switch=raw.get(CONF_BOILER_SWITCH),
            opentherm_entity=raw.get(CONF_OPENTHERM_ENTITY),
            opentherm_min_temp=float(raw.get(CONF_OPENTHERM_MIN_TEMP, 35.0)),
            opentherm_max_temp=float(raw.get(CONF_OPENTHERM_MAX_TEMP, 75.0)),
            opentherm_ch_switch=raw.get(CONF_OPENTHERM_CH_SWITCH),
            dhw_active_sensor=raw.get(CONF_DHW_ACTIVE_SENSOR),
            has_mixing_valve=bool(raw.get(CONF_HAS_MIXING_VALVE, DEFAULT_HAS_MIXING_VALVE)),
            zones=raw.get(CONF_ZONES, []),
            presence_sensor=raw.get(CONF_PRESENCE_SENSOR),
            weather_sensor_id=raw.get(CONF_WEATHER_SENSOR),
            global_calendar_id=raw.get(CONF_GLOBAL_CALENDAR),
            enable_gas_heater=bool(raw.get(CONF_ENABLE_GAS_HEATER, True)),
            enable_heat_pump=bool(raw.get(CONF_ENABLE_HEAT_PUMP, False)),
            heat_pump_type=raw.get(CONF_HEAT_PUMP_TYPE, HP_TYPE_CLIMATE),
            heat_pump_entity=raw.get(CONF_HEAT_PUMP_ENTITY),
            heat_pump_min_temp=float(raw.get(CONF_HEAT_PUMP_MIN_TEMP, 25.0)),
            heat_pump_max_temp=float(raw.get(CONF_HEAT_PUMP_MAX_TEMP, 55.0)),
            heat_pump_ch_switch=raw.get(CONF_HEAT_PUMP_CH_SWITCH),
            heat_pump_cooling=bool(raw.get(CONF_HEAT_PUMP_COOLING, DEFAULT_HEAT_PUMP_COOLING)),
            hp_cool_min_temp=float(raw.get("hp_cool_min_temp", raw.get("heat_pump_cool_min_temp", DEFAULT_HP_COOL_MIN_TEMP))),
            hp_cool_max_temp=float(raw.get("hp_cool_max_temp", raw.get("heat_pump_cool_max_temp", DEFAULT_HP_COOL_MAX_TEMP))),
            master_hvac_mode=DEFAULT_MASTER_OPERATION_MODE,
            energy_management_enabled=bool(raw.get(CONF_ENERGY_MANAGEMENT_ENABLED, False)),
            solar_power_sensor=raw.get(CONF_SOLAR_POWER_SENSOR),
            grid_export_sensor=raw.get(CONF_GRID_EXPORT_SENSOR),
            battery_soc_sensor=raw.get(CONF_BATTERY_SOC_SENSOR),
            external_solar_override_entity=raw.get(CONF_EXTERNAL_SOLAR_OVERRIDE_ENTITY),
            solar_export_threshold=float(raw.get(CONF_SOLAR_EXPORT_THRESHOLD, DEFAULT_SOLAR_EXPORT_THRESHOLD)),
            battery_min_reserve_soc=float(raw.get(CONF_BATTERY_MIN_RESERVE_SOC, DEFAULT_BATTERY_MIN_RESERVE_SOC)),
            min_cycle_on=float(raw.get(CONF_MIN_CYCLE_ON, DEFAULT_MIN_CYCLE_ON)),
            min_cycle_off=float(raw.get(CONF_MIN_CYCLE_OFF, DEFAULT_MIN_CYCLE_OFF)),
            valve_delay=float(raw.get(CONF_VALVE_DELAY, DEFAULT_VALVE_DELAY)),
        )


def get_zone_name(zone: dict[str, Any] | None) -> str:
    """Extract zone name, supporting both 'name' and 'zone_name'."""
    if not isinstance(zone, dict):
        return ""
    return str(zone.get(CONF_ZONE_NAME) or zone.get("zone_name") or "")


def get_zone_climates(zone: dict[str, Any] | None) -> list[str]:
    """Extract list of climate entities (TRVs), supporting aliases."""
    if not isinstance(zone, dict):
        return []
    res = zone.get(CONF_ZONE_CLIMATES) or zone.get("zone_climates") or zone.get("climates") or []
    return list(res) if isinstance(res, (list, tuple, set)) else []


def get_zone_switches(zone: dict[str, Any] | None) -> list[str]:
    """Extract list of switch entities (relays), supporting aliases."""
    if not isinstance(zone, dict):
        return []
    res = zone.get(CONF_ZONE_SWITCHES) or zone.get("zone_switches") or zone.get("switches") or []
    return list(res) if isinstance(res, (list, tuple, set)) else []


def get_zone_valves(zone: dict[str, Any] | None) -> list[str]:
    """Extract list of proportional/analog valve entities, supporting aliases."""
    if not isinstance(zone, dict):
        return []
    res = zone.get(CONF_ZONE_VALVES) or zone.get("zone_valves") or zone.get("valves") or []
    return list(res) if isinstance(res, (list, tuple, set)) else []
