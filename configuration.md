# Configuration & Documentation

[⬅️ Back to Main Readme](README.md)

Everything you need to know to set up, configure, and understand how the Multizone Thermostat integration works.

## Setup Wizard

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **"Multizone Thermostat"**
3. Follow the setup wizard:
   - **Step 1**: Select your boiler switch/relay entity
   - **Step 2**: Select an optional presence sensor for Geofencing (Away/Comfort)
   - **Step 3**: Choose zone type — **existing thermostat** or **create a virtual thermostat**
   - **Step 4**: Configure the zone (name, optional window sensor, optional TRV sync)
   - **Step 5**: Add more zones or confirm and finish

---

## Creating a Virtual Thermostat

If you don't have a pre-existing `climate` entity (e.g., you have a standalone temperature sensor and a relay/switch controlling a fancoil, radiator valve, or underfloor heating), you can create a **Virtual Thermostat** directly from the UI without writing any YAML:

### During Initial Setup
1. In the "Choose zone type" step of the wizard, select **"Create virtual thermostat"**
2. Fill in:
   - **Zone Name**: A friendly name for the zone (e.g., "Camera", "Studio")
   - **Temperature Sensor**: The `sensor` entity that reads the room temperature (must have `device_class: temperature`)
   - **Heater Switch**: The `switch` entity that controls the heater/relay in that zone
   - **Target Temperature**: Initial target temperature (default: 20°C)
   - **Tolerance**: Hysteresis in °C (default: 0.5°C) — the heater turns ON when temperature drops below `target - tolerance`, and turns OFF when it rises above `target + tolerance`
   - **Window Sensor** _(optional)_: A `binary_sensor` to auto-bypass the zone when a window is open
3. The integration will automatically create a `climate` entity and register it as a zone.

### After Installation
Virtual thermostats can also be created **after installation** from the Options menu:
1. Go to **Settings → Devices & Services → Multizone Thermostat**
2. Click **Configure**
3. Select **"Create a new virtual thermostat"**

---

## Entities Created

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
| `switch.multizone_thermostat_anti_seize_summer_protection` | Global ON/OFF toggle for the Summer Anti-seize protection |
| `number.multizone_thermostat_anti_seize_idle_days` | Number of idle days before triggering the Anti-seize cycle (default: 15) |
| `number.multizone_thermostat_anti_seize_duration` | Duration in minutes of the Anti-seize cycle (default: 2) |
| `binary_sensor.multizone_thermostat_boiler_status` | Status of the boiler |

---

## How It Works

```
Master Switch ON
    └── Zone Mode = Primary   → Boiler can be triggered if zone is heating
    └── Zone Mode = Secondary → Receives heat if boiler is running, but cannot trigger boiler
    └── Zone Mode = Bypass    → Zone is completely excluded

Master Switch OFF
    └── ALL zones → Overridden to OFF
    └── Boiler   → switch.turn_off() (ignores min_cycle_on for safety)

Any Primary zone hvac_action = heating
    └── If valve_delay > 0, wait for delay
    └── If boiler was recently off, wait for min_cycle_off
    └── Boiler ON

All Primary zones hvac_action = idle/off
    └── If boiler was recently on, wait for min_cycle_on
    └── Boiler OFF
    
Window Opened
    └── Zone Mode temporarily overridden to Bypassed (saves previous state)
Window Closed
    └── Zone Mode restores previous state

Virtual Thermostat Logic (ON/OFF with hysteresis)
    └── current_temp < target - tolerance → heater switch ON
    └── current_temp > target + tolerance → heater switch OFF
    └── Reports hvac_action = heating/idle to the coordinator
```

---

## Options (Post-Installation)

Go to **Settings → Devices & Services → Multizone Thermostat → Configure** to:
- Change the boiler switch
- Change the presence sensor for geofencing
- Add a new zone (existing thermostat)
- Create a new virtual thermostat (sensor + switch → climate entity)
- Remove a zone
- Remove a virtual thermostat (removes both the climate entity and the associated zone)
- Edit a zone (TRV preset sync, Window Sensor, Anti-seize exclusion)

---

## TRV Preset Sync

When enabled for a zone, the integration automatically syncs the TRV preset mode:
- HVAC mode `heat` → preset `manual`
- HVAC mode `off` → preset `off`

Only enable this for zones with physical TRV valves that support preset modes.

---

## Summer Anti-seize Protection

During the summer months, thermostatic valves and boiler circulator pumps can remain inactive for long periods, which may cause them to mechanically seize or become stuck.
The integration includes a built-in safety mechanism to periodically cycle them:

1. Enable the `switch.multizone_thermostat_anti_seize_summer_protection` entity.
2. The system tracks the exact time since the heating was last turned on.
3. If the system remains completely idle for the configured number of days (`number.multizone_thermostat_anti_seize_idle_days`, default 15 days), the integration will:
   - Save the current state of all zones.
   - Force all zones that have the anti-seize feature enabled to turn ON (opening their valves).
   - Wait for the configured valve opening delay.
   - Wait for the configured duration (`number.multizone_thermostat_anti_seize_duration`, default 2 minutes).
   - Restore all zones to their previous state.

**Note**: You can selectively disable the Anti-seize protection for specific zones (e.g., fancoil units that don't have moving mechanical valves) through the UI Options flow (**Edit a zone** -> Disable "Enable Anti-seize (Summer Protection) for this zone").
