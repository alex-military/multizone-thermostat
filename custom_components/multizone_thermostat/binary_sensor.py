"""Binary sensor platform for Multizone Thermostat: plant & zone anomaly detection."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN, CONF_ZONES, CONF_ZONE_NAME, make_zone_entity_id

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors for Multizone Thermostat."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    zones = config_entry.data.get(CONF_ZONES, [])

    entities: list[BinarySensorEntity] = []

    # 1. Global Plant Anomaly Binary Sensor
    entities.append(MultizonePlantAnomalyBinarySensor(coordinator, config_entry.entry_id))

    # 2. Per-Zone Anomaly Binary Sensors
    for zone in zones:
        climate_id = make_zone_entity_id(zone[CONF_ZONE_NAME])
        name = zone.get(CONF_ZONE_NAME, climate_id.split(".")[-1].replace("_", " ").title())
        entities.append(MultizoneZoneAnomalyBinarySensor(coordinator, config_entry.entry_id, name, climate_id))

    async_add_entities(entities)


class MultizonePlantAnomalyBinarySensor(BinarySensorEntity):
    """Binary sensor that turns ON if any plant-wide or zone anomaly is detected."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_name = "Plant Anomaly"
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, coordinator: Any, entry_id: str) -> None:
        """Initialize the plant anomaly sensor."""
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_plant_anomaly"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="Master Control",
            manufacturer="Custom Integration",
            model="Master Control",
        )

    @property
    def is_on(self) -> bool:
        """Return True if any anomaly is present in the plant."""
        engine = getattr(self._coordinator, "plant_diagnostics", None)
        if not engine:
            return False
        summary = engine.get_plant_health_summary()
        return summary["status"] != "optimal"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return details of all active anomalies."""
        engine = getattr(self._coordinator, "plant_diagnostics", None)
        if not engine:
            return {}
        summary = engine.get_plant_health_summary()
        return {
            "health_status": summary["status"],
            "anomalies_count": summary["anomalies_count"],
            "anomalies": summary["anomalies"],
            "cycles_per_hour": summary["cycles_per_hour"],
            "daily_runtime_hours": summary["daily_runtime_hours"],
        }

    async def async_added_to_hass(self) -> None:
        """Periodically refresh anomaly evaluations."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                lambda _: self.async_write_ha_state(),
                timedelta(seconds=60),
            )
        )


class MultizoneZoneAnomalyBinarySensor(BinarySensorEntity):
    """Binary sensor that turns ON if an anomaly is detected in this specific zone."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:radiator-alert"

    def __init__(self, coordinator: Any, entry_id: str, name: str, climate_id: str) -> None:
        """Initialize the zone anomaly sensor."""
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._name = name
        self._climate_id = climate_id
        self._attr_name = f"{name} Anomaly"
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_anomaly_{climate_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_zones")},
            name="Heating Zones",
            manufacturer="Multizone Thermostat",
            model="Hybrid Zone Controller",
        )

    @property
    def is_on(self) -> bool:
        """Return True if an anomaly is detected in this zone."""
        engine = getattr(self._coordinator, "plant_diagnostics", None)
        if not engine:
            return False
        anomaly_type, _ = engine.evaluate_zone_anomalies(self._climate_id)
        return anomaly_type != "none"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return anomaly type and description."""
        engine = getattr(self._coordinator, "plant_diagnostics", None)
        if not engine:
            return {}
        anomaly_type, details = engine.evaluate_zone_anomalies(self._climate_id)
        return {
            "anomaly_type": anomaly_type,
            "details": details,
        }

    async def async_added_to_hass(self) -> None:
        """Periodically refresh anomaly evaluations."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                lambda _: self.async_write_ha_state(),
                timedelta(seconds=60),
            )
        )
