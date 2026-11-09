from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)

from .const import DOMAIN, CONF_ZONES, CONF_ZONE_NAME, make_zone_entity_id, make_via_device_kwargs, make_zone_device_info

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up demand and diagnostic sensors for each virtual thermostat and plant."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    zones = coordinator.zones
    if not zones:
        return

    entities: list[SensorEntity] = []

    # Plant-wide diagnostic sensors
    if hasattr(coordinator, "plant_diagnostics"):
        entities.append(MultizonePlantHealthSensor(hass, config_entry.entry_id, coordinator))
        entities.append(MultizoneBoilerCyclesSensor(hass, config_entry.entry_id, coordinator))
        entities.append(MultizoneBoilerDailyRuntimeSensor(hass, config_entry.entry_id, coordinator))

    for zone in zones:
        climate_entity_id = make_zone_entity_id(zone[CONF_ZONE_NAME])
        name = zone.get(CONF_ZONE_NAME, climate_entity_id.split(".")[-1].replace("_", " ").title())
        entities.append(DemandSensor(hass, config_entry.entry_id, name, climate_entity_id, coordinator))
        entities.append(AutotuneSensor(hass, config_entry.entry_id, name, climate_entity_id, coordinator))
        entities.append(HeatingRateSensor(hass, config_entry.entry_id, name, climate_entity_id, coordinator))
        entities.append(CoolingRateSensor(hass, config_entry.entry_id, name, climate_entity_id, coordinator))
        entities.append(ThermalInertiaSensor(hass, config_entry.entry_id, name, climate_entity_id, coordinator))
        entities.append(MultizoneZoneEnergyClassSensor(hass, config_entry.entry_id, name, climate_entity_id, coordinator))
        entities.append(MultizoneZoneRetentionTimeSensor(hass, config_entry.entry_id, name, climate_entity_id, coordinator))
        entities.append(MultizoneZoneRadiatorSizingSensor(hass, config_entry.entry_id, name, climate_entity_id, coordinator))

    if entities:
        async_add_entities(entities)

