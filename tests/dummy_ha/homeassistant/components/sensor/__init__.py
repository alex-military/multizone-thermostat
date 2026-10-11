"""Sensor component for dummy Home Assistant."""
from homeassistant.helpers.entity import Entity

class SensorDeviceClass:
    TEMPERATURE = "temperature"
    BATTERY = "battery"

class SensorStateClass:
    MEASUREMENT = "measurement"

class SensorEntity(Entity):
    pass
