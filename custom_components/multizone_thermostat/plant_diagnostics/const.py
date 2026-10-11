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

# Human-readable anomaly labels (Italian)
ANOMALY_LABELS = {
    ANOMALY_NONE: "Nessuna anomalia",
    ANOMALY_VALVE_STUCK_CLOSED: "Possibile valvola bloccata chiusa / Nessun apporto termico",
    ANOMALY_GHOST_HEATING: "Possibile trafilamento o valvola aperta (Riscaldamento fantasma)",
    ANOMALY_AIR_IN_RADIATOR: "Calo di resa termica (Possibile aria nel radiatore)",
    ANOMALY_STALE_SENSOR: "Sensore temperatura non aggiornato da oltre 2 ore",
    ANOMALY_OVERSHOOT: "Superamento anomalo temperatura impostata (>1.5°C)",
    ANOMALY_LOW_BATTERY: "Batteria sensore in esaurimento (<= 10%)",
    ANOMALY_SENSOR_FAULT: "Guasto sensore o temperatura non plausibile",
    ANOMALY_SENSOR_TIMEOUT: "Watchdog: Sonda offline / mancata ricezione dati",
    ANOMALY_BOILER_LOW_PRESSURE: "Pressione circuito caldaia insufficiente (< 0.8 bar)",
    ANOMALY_BOILER_FAULT: "Allarme guasto generatore OpenTherm",
}