class DemandSensor(SensorEntity):
    """Sensor that reports the PID heating demand (0-100%)."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:heating-coil"

    def __init__(self, hass: HomeAssistant, entry_id: str, name: str, climate_entity_id: str, coordinator) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._name = name
        self._climate_entity_id = climate_entity_id
        self._coordinator = coordinator
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_demand_{climate_entity_id}"
        
        master_dev_id = getattr(coordinator, "master_device_id", None)
        self._attr_device_info = make_zone_device_info(entry_id, self._name, master_dev_id)

    @property
    def name(self) -> str:
        return "Demand"

    @property
    def native_value(self) -> float:
        """Return the current demand."""
        demand = self._coordinator.get_zone_demand(self._climate_entity_id)
        return round(demand, 1) if demand is not None else 0.0

    async def async_added_to_hass(self) -> None:
        """Listen to updates from the climate entity."""
        await super().async_added_to_hass()
        # Since demand is updated when the climate entity updates, we listen to the climate entity
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._climate_entity_id],
                self._async_on_climate_change
            )
        )
        
    @callback
    def _async_on_climate_change(self, event):
        """Update sensor when climate entity updates."""
        self.async_write_ha_state()

class AutotuneSensor(SensorEntity):
    """Sensor that reports the Autotuning progress and parameters."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:brain"

    def __init__(self, hass: HomeAssistant, entry_id: str, name: str, climate_entity_id: str, coordinator) -> None:
        self.hass = hass
        self._name = name
        self._climate_entity_id = climate_entity_id
        self._coordinator = coordinator
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_autotune_{climate_entity_id}"
        
        master_dev_id = getattr(coordinator, "master_device_id", None)
        self._attr_device_info = make_zone_device_info(entry_id, self._name, master_dev_id)

    @property
    def name(self) -> str:
        return "Autotuning"

    @property
    def native_value(self) -> str:
        """Return the current autotuner state for the active season."""
        season = getattr(self._coordinator, "master_hvac_mode", "heat") or "heat"
        season_mode = "cool" if str(season).lower() == "cool" else "heat"
        tuner = self._coordinator.zone_controller.get_autotuner(self._climate_entity_id, mode=season_mode)
        if not tuner:
            return "unknown"
        season_label = "Freddo" if season_mode == "cool" else "Caldo"
        if tuner.state == tuner.STATE_COMPLETED:
            return f"Smart PID Attivo ({season_label})"
        return f"Apprendimento {season_label} ({len(tuner.completed_cycles)}/{tuner.required_cycles})"

    @property
    def extra_state_attributes(self):
        """Return detailed dual-track heat and cool PID & autotuner parameters."""
        season = getattr(self._coordinator, "master_hvac_mode", "heat") or "heat"
        season_mode = "cool" if str(season).lower() == "cool" else "heat"
        tuner_heat = self._coordinator.zone_controller.get_autotuner(self._climate_entity_id, mode="heat")
        tuner_cool = self._coordinator.zone_controller.get_autotuner(self._climate_entity_id, mode="cool")

        active_tuner = tuner_cool if season_mode == "cool" else tuner_heat
        kp_active = round(active_tuner.kp, 2) if active_tuner and active_tuner.state == active_tuner.STATE_COMPLETED else 0.0
        ki_active = round(active_tuner.ki, 4) if active_tuner and active_tuner.state == active_tuner.STATE_COMPLETED else 0.0
        kd_active = round(active_tuner.kd, 2) if active_tuner and active_tuner.state == active_tuner.STATE_COMPLETED else 0.0

        attrs = {
            "active_season": season_mode,
            "Kp": kp_active,
            "Ki": ki_active,
            "Kd": kd_active,
            "heat_status": tuner_heat.state if tuner_heat else "unknown",
            "heat_cycles": f"{len(tuner_heat.completed_cycles)}/{tuner_heat.required_cycles}" if tuner_heat else "0/3",
            "heat_kp": round(tuner_heat.kp, 2) if tuner_heat and tuner_heat.state == tuner_heat.STATE_COMPLETED else 0.0,
            "heat_ki": round(tuner_heat.ki, 4) if tuner_heat and tuner_heat.state == tuner_heat.STATE_COMPLETED else 0.0,
            "heat_kd": round(tuner_heat.kd, 2) if tuner_heat and tuner_heat.state == tuner_heat.STATE_COMPLETED else 0.0,
            "cool_status": tuner_cool.state if tuner_cool else "unknown",
            "cool_cycles": f"{len(tuner_cool.completed_cycles)}/{tuner_cool.required_cycles}" if tuner_cool else "0/3",
            "cool_kp": round(tuner_cool.kp, 2) if tuner_cool and tuner_cool.state == tuner_cool.STATE_COMPLETED else 0.0,
            "cool_ki": round(tuner_cool.ki, 4) if tuner_cool and tuner_cool.state == tuner_cool.STATE_COMPLETED else 0.0,
            "cool_kd": round(tuner_cool.kd, 2) if tuner_cool and tuner_cool.state == tuner_cool.STATE_COMPLETED else 0.0,
        }
        return attrs

    async def async_added_to_hass(self) -> None:
        """Listen to updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._climate_entity_id],
                self._async_on_climate_change
            )
        )
        
    @callback
    def _async_on_climate_change(self, event):
        self.async_write_ha_state()

class ThermalSensorBase(SensorEntity):
    """Base class for thermal model sensors."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass: HomeAssistant, entry_id: str, name: str, climate_entity_id: str, coordinator) -> None:
        self.hass = hass
        self._name = name
        self._climate_entity_id = climate_entity_id
        self._coordinator = coordinator
        
        master_dev_id = getattr(coordinator, "master_device_id", None)
        self._attr_device_info = make_zone_device_info(entry_id, self._name, master_dev_id)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._climate_entity_id], self._async_on_climate_change
            )
        )

    @callback
    def _async_on_climate_change(self, event):
        self.async_write_ha_state()

