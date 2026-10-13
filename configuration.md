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
   - **Step 1 (Boiler Mode)**: Choose between **Relay (ON/OFF)** and **OpenTherm (Modulating)**.
   - **Step 1a (Relay Mode)**: Select your central boiler relay / circulator pump (`switch`).
   - **Step 1b (OpenTherm Mode)**: Select your OpenTherm entity (`climate`, `water_heater`, or `number`), optionally specify a dedicated Central Heating toggle switch (`opentherm_ch_switch`), and set the Minimum ($T_{\text{min}}$, default 35°C) and Maximum ($T_{\text{max}}$, default 75°C) boiler water temperatures.
   - **Step 2 (Add Zone)**: Create your thermal zone through intuitive collapsible sections:
     - **Main Settings**: Name, primary Temperature Sensor, and Base Target Temperature.
     - **▶ TRVs (Standard)**: Assign smart thermostatic radiator valves (`climate`) and enable preset sync.
     - **▶ Proportional & 0-10V Valves**: Assign direct-opening actuators (`valve`, `number`) and choose scaling (**Percentage 0–100%** or **Voltage 0.0–10.0 V**).
     - **▶ Relay Actuators (PWM)**: Assign switches/relays for thermal ON/OFF actuators.
     - **▶ Protections & Advanced**: Assign Window Sensors, adjust Sensor Watchdog Timeout, toggle Summer Anti-seize, or enable Passive Heat intake.
   - **Step 3 (TRV Calibration - Conditional)**: If in Step 2 you assigned *both* TRVs and a pure external Temperature Sensor, you will be asked if you want to assign a `Local Temperature Calibration` entity to each TRV (for the mathematical offset injection).
   - **Step 4 (More Zones)**: Choose whether to add another zone or proceed to global settings.
   - **Step 5 (Global Calendar)**: Select the Local Calendar entity you created in the prerequisite step. Leave blank if you don't want to use calendar scheduling.
   - **Step 6 (Weather Compensation)**: Select an optional outdoor sensor (physical or `weather` domain) to enable the Feed-Forward heating curve.
   - **Step 7 (Geofencing)**: Select an optional presence sensor (`binary_sensor` or `device_tracker` or `zone`) and choose the target presets for when you leave or return home.
   - **Step 8**: Confirm and finish.

---

## 🧠 Zone Intelligence & Hardware Aggregation

In the modular architecture, a **Zone** is a powerful virtual aggregator:

- **Pure TRV Room**: Assign one or multiple TRVs to the zone. The zone averages their temperatures and syncs their setpoints.
- **Relay / Underfloor Room**: Assign a simple relay switch and a temperature sensor. The zone automatically acts as a virtual thermostat, computing PID and driving the relay via PWM!
- **Proportional / 0-10V Analog Actuators**: Assign motorized valves or 0-10V DAC/dimmer modules (e.g. Shelly Dimmer 0-10V, ESPHome). The zone maps the calculated PID demand (0-100%) directly into opening percentage or analog voltage (0-10V), bypassing PWM clicking completely!
- **Direct-Pin TRVs**: TRVs that expose an internal valve opening percentage or `valve` entity can be driven directly via the Proportional Valves section for continuous micro-regulation without local setpoint fighting.
- **Hybrid TRV + External Sensor**: Assign your TRVs AND a pure external temperature sensor. The zone intercepts the TRVs and injects a fake target (or a dynamic calibration offset) to force the physical TRV to align with the pure external sensor, bypassing the TRV's inaccurate internal thermometer!

---

## Entities Created

> **Note:** Entity IDs are assigned by Home Assistant based on the entity's unique ID and device name. The actual IDs may differ slightly from the examples below. Always copy the exact entity ID from **Settings → Devices & Services → Multizone Thermostat** or from the entity's settings page.

