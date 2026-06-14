# Multizone Thermostat — Home Assistant Custom Integration

A custom integration for Home Assistant that provides **multi-zone heating management** with **centralized boiler control**. No YAML scripting or manual automations required — everything is configured through the HA UI.

## Features

- 🖥️ **100% UI Config Flow** — Setup wizard: select your boiler relay and add zones directly from the HA interface
- 🔘 **Master Switch** — One switch to enable/disable the entire heating system
- 🏠 **Per-Zone Switches** — Individual switches for each room/zone, persistent across restarts
- 🔥 **Automatic Boiler Control** — Boiler turns ON when any zone is heating, OFF when all zones are idle
- 🛡️ **Boiler Protection** — Native `number` entities for anti-short-cycle (min cycle on/off) and valve opening delay
- 🪟 **Window Sensor Detection** — Automatically bypass zones when a window is opened, and restore them when closed
- 🌡️ **Virtual Thermostats** — Create virtual thermostat entities directly from the UI by combining a temperature sensor and a heater switch — no YAML needed
- 🔄 **TRV Preset Sync** — Optional per-zone preset synchronization for physical TRV valves
- ⚙️ **Options Flow** — Add/remove zones and virtual thermostats, change window sensors and settings after installation
- 🎨 **3 Custom Lovelace Cards** — Master status card, circular dial card, and compact button card — all auto-registered

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

| Entity | Description |
|--------|-------------|
| `switch.multizone_master` | Master on/off for the entire heating system |
| `switch.multizone_zone_[zone_name]` | Per-zone on/off switch (one per configured zone) |
| `climate.multizone_thermostat_vt_[name]` | Virtual thermostat entity (only if created via the UI) |
| `number.multizone_min_cycle_on` | Minimum boiler ON time (minutes, default: 5) |
| `number.multizone_min_cycle_off` | Minimum boiler OFF time (minutes, default: 5) |
| `number.multizone_valve_delay` | Valve opening delay before boiler starts (seconds, default: 0) |

## How It Works