class HeatingRateSensor(ThermalSensorBase):
    """Sensor that reports the Heating Rate (°C/hr)."""
    _attr_icon = "mdi:thermometer-chevron-up"
    
    def __init__(self, hass: HomeAssistant, entry_id: str, name: str, climate_entity_id: str, coordinator) -> None:
        super().__init__(hass, entry_id, name, climate_entity_id, coordinator)
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_heating_rate_{climate_entity_id}"
    
    @property
    def name(self) -> str:
        return "Heating Rate"
        
    @property
    def native_value(self) -> float:
        model = self._coordinator.zone_controller.get_thermal_model(self._climate_entity_id)
        return round(model.heating_rate, 2) if model else 0.0

    @property
    def native_unit_of_measurement(self) -> str:
        return "°C/hr"

class CoolingRateSensor(ThermalSensorBase):
    """Sensor that reports the Cooling Rate (°C/hr)."""
    _attr_icon = "mdi:thermometer-chevron-down"
    
    def __init__(self, hass: HomeAssistant, entry_id: str, name: str, climate_entity_id: str, coordinator) -> None:
        super().__init__(hass, entry_id, name, climate_entity_id, coordinator)
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_cooling_rate_{climate_entity_id}"
    
    @property
    def name(self) -> str:
        return "Cooling Rate"
        
    @property
    def native_value(self) -> float:
        model = self._coordinator.zone_controller.get_thermal_model(self._climate_entity_id)
        return round(model.cooling_rate, 2) if model else 0.0

    @property
    def native_unit_of_measurement(self) -> str:
        return "°C/hr"

class ThermalInertiaSensor(ThermalSensorBase):
    """Sensor that reports the Thermal Inertia (°C)."""
    _attr_icon = "mdi:waves"
    
    def __init__(self, hass: HomeAssistant, entry_id: str, name: str, climate_entity_id: str, coordinator) -> None:
        super().__init__(hass, entry_id, name, climate_entity_id, coordinator)
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_thermal_inertia_{climate_entity_id}"
    
    @property
    def name(self) -> str:
        return "Thermal Inertia"
        
    @property
    def native_value(self) -> float:
        model = self._coordinator.zone_controller.get_thermal_model(self._climate_entity_id)
        return round(model.thermal_inertia, 2) if model else 0.0

    @property
    def native_unit_of_measurement(self) -> str:
        return "°C"


class MultizonePlantHealthSensor(SensorEntity):
    """Sensor that reports the overall physical heating plant health status."""

    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, entry_id: str, coordinator) -> None:
        self.hass = hass
        self._coordinator = coordinator
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_plant_health"
        self._attr_name = "Plant Health Status"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="Master Control",
            manufacturer="Custom Integration",
            model="Master Control",
        )

    @property
    def native_value(self) -> str:
        """Return human-readable plant health rating."""
        engine = getattr(self._coordinator, "plant_diagnostics", None)
        if not engine:
            return "N/A"
        return engine.get_plant_health_summary().get("label", "Optimal")

    @property
    def icon(self) -> str:
        """Dynamic icon based on health status."""
        val = self.native_value
        if val in ("Optimal", "Ottimale"):
            return "mdi:check-decagram"
        elif val in ("Critical", "Critico"):
            return "mdi:alert-octagon"
        return "mdi:alert"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return full plant health details."""
        engine = getattr(self._coordinator, "plant_diagnostics", None)
        if not engine:
            return {}
        return engine.get_plant_health_summary()

    @callback
    def _update_state(self, _) -> None:
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(
                self.hass, self._update_state, timedelta(seconds=60)
            )
        )


class MultizoneBoilerCyclesSensor(SensorEntity):
    """Sensor reporting boiler ignition frequency (cycles/hour)."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "cycles/h"
    _attr_icon = "mdi:fire-alert"

    def __init__(self, hass: HomeAssistant, entry_id: str, coordinator) -> None:
        self.hass = hass
        self._coordinator = coordinator
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_boiler_cycles_per_hour"
        self._attr_name = "Boiler Cycles per Hour"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="Master Control",
            manufacturer="Custom Integration",
            model="Master Control",
        )

    @property
    def native_value(self) -> int:
        engine = getattr(self._coordinator, "plant_diagnostics", None)
        return engine.get_boiler_cycles_per_hour() if engine else 0

    @callback
    def _update_state(self, _) -> None:
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(
                self.hass, self._update_state, timedelta(seconds=60)
            )
        )


