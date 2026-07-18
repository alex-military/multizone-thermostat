# Entities Created

> **Note:** Entity IDs are assigned by Home Assistant based on the entity's unique ID and device name. The actual IDs may differ slightly from the examples below. Always copy the exact entity ID from **Settings → Devices & Services → Multizone Thermostat** or from the entity's settings page.

| Entity (example ID) | Description |
|--------|-------------|
| `switch.multizone_thermostat_heating_master` | Master on/off for the entire heating system |
| `select.zone_modes_[zone_name]_mode` | Per-zone mode selector (Primary, Secondary, Bypass) |
| `climate.multizone_thermostat_vt_[name]` | Virtual thermostat entity (only if created via the UI) |
| `select.multizone_thermostat_global_preset` | Global preset selector (Manual, Eco, Comfort, Sleep, Away) |
| `number.multizone_thermostat_min_cycle_on` | Minimum boiler ON time (minutes, default: 5) |
| `number.multizone_thermostat_min_cycle_off` | Minimum boiler OFF time (minutes, default: 5) |
| `number.multizone_thermostat_valve_delay` | Valve opening delay before boiler starts (seconds, default: 0) |
| `binary_sensor.multizone_thermostat_boiler_status` | Status of the boiler |