```
Master Switch ON
    └── Zone Switch ON  → climate.set_hvac_mode(heat)
    └── Zone Switch OFF → climate.set_hvac_mode(off)

Master Switch OFF
    └── ALL zones → climate.set_hvac_mode(off)
    └── Boiler   → switch.turn_off() (ignores min_cycle_on for safety)

Any zone hvac_action = heating
    └── If valve_delay > 0, wait for delay
    └── If boiler was recently off, wait for min_cycle_off
    └── Boiler ON

All zones hvac_action = idle/off
    └── If boiler was recently on, wait for min_cycle_on
    └── Boiler OFF
    
Window Opened
    └── Zone Switch turns OFF automatically (bypassed) and saves state
Window Closed
    └── Zone Switch restores previous state

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

This integration includes three custom Lovelace cards to control your heating zones and view the central heating status directly in your Home Assistant dashboards. The cards are **auto-registered** — no manual resource configuration needed.

### 1. Central Heating Status Card (`custom:multizone-thermostat-status-card`)
A zero-configuration, button-style card that displays the status of the central heating master switch. It changes color and icon dynamically depending on the state of the Master Switch and the Boiler/Circulator:
- **Grey (Off)**: The master heating system is disabled.
- **Yellow (Standby)**: The master heating system is enabled, but no zone is currently calling for heat (boiler is idle).
- **Orange (Heating)**: The master heating system is enabled, and at least one zone is calling for heat (boiler is active).

#### States
| Off | Standby (Idle) | Active Heating |
|---|---|---|
| ![Master Off](images/status_off.png) | ![Master Standby](images/status_idle.png) | ![Master Heating](images/status_heating.png) |

---

### 2. Dial Thermostat Card (`custom:multizone-thermostat-dial-card`)
Wraps the native Home Assistant circular thermostat card and adds a built-in toggle switch to easily enable or exclude (bypass) the zone.
- **Enabled**: Displays the interactive dial to adjust temperature.
- **Disabled**: Dims the dial and overlays a clean "Zone Excluded / Bypassed" message.

#### States
| Enabled | Excluded (Bypassed) |
|---|---|
| ![Dial Enabled](images/dial_enabled.png) | ![Dial Disabled](images/dial_disabled.png) |

---

### 3. Button Thermostat Card (`custom:multizone-thermostat-button-card`)
A compact button-based thermostat card designed for spaces where a circular dial is too large. It includes temperature controls (`+` / `-`), current and target temperature displays, HVAC mode selectors, and the zone enable/exclude switch.
- **Enabled**: Fully interactive controls.
- **Disabled**: Dims the controls and displays a "Zone Excluded / Bypassed" overlay.

#### States
| Enabled | Excluded (Bypassed) |
|---|---|
| ![Button Enabled](images/button_enabled.png) | ![Button Disabled](images/button_disabled.png) |

---

### Card Configuration

#### Status Card (Zero-Config)
The status card requires zero configuration because it automatically detects your Master Switch:
```yaml
type: custom:multizone-thermostat-status-card
```

#### Dial Thermostat Card
```yaml
type: custom:multizone-thermostat-dial-card
entity: climate.living_room                    # Your climate entity (or virtual thermostat)
switch: switch.multizone_zone_living_room      # (Optional) The bypass switch for this zone
title: Living Room                             # (Optional) Custom title
```

#### Button Thermostat Card
```yaml
type: custom:multizone-thermostat-button-card
entity: climate.living_room                    # Your climate entity (or virtual thermostat)
switch: switch.multizone_zone_living_room      # (Optional) The bypass switch for this zone
title: Living Room                             # (Optional) Custom title
```

> **Note**: If you installed via HACS, the Lovelace card resource is registered automatically. If cards don't appear, add the resource manually:
> Go to **Settings → Dashboards → Resources** → Add `/multizone_thermostat_card/multizone-thermostat-card.js` as **JavaScript Module**.

## Requirements

- Home Assistant 2024.x or newer
- At least one `switch` entity (boiler relay/circulator)
- At least one `climate` entity (thermostat/TRV) **OR** a temperature sensor + heater switch (to create a Virtual Thermostat)
- **Note**: Currently supports only ON/OFF systems with a relay or actuator. Proportional modulation (PWM/PID) or OpenTherm will be added in future phases.

## Future Roadmap

The project is structured in phases to evolve from a simple aggregator to a full-fledged smart climate manager.

### FASE 1 — Sicurezza Impianto ✅
- [x] **Antipendolamento (`min_cycle_duration`)**: Previene oscillazioni rapide della caldaia con tempi minimi di ON/OFF (implementato via entità `number`).
- [x] **Ritardo Accensione Caldaia (`valve_opening_delay`)**: Ritardo in secondi per permettere l'apertura delle valvole termoelettriche (implementato via entità `number`).
- [x] **Rilevamento Finestra Aperta (`window_sensor`)**: Bypass automatico zona su apertura finestra, con ripristino stato precedente e persistenza su riavvio.

### FASE 2 — Evoluzione Architetturale (In Progress)
- [x] **Termostati Virtuali via UI**: Creazione automatica di entità `climate` da un sensore di temperatura e uno switch (es. fancoil/relè sfusi) senza YAML.
- [ ] **Preset Globali (Memoria Temperature e Bypass)**: I preset (Eco / Comfort / Sleep / Away) fungono da "scenari globali" con memoria dinamica per singola zona. 
  - Selezionando un preset, il sistema applicherà le impostazioni salvate per ogni zona.
  - Se modifichi la temperatura o attivi/disattivi il bypass di una zona mentre è attivo un preset, il sistema *ricorda* quella modifica e la salverà permanentemente per quel preset.
  - Al successivo utilizzo dello stesso preset, la zona tornerà esattamente allo stato (temperatura target e stato bypass) configurato l'ultima volta.
- [ ] **Geofencing Zero-Code**: Cambio preset automatico in base alla presenza (Away/Comfort).

### FASE 3 — Ottimizzazione Energetica Avanzata
- [ ] **Algoritmo PWM/PID Selezionabile**: Modulazione del tempo di accensione per impianti modulanti.
- [ ] **Carico Richiesto Globale (%)**: Sensore percentuale del fabbisogno termico per pompe di calore.
- [ ] **Curva Climatica Integrata**: Ottimizzazione temperatura di mandata basata sul meteo esterno.
- [ ] **Antigrippaggio Estivo**: Attivazione periodica delle valvole in estate per prevenire blocchi.

## License

This project is licensed under the MIT License.