| Entity (example ID) | Platform | Description |
|----------------------|----------|-------------|
| `switch.master_control_heating_master` | Switch | Master on/off for the entire heating system |
| `switch.master_control_anti_seize_summer_protection` | Switch | Global toggle for the Summer Anti-seize protection |
| `switch.master_control_anti_frost_protection` | Switch | Emergency frost protection toggle |
| `switch.time_geofencing_geofencing` | Switch | Geofencing automation toggle |
| `switch.time_geofencing_auto_night_mode` | Switch | Automated night mode toggle |
| `switch.zone_modes_sync_controlli_fisici_[zone]` | Switch | Bidirectional physical TRV button synchronization toggle |
| `switch.zone_modes_apporto_passivo_[zone]` | Switch | Passive heat intake toggle (fancoils without valves / mezzanines) |
| `select.zone_modes_[zone]_mode` | Select | Per-zone mode selector (`primary`, `secondary`, `bypass`) |
| `select.master_control_global_preset` | Select | Global preset selector (`manual`, `eco`, `comfort`, `sleep`, `away`) |
| `number.master_control_min_cycle_on` | Number | Minimum boiler ON time (minutes, default: 5) |
| `number.master_control_min_cycle_off` | Number | Minimum boiler OFF time (minutes, default: 5) |
| `number.master_control_valve_delay` | Number | Valve opening delay before boiler starts (seconds, default: 0) |
| `number.master_control_anti_seize_idle_days` | Number | Idle days before triggering Anti-seize exercise (default: 15) |
| `number.master_control_anti_seize_duration` | Number | Duration in minutes of Anti-seize exercise (default: 2) |
| `number.master_control_weather_curve` | Number | Outdoor weather compensation curve multiplier (default: 0.0) |
| `number.master_control_anti_frost_temperature` | Number | Emergency anti-frost target temperature threshold (default: 7.0°C) |
| `time.time_geofencing_morning_time` | Time | Morning comfort transition time |
| `time.time_geofencing_night_time` | Time | Night sleep transition time |
| `binary_sensor.master_control_plant_anomaly` | Binary Sensor | Plant-wide anomaly detection indicator |
| `binary_sensor.heating_zones_[zone]_anomaly` | Binary Sensor | Per-zone heating circuit anomaly indicator |
| `sensor.master_control_stato_salute_impianto` | Sensor | Overall heating plant health score (0-100%) |
| `sensor.master_control_frequenza_accensioni_caldaia` | Sensor | Boiler hourly ignition cycle frequency |
| `sensor.master_control_ore_funzionamento_caldaia_24h` | Sensor | Boiler cumulative runtime in the last 24h |
| `sensor.multizone_brain_[zone]_fabbisogno` | Sensor | Real-time zone PID heat demand (0-100%) |
| `sensor.multizone_brain_[zone]_autotuning` | Sensor | Self-learning PID status and learned parameters |
| `sensor.multizone_brain_[zone]_velocita_riscaldamento` | Sensor | Room heating rate (°C/h) |
| `sensor.multizone_brain_[zone]_dispersione` | Sensor | Room natural cooling/dispersion rate (°C/h) |
| `sensor.multizone_brain_[zone]_inerzia_termica` | Sensor | Thermal inertia estimate (minutes) |
| `sensor.multizone_brain_[zone]_classe_energetica` | Sensor | Theoretical building energy class (A4 to G) |
| `sensor.multizone_brain_[zone]_tempo_ritenzione_termica`| Sensor | Thermal retention duration (hours to lose 1°C) |
| `sensor.multizone_brain_[zone]_dimensionamento_radiatore`| Sensor | Radiator power sizing adequacy estimate |

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
- Change boiler mode or entity (Relay vs OpenTherm settings)
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

1. Enable the `switch.master_control_anti_seize_summer_protection` entity.
2. The system tracks the exact time since the heating was last turned on.
3. If the system remains completely idle for the configured number of days (`number.master_control_anti_seize_idle_days`, default 15 days), the integration will:
   - Save the current state of all zones.
   - Force all zones that have the anti-seize feature enabled to turn ON (opening their valves).
   - Wait for the configured valve opening delay.
   - Wait for the configured duration (`number.master_control_anti_seize_duration`, default 2 minutes).
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

