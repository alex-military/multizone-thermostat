"""Constants for Plant Diagnostics."""

ANOMALY_NONE = "none"
ANOMALY_VALVE_STUCK_CLOSED = "valve_stuck_closed"
ANOMALY_GHOST_HEATING = "ghost_heating"
ANOMALY_AIR_IN_RADIATOR = "air_in_radiator"
ANOMALY_STALE_SENSOR = "stale_sensor"
ANOMALY_OVERSHOOT = "overshoot"
ANOMALY_LOW_BATTERY = "low_battery"
ANOMALY_SENSOR_FAULT = "sensor_fault"
ANOMALY_SENSOR_TIMEOUT = "sensor_timeout"
ANOMALY_BOILER_LOW_PRESSURE = "boiler_low_pressure"
ANOMALY_BOILER_FAULT = "boiler_fault"

# Human-readable anomaly labels
ANOMALY_LABELS = {
    ANOMALY_NONE: "No anomaly",
    ANOMALY_VALVE_STUCK_CLOSED: "Possible valve stuck closed / No heat delivery",
    ANOMALY_GHOST_HEATING: "Possible valve leakage or open valve (Ghost heating)",
    ANOMALY_AIR_IN_RADIATOR: "Thermal output drop (Possible air in radiator)",
    ANOMALY_STALE_SENSOR: "Temperature sensor not updated for over 6 hours",
    ANOMALY_OVERSHOOT: "Abnormal temperature overshoot (>1.5°C)",
    ANOMALY_LOW_BATTERY: "Sensor battery low (<= 10%)",
    ANOMALY_SENSOR_FAULT: "Sensor fault or implausible temperature",
    ANOMALY_SENSOR_TIMEOUT: "Watchdog: Sensor offline / no data received",
    ANOMALY_BOILER_LOW_PRESSURE: "Boiler circuit pressure low (< 0.8 bar)",
    ANOMALY_BOILER_FAULT: "OpenTherm boiler fault alarm",
}
