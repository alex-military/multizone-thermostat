# Multizone Thermostat — Home Assistant Custom Integration

A custom integration for Home Assistant that provides **multi-zone heating management** with **centralized boiler control**. No YAML scripting or manual automations required — everything is configured through the HA UI.

## Features

- 🖥️ **100% UI Config Flow** — Setup wizard: select your boiler relay and add zones directly from the HA interface
- 🔘 **Master Switch** — One switch to enable/disable the entire heating system
- 🏠 **Zone Modes (Primary/Secondary/Bypass)** — Advanced per-zone control. Primary zones trigger the boiler; Secondary zones only receive heat if the boiler is already running; Bypassed zones are excluded entirely.
- 📍 **Geofencing & Auto-Sleep** — Automatically switch to Away or Sleep presets based on home occupancy (presence sensors) or time of day.
- 🔥 **Automatic Boiler Control** — Boiler turns ON when any Primary zone is heating, OFF when all zones are idle
- 🛡️ **Boiler Protection** — Native `number` entities for anti-short-cycle (min cycle on/off) and valve opening delay
- 🪟 **Window Sensor Detection** — Automatically bypass zones when a window is opened, and restore them when closed
- 🌡️ **Virtual Thermostats** — Create virtual thermostat entities directly from the UI by combining a temperature sensor and a heater switch — no YAML needed
- 🔄 **TRV Preset Sync** — Optional per-zone preset synchronization for physical TRV valves
- ⚙️ **Options Flow** — Add/remove zones and virtual thermostats, change window sensors and settings after installation
- 🎨 **4 Custom Lovelace Cards** — Master status card, circular dial card, compact button card, and global preset card — all auto-registered

## Installation

### Via HACS (recommended)
1. Open **HACS** from the sidebar
2. Go to **Integrations**, click the 3-dot menu (top right) → **Custom repositories**
3. Add `https://github.com/alex-military/multizone-thermostat` with category **Integration**
4. Search for **"Multizone Thermostat"** in HACS and click **Download**
5. Restart Home Assistant