---

## 🐕 Sensor Timeout Watchdog & TRV Fallback (P1)

External wireless thermometers (Zigbee, BLE, Wi-Fi) can run out of battery, drop off the mesh network, or freeze up. When this happens, a traditional thermostat risks staying permanently stuck in heating (burning fuel) or permanently off (freezing the room).

Multizone Thermostat includes an **active sensor watchdog**:
- **Configurable Timeout**: Set `sensor_timeout_min` per zone (default: 60 minutes; set to `0` to disable).
- **Graceful Fallback**: If the external temperature sensor doesn't report a new state for longer than the timeout period (or goes `unavailable` / `unknown`), the zone automatically falls back to reading the internal temperature sensor of the assigned TRV(s).
- **Safety Mode**: TRV calibration offsets and fake target injections are suspended while fallback is active, ensuring the TRV modulates safely based on its local reading.
- **Trace & Telemetry**: When fallback triggers, a `SENSOR_TIMEOUT_FALLBACK` event is recorded in the diagnostics history, and `safety_fallback_active: true` is set in the zone's thermostat attributes.
- **Automatic Recovery**: The instant the external thermometer resumes broadcasting valid temperature readings, the zone automatically disengages fallback mode and returns to normal high-precision operation.

---

## 🔥 OpenTherm Telemetry, Fault Codes & DHW Priority

When OpenTherm mode is enabled, the integration does more than just modulate water temperature — it turns Home Assistant into a boiler supervision station:

### Telemetry Auto-Discovery
The integration automatically queries the OpenTherm gateway and exposes:
- **Water Pressure (`water_pressure`)**: Measured in Bar. The diagnostic supervisor alerts if water pressure drops below 0.8 Bar (low circuit pressure warning).
- **Return Temperature (`return_temperature`)**: Flow and return temperature monitoring allows calculating the exact $\Delta T$ of the hydraulic distribution system.
- **Flame Active (`flame_active`)**: Real-time binary indicator showing whether the burner flame is physically ignited.
- **Modulation Level (`modulation_level`)**: Current burner modulation percentage (0-100%).
- **Boiler Fault Code (`fault_code`)**: Direct capture of boiler error codes transmitted over the OpenTherm bus, eliminating the need to physically check the boiler panel.

### Domestic Hot Water (DHW) Priority Freeze
When a tap or shower is running, modern combination boilers prioritize Domestic Hot Water production over central heating. 
During this time:
1. The coordinator detects DHW production (`is_dhw_active: true`).
2. Zone PID demand calculations are **frozen** (holding the previous integral state) so the integration does not falsely assume radiators are failing to warm the rooms.
3. False "stuck valve" or "heating anomaly" alarms are suppressed.
4. The boiler status reason cleanly displays: `HOLD_DHW - Priorità Acqua Calda Sanitaria attiva`.
5. Once DHW draw-off finishes, central heating resumes immediately without integral windup overshoot.

---

## 🔋 Universal Battery Monitoring & Diagnostics

Managing wireless thermostats and radiator valves across multiple rooms requires clear visibility over battery health:
- **Automatic Discovery**: The integration resolves battery levels automatically across Zigbee2MQTT, ZHA, and Tuya/Avatto devices without requiring manual sensor mapping.
- **Zone Thermostat Attributes**: Every zone thermostat entity exposes `battery_level` in its `extra_state_attributes` (reflecting the lowest battery among the zone's external thermometer and TRVs).
- **Diagnostic Dashboard Card**: The `ZoneEnergyCard` displays real-time battery percentage and color-coded status icons:
  - 🟢 **> 80%**: Optimal battery health (`mdi:battery`)
  - 🟡 **40% - 80%**: Normal operation (`mdi:battery-50`)
  - 🟠 **15% - 40%**: Low battery warning (`mdi:battery-20`)
  - 🔴 **< 15%**: Critical alert (`mdi:battery-alert`)
- **Proactive Anomaly Prevention**: Low-battery devices are flagged early in diagnostics before sensor dropouts cause room temperature disruptions.
