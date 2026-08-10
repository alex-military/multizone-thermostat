# Configuration & Documentation

[⬅️ Back to Main Readme](README.md)

Everything you need to know to set up, configure, and understand how the Multizone Thermostat integration works.

## Prerequisite: Home Assistant Local Calendar

If you want to use the **Global Calendar & Smart Start** feature, you must first create a local calendar in Home Assistant *before* starting the setup wizard:
1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **"Local Calendar"** and install it.
3. Name it something like "Thermostat Calendar".
4. You will now see a "Calendar" tab in your main Home Assistant sidebar.

---

## Setup Wizard

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **"Multizone Thermostat"**
3. Follow the setup wizard:
   - **Step 1 (Global Heating)**: Select your central boiler relay / circulator pump (`switch`).
   - **Step 2 (Add Zone)**: Create your first thermal zone. Here you can assign all its hardware in a single page: Name, Temperature Sensor (optional), TRVs (`climate`), Heater Switches (`switch`), Window Sensor, and toggle Anti-seize/Preset Sync.
   - **Step 3 (TRV Calibration - Conditional)**: If in Step 2 you assigned *both* TRVs and a pure external Temperature Sensor, you will be asked if you want to assign a `Local Temperature Calibration` entity to each TRV (for the mathematical offset injection).
   - **Step 4 (More Zones)**: Choose whether to add another zone or proceed to global settings.
   - **Step 5 (Global Calendar)**: Select the Local Calendar entity you created in the prerequisite step. Leave blank if you don't want to use calendar scheduling.
   - **Step 6 (Weather Compensation)**: Select an optional outdoor sensor (physical or `weather` domain) to enable the Feed-Forward heating curve.
   - **Step 7 (Geofencing)**: Select an optional presence sensor (`binary_sensor` or `device_tracker` or `zone`) and choose the target presets for when you leave or return home.
   - **Step 8**: Confirm and finish.

---

## 🧠 Zone Intelligence & Hardware Aggregation

In the new V3 architecture, a **Zone** is a powerful virtual aggregator. You don't need to create separate "virtual thermostats" anymore. 

- **Pure TRV Room**: Assign one or multiple TRVs to the zone. The zone will average their temperatures and sync their targets.
- **Relay/Underfloor Room**: Assign a simple relay switch and a temperature sensor. The zone automatically acts as a virtual thermostat, computing PID and driving the relay via PWM!
- **Hybrid TRV + External Sensor**: Assign your TRVs AND a pure external temperature sensor. The zone intercepts the TRVs and injects a fake target (or a dynamic calibration offset) to force the physical TRV to align with the pure external sensor, bypassing the TRV's inaccurate internal thermometer!

---

## Entities Created

> **Note:** Entity IDs are assigned by Home Assistant based on the entity's unique ID and device name. The actual IDs may differ slightly from the examples below. Always copy the exact entity ID from **Settings → Devices & Services → Multizone Thermostat** or from the entity's settings page.

| Entity (example ID) | Description |
|--------|-------------|
| `switch.multizone_thermostat_heating_master` | Master on/off for the entire heating system |
| `select.zone_modes_[zone_name]_mode` | Per-zone mode selector (Primary, Secondary, Bypass) |
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
```

---

## Options (Post-Installation)

Go to **Settings → Devices & Services → Multizone Thermostat → Configure** to:
- Change the boiler switch
- Edit Global Calendar (change or remove the calendar entity)
- Edit Weather Compensation (change or remove outdoor sensor)
- Change the presence sensor for geofencing
- Add a new zone
- Remove a zone
- Edit a zone (TRV preset sync, Window Sensor, Anti-seize exclusion, etc)

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

---

## 📅 Global Calendar Integration & Smart Start

You can control the entire Multizone Thermostat system natively using Home Assistant's `Local Calendar` integration. 
Go to **Settings → Devices & Services → Multizone Thermostat → Configure** and select "Edit Global Calendar" to assign a calendar to the integration.

### Syntax Rules

When you create an event in the calendar, the integration reads the **Summary (Title)** of the event. The syntax is highly flexible.

#### 1. Change the Global Preset
Simply write the name of the preset:
`Eco` or `Comfort` or `Sleep` or `Away` or `Manual`
- *What it does*: The system switches to this preset for the duration of the event, and seamlessly restores the previous preset when the event ends.

#### 2. Set a Global Temperature
Simply write a number:
`21.5`
- *What it does*: Temporarily overrides all zones to 21.5°C for the duration of the event.

#### 3. Advanced Per-Zone Overrides
You can combine a global preset with specific overrides for individual zones. Separate commands with commas `,` and specify the zone name with a colon `:`.
`Comfort, Bagno: 24, Camera: Bypass`
- *What it does*: Sets the system to Comfort. However, it forces the "Bagno" zone to 24°C, and forces the "Camera" zone to Bypass mode. 
- *When the event ends*: The system reverts to its previous state (restores previous preset, clears 24°C from Bagno, and restores Camera).

#### 4. Multiple Commands per Zone
You can send multiple commands to the same zone by separating them with spaces. Valid modes are `primary`, `secondary`, `bypass`, `standalone`, `off`.
`Eco, Salone: 22.5 primary`
- *What it does*: Sets global preset to Eco. Forces the "Salone" to 22.5°C AND forces its mode to Primary.

#### 5. Permanent Overrides (The `SET` keyword)
By default, all calendar overrides are temporary and vanish when the event ends. If you want a calendar event to permanently alter the underlying preset, add the word `SET` to the zone command:
`Comfort, Bagno: 25 SET`
- *What it does*: Changes the target temperature of the Bagno to 25°C and saves it permanently into the Comfort preset memory. When the event ends, the Bagno will still be 25°C next time Comfort is activated!

### 🤖 Predictive Smart Start

Because the Multizone Thermostat actively builds a **Thermal Model** of each room (learning its heating rate in °C/hour), it can predict exactly how long a room will take to heat up!

If you schedule an event like `Comfort` at 08:00 AM, the system will look ahead in the calendar. If it predicts that your bedroom needs 45 minutes to reach the Comfort temperature, the boiler will automatically fire up at 07:15 AM (Smart Start), ensuring the room is exactly at the right temperature when your alarm rings at 08:00!