class MultizoneBoilerDailyRuntimeSensor(SensorEntity):
    """Sensor reporting total boiler running hours in the past 24 hours."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "h"
    _attr_icon = "mdi:timer-sand"

    def __init__(self, hass: HomeAssistant, entry_id: str, coordinator) -> None:
        self.hass = hass
        self._coordinator = coordinator
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_boiler_daily_runtime"
        self._attr_name = "Boiler Daily Runtime (24h)"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="Master Control",
            manufacturer="Custom Integration",
            model="Master Control",
        )

    @property
    def native_value(self) -> float:
        engine = getattr(self._coordinator, "plant_diagnostics", None)
        return engine.get_boiler_daily_runtime_hours() if engine else 0.0

    @callback
    def _update_state(self, _) -> None:
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(
                self.hass, self._update_state, timedelta(seconds=60)
            )
        )


class MultizoneZoneEnergyClassSensor(ThermalSensorBase):
    """Sensor reporting the theoretical energy efficiency class of a zone."""

    _attr_icon = "mdi:home-lightning-bolt-outline"
    _attr_translation_key = "energy_class"

    def __init__(self, hass: HomeAssistant, entry_id: str, name: str, climate_entity_id: str, coordinator) -> None:
        super().__init__(hass, entry_id, name, climate_entity_id, coordinator)
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_energy_class_{climate_entity_id}"
        self._attr_state_class = None

    @property
    def name(self) -> str:
        return "Energy Class"

    @property
    def native_value(self) -> str:
        engine = getattr(self._coordinator, "plant_diagnostics", None)
        if not engine:
            return "N/A"
        return engine.get_zone_energy_class(self._climate_entity_id)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        thermal = self._coordinator.zone_controller.get_thermal_model(self._climate_entity_id)
        return {
            "cooling_rate": round(thermal.cooling_rate, 3) if thermal else 0.0,
            "heating_rate": round(thermal.heating_rate, 3) if thermal else 0.0,
            "thermal_inertia": round(thermal.thermal_inertia, 2) if thermal else 0.0,
        }


class MultizoneZoneRetentionTimeSensor(ThermalSensorBase):
    """Sensor reporting hours required for the zone to lose 1°C."""

    _attr_icon = "mdi:clock-fast"
    _attr_native_unit_of_measurement = "h"

    def __init__(self, hass: HomeAssistant, entry_id: str, name: str, climate_entity_id: str, coordinator) -> None:
        super().__init__(hass, entry_id, name, climate_entity_id, coordinator)
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_thermal_retention_{climate_entity_id}"

    @property
    def name(self) -> str:
        return "Thermal Retention Time"

    @property
    def native_value(self) -> float | None:
        engine = getattr(self._coordinator, "plant_diagnostics", None)
        if not engine:
            return None
        return engine.get_zone_thermal_retention_hours(self._climate_entity_id)


class MultizoneZoneRadiatorSizingSensor(ThermalSensorBase):
    """Sensor evaluating if radiators/emitters in the zone are properly sized."""

    _attr_icon = "mdi:radiator"

    def __init__(self, hass: HomeAssistant, entry_id: str, name: str, climate_entity_id: str, coordinator) -> None:
        super().__init__(hass, entry_id, name, climate_entity_id, coordinator)
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_radiator_sizing_{climate_entity_id}"
        self._attr_state_class = None

    @property
    def name(self) -> str:
        return "Radiator Sizing"

    @property
    def native_value(self) -> str:
        engine = getattr(self._coordinator, "plant_diagnostics", None)
        if not engine:
            return "N/A"
        return engine.get_zone_radiator_sizing(self._climate_entity_id)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        thermal = self._coordinator.zone_controller.get_thermal_model(self._climate_entity_id)
        if thermal and thermal.cooling_rate > 0.01:
            ratio = round(thermal.heating_rate / thermal.cooling_rate, 2)
        else:
            ratio = None
        return {
            "power_to_loss_ratio": ratio,
        }



