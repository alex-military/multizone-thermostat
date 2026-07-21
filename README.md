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

## Configuration & Documentation

The Multizone Thermostat is 100% configured via the Home Assistant UI, without needing any YAML. 
It supports advanced features like Geofencing, Virtual Thermostats, and Zone Priorities.

👉 **[Click here to view the full Configuration Guide, Setup Instructions, and System Logic](configuration.md)**

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

- 🛡️ **Boiler & Valve Protection** — Native `number` entities for anti-short-cycle, valve opening delay, and **Summer Anti-seize protection**

### PHASE 3 — Quality of Life & Dashboards (Completed) ✅
- [x] **Summer Valve Protection (Anti-seize)**: Cyclical safety activation during summer to prevent mechanical seizing of valves and circulator pumps. Includes global toggle, custom interval/duration settings, and per-zone exclusion.
- [x] **Auto-Generated Lovelace Dashboard**: The integration automatically generates (and keeps updated) a full Home Assistant dashboard page with premium climate-dedicated graphics, including all our custom cards — zero-code required. Supports dynamic grid sizing (columns).

### PHASE 4 — Advanced Energy Optimization
- [ ] **Self-Learning PID Auto-Tuning**: Advanced self-learning PID algorithm that studies the thermal inertia of the house and regulates proportional modulation (PWM) autonomously to eliminate temperature swings.
- [ ] **Global Heat Demand (%)**: A `sensor` entity that calculates the exact percentage of load required by the house, essential for intelligently driving Heat Pump inverters based on real load.
- [ ] **Weather Compensation Curve**: Dynamic adjustment of the heating demand (and heat pump flow temperature) based on weather forecasts and outdoor temperature.

### PHASE 5 — Total Climate Control & External AI
- [ ] **Hybrid Support (Heating / Cooling)**: Complete rewrite of the configuration engine to simultaneously manage and easily switch between Winter (Heating) and Summer (Cooling) modes, supporting reversible heat pumps.
- [ ] **External AI Integration (Predictive Optimization)**: Dedicated API/Sensors interface allowing external AIs to read historical data and constantly optimize PID parameters, weather compensation curves, and predictive geofencing. *(Note: This phase is exploratory. We need to evaluate if existing AI solutions can be integrated or if we need to develop something completely from scratch).*

## License

This project is licensed under the MIT License.