### Manual
1. Copy the `custom_components/multizone_thermostat` folder to your HA `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **"Multizone Thermostat"**
3. Follow the setup wizard:
   - **Step 1**: Select your boiler switch/relay entity
   - **Step 2**: Choose zone type — **existing thermostat** or **create a virtual thermostat**
   - **Step 3**: Configure the zone (name, optional window sensor, optional TRV sync)
   - **Step 4**: Add more zones or confirm and finish

### Creating a Virtual Thermostat

If you don't have a pre-existing `climate` entity (e.g., you have a standalone temperature sensor and a relay/switch controlling a fancoil, radiator valve, or underfloor heating), you can create a **Virtual Thermostat** directly from the wizard:

1. In the "Choose zone type" step, select **"Create virtual thermostat"**
2. Fill in:
   - **Zone Name**: A friendly name for the zone (e.g., "Camera", "Studio")
   - **Temperature Sensor**: The `sensor` entity that reads the room temperature (must have `device_class: temperature`)
   - **Heater Switch**: The `switch` entity that controls the heater/relay in that zone
   - **Target Temperature**: Initial target temperature (default: 20°C)
   - **Tolerance**: Hysteresis in °C (default: 0.5°C) — the heater turns ON when temperature drops below `target - tolerance`, and turns OFF when it rises above `target + tolerance`
   - **Window Sensor** _(optional)_: A `binary_sensor` to auto-bypass the zone when a window is open
3. The integration will automatically create a `climate` entity and register it as a zone

Virtual thermostats can also be created **after installation** from the Options menu.

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

## Options (Post-Installation)

Go to **Settings → Devices & Services → Multizone Thermostat → Configure** to:
- Change the boiler switch
- Add a new zone (existing thermostat)
- Create a new virtual thermostat (sensor + switch → climate entity)
- Remove a zone
- Remove a virtual thermostat (removes both the climate entity and the associated zone)
- Edit a zone (TRV preset sync, Window Sensor)

## TRV Preset Sync

When enabled for a zone, the integration automatically syncs the TRV preset mode:
- HVAC mode `heat` → preset `manual`
- HVAC mode `off` → preset `off`

Only enable this for zones with physical TRV valves that support preset modes.

## Lovelace Cards

This integration includes four custom Lovelace cards to control your heating zones, presets, and view the central heating status directly in your Home Assistant dashboards. The cards are **auto-registered** — no manual resource configuration needed.

👉 **[Click here to view the documentation and screenshots for the Custom Lovelace Cards](cards.md)**

## Requirements

- Home Assistant 2024.x or newer
- At least one `switch` entity (boiler relay/circulator)
- At least one `climate` entity (thermostat/TRV) **OR** a temperature sensor + heater switch (to create a Virtual Thermostat)
- **Note**: Currently supports only ON/OFF systems with a relay or actuator. Proportional modulation (PWM/PID) or OpenTherm will be added in future phases.

## Future Roadmap

The project is structured in phases to evolve from a simple aggregator to a full-fledged smart climate manager.

### PHASE 1 — System Safety ✅
- [x] **Anti-short Cycle (`min_cycle_duration`)**: Prevents rapid boiler oscillations with minimum ON/OFF times (implemented via `number` entities).
- [x] **Boiler Ignition Delay (`valve_opening_delay`)**: Delay in seconds to allow thermoelectric valves to open fully before firing the boiler (implemented via `number` entity).
- [x] **Open Window Detection (`window_sensor`)**: Automatic zone bypass upon window opening, with state restoration and persistence across restarts.

### PHASE 2 — Architectural Evolution (In Progress)
- [x] **Virtual Thermostats via UI**: Automatic creation of `climate` entities from a temperature sensor and a simple switch (e.g., bare relays) without YAML.
- [x] **Global Presets (Dynamic Memory)**: Presets (Manual / Eco / Comfort / Sleep / Away) act as "global scenes" with dynamic memory per individual zone. 
  - Selecting a preset applies the saved settings for each zone.
  - Modifying the temperature or bypass state of a zone while a preset is active permanently saves that change to the current preset.
  - Upon subsequent selection of the same preset, the zone accurately returns to its previously configured state (target temp and bypass).
- [x] **Quick Preset Card**: A dedicated custom Lovelace card for quick and centralized global preset selection.
- [x] **Geofencing Zero-Code**: Automatic preset switching based on home occupancy (Away/Comfort).
- [x] **Room Priority Selector**: Replace the zone bypass switch with a multi-state selector (Primary / Secondary / Bypassed). *Primary* zones can turn on the boiler; *Secondary* zones can open their valves to receive heat but cannot turn on the boiler; *Bypassed* zones are excluded entirely.

### PHASE 3 — Advanced Energy Optimization & AI
- [ ] **PID Auto-Tuning**: Advanced self-learning PID algorithm that studies the thermal inertia of the house and regulates proportional modulation (PWM) autonomously to eliminate temperature swings.
- [ ] **External AI Integration (Predictive Optimization)**: Dedicated API/Sensors interface allowing external AIs to read historical data and constantly optimize PID parameters, weather compensation curves, and predictive geofencing.
- [ ] **Weather Compensation Curve**: Dynamic adjustment of the heating demand (and heat pump flow temperature) based on weather forecasts and outdoor temperature.
- [ ] **Global Heat Demand (%)**: A `sensor` entity that calculates the exact percentage of load required by the house, essential for intelligently driving Heat Pump inverters based on real load.

### PHASE 4 — Total Climate Control & Auto-Generated Dashboards
- [ ] **Hybrid Support (Heating / Cooling)**: Complete rewrite of the configuration engine to simultaneously manage and easily switch between Winter (Heating) and Summer (Cooling) modes, supporting reversible heat pumps.
- [ ] **Auto-Generated Lovelace Dashboard**: The integration will automatically generate (and keep updated) a full Home Assistant dashboard page with premium climate-dedicated graphics, including all our custom cards — zero-code required.
- [ ] **Summer Valve Protection (Anti-seize)**: Cyclical safety activation during summer to prevent mechanical seizing of valves and circulator pumps.

## License

This project is licensed under the MIT License.
