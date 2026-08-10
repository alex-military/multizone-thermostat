"""Sensor platform for Multizone Thermostat: displays zone demands (0-100%)."""
import logging
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN, CONF_ZONES, CONF_ZONE_NAME, make_zone_entity_id

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up demand sensors for each virtual thermostat."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    zones = config_entry.data.get(CONF_ZONES, [])
    if not zones:
        return

    entities = []
    for zone in zones:
        climate_entity_id = make_zone_entity_id(zone[CONF_ZONE_NAME])
        name = zone.get(CONF_ZONE_NAME, climate_entity_id.split(".")[-1].replace("_", " ").title())
        entities.append(DemandSensor(hass, config_entry.entry_id, name, climate_entity_id, coordinator))
        entities.append(AutotuneSensor(hass, config_entry.entry_id, name, climate_entity_id, coordinator))
        entities.append(HeatingRateSensor(hass, config_entry.entry_id, name, climate_entity_id, coordinator))
        entities.append(CoolingRateSensor(hass, config_entry.entry_id, name, climate_entity_id, coordinator))
        entities.append(ThermalInertiaSensor(hass, config_entry.entry_id, name, climate_entity_id, coordinator))

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
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_virtual_thermostats")},
            name="Multizone Brain",
            manufacturer="Custom Integration",
            model="Multizone Brain",
            via_device=(DOMAIN, entry_id),
        )

    @property
    def name(self) -> str:
        return f"{self._name} Fabbisogno"

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
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_virtual_thermostats")},
            name="Multizone Brain",
            manufacturer="Custom Integration",
            model="Multizone Brain",
            via_device=(DOMAIN, entry_id),
        )

    @property
    def name(self) -> str:
        return f"{self._name} Autotuning"

    @property
    def native_value(self) -> str:
        """Return the current autotuner state."""
        tuner = self._coordinator._autotuners.get(self._climate_entity_id)
        if not tuner:
            return "unknown"
        if tuner.state == tuner.STATE_COMPLETED:
            return "Smart PID Active"
        return f"Learning ({len(tuner.completed_cycles)}/{tuner.required_cycles})"

    @property
    def extra_state_attributes(self):
        """Return computed PID parameters."""
        tuner = self._coordinator._autotuners.get(self._climate_entity_id)
        if not tuner:
            return {}
        if tuner.state == tuner.STATE_COMPLETED:
            return {
                "Kp": round(tuner.kp, 2),
                "Ki": round(tuner.ki, 4),
                "Kd": round(tuner.kd, 2)
            }
        return {
            "Kp": 0.0,
            "Ki": 0.0,
            "Kd": 0.0
        }

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
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_virtual_thermostats")},
            name="Multizone Brain",
            manufacturer="Custom Integration",
            model="Multizone Brain",
            via_device=(DOMAIN, entry_id),
        )

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
        return f"{self._name} Velocità Riscaldamento"
        
    @property
    def native_value(self) -> float:
        model = self._coordinator._thermal_models.get(self._climate_entity_id)
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
        return f"{self._name} Dispersione"
        
    @property
    def native_value(self) -> float:
        model = self._coordinator._thermal_models.get(self._climate_entity_id)
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
        return f"{self._name} Inerzia Termica"
        
    @property
    def native_value(self) -> float:
        model = self._coordinator._thermal_models.get(self._climate_entity_id)
        return round(model.thermal_inertia, 2) if model else 0.0

    @property
    def native_unit_of_measurement(self) -> str:
        return "°C"
