# Multizone Thermostat Custom Lovelace Cards

[⬅️ Back to Main Readme](README.md) • [🌿 Hybrid Plant, Split AC & Energy Guide](hybrid_and_energy.md) • [⚙️ Configuration Guide](configuration.md)

> [!TIP]
> 📖 **Interactive Multilingual Wiki Available!**  
> Explore our interactive Wiki:  
> - 🇬🇧 **[English Lovelace Cards Guide](docs/wiki/index.html#/cards_guide)**
> - 🇮🇹 **[Guida Schede Lovelace in Italiano](docs/wiki/index.html#/it/cards_guide)**  
> - 🎮 **[Interactive 3-Dashboard Live Simulator](docs/wiki/index.html#/simulator_view)**

This integration includes custom Lovelace cards and auto-generated dashboard strategies to manage your multi-zone climate system, bivalent central plant, room split air conditioners, and building energy diagnostics directly in Home Assistant. The cards are **auto-registered** — no manual resource configuration is required.

> [!IMPORTANT]
> **Phase 11 (v6.1.0-beta)** introduces 1-to-1 visual twin styling matching Home Assistant's native thermostat cards, direct arc touch/click target setting, active source badges (`🔥 GAS`, `⚡ ELETTRICO`, `🔥⚡ GAS + ELETTRICO`), single-room split manual override with safety lockout, seasonal Caldo 🔥 / Freddo ❄️ presets, and constant-height segmented priority selectors.

---

## 1. Central Heating & Cooling Status Card (`custom:multizone-thermostat-status-card`)
A zero-configuration, button-style card that displays the real-time status of the central plant master switch and generator staging:
- **Dynamic Color Aura**:
  - **Grey (Off)**: System disabled.
  - **Yellow (Standby)**: Enabled, but all zones satisfied (circulators and burners idle).
  - **Orange (Heating)**: Central boiler or electric heating active.
  - **Cyan/Celeste (Cooling)**: Central heat pump or room split cooling active.
- **Generator Telemetry Subtitle**:
  - `Caldaia: ON` / `Caldaia: ON + Split` / `Split Elettrico: ON` / `Zone attive: X`.

```yaml
type: custom:multizone-thermostat-status-card
```

---

## 2. Dial Thermostat Card (`custom:multizone-thermostat-dial-card`)

A modern circular thermostat designed as a **1-to-1 Visual Twin** of the native Home Assistant thermostat card, with extensive enhancements for multi-zone and bivalent systems:

### Key Enhancements (v6.1.0-beta)
- **1-to-1 Geometry**: Design disponibile in stile Luxury e Classic perfettamente integrato in Home Assistant.
- **Direct Arc Click / Touch**: Click or tap anywhere along the circular arc to immediately set the desired target temperature without needing to drag the handle.
- **Circular Step Buttons `[-]` and `[+]`**: Ergonomic 42px diameter buttons positioned symmetrically in the bottom dial opening to adjust temperature by 0.5°C steps.
- **Clean Title Case & Comma Formatted**: Displays clean status text ("Riscaldamento", "Spento", "In attesa") and Italian/European comma decimals (e.g. `21,5 °C` and `19,5 °C`).
- **Active Source Badge (Top Left)**:
  - `🔥 GAS` (Orange): Zone heated by the central gas boiler.
  - `⚡ ELETTRICO` (Cyan): Zone heated or cooled by the room split AC.
  - `🔥⚡ GAS + ELETTRICO` (Amber): Combined operation with gas radiators and electric split working together.
- **Room Split AC Manual Run Button (Header Center)**:
  - Posizionato al centro matematico della card per le stanze con climatizzatore split associato.
  - **Master OFF**: Allows running the split air conditioner independently for that room without turning on the gas boiler.
  - **Master ON (Safety Lockout)**: Automatically disables clicks when central heating is ON to prevent conflicts with whole-house orchestration.
- **Automatic Summer Filtering (`hide_if_cannot_cool: true`)**: Automatically hides zones that do not have cooling capability when the system switches to summer mode.
- **Zone Mode Selector**: Cycle between `Primaria`, `Secondaria`, and `Bypassata` with a single touch.

```yaml
type: custom:multizone-thermostat-dial-card
entity: climate.multizone_thermostat_salone
title: Salone
```

---

## 3. Button Thermostat Card (`custom:multizone-thermostat-button-card`)
A compact button-based thermostat card designed for dense dashboard grids where a circular dial is too large:
- Includes temperature step controls (`+` / `-`), current and target temperature displays, HVAC modes, and zone mode selector.
- Features active source badges (`🔥 GAS`, `⚡ ELETTRICO`, `🔥⚡ GAS + ELETTRICO`).
- Shows orange aura during heating and cyan aura during cooling.

```yaml
type: custom:multizone-thermostat-button-card
entity: climate.multizone_thermostat_camera
title: Camera Matrimoniale
```

---

## 4. Global Preset Card (`custom:multizone-thermostat-preset-card`)
A multi-function global control bar with dynamic theme styling and constant height across seasons:
- **Header All-in-One**:
  - **Left**: Segmented pill selector for **Heat Source Priority** (`Auto`, `Ibrido`, `Combinato`, `Elettrico`, `Gas`). In summer cooling mode, automatically transitions to the aesthetic pill `❄️ Raffrescamento Elettrico` with the exact same height.
  - **Right**: Master Seasonal Switch (**Caldo 🔥 / Freddo ❄️**).
- **Preset Buttons**: `Manuale`, `Eco`, `Comfort`, `Notte`, `Fuori Casa`.
- **Dual-Track Memory**: Automatically recalls winter targets (`presets_heat`) in winter and summer targets (`presets_cool`) in summer.

```yaml
type: custom:multizone-thermostat-preset-card
```

---

## 5. Weekly Scheduler Card (`custom:multizone-thermostat-scheduler-card`)
An interactive weekly scheduling interface with thermal anticipation:
- **24-Hour Timeline Matrix**: Visual timeline with color-coded preset blocks per zone.
- **Multi-Profile Management**: Fast switching between *Standard*, *Festivo / Weekend*, *Smart Working*, and custom user profiles.
- **Smart Return (Pianifica Rientro)**: Predictive arrival planner calculating thermal pre-heating times based on learned room thermal dispersion.

```yaml
type: custom:multizone-thermostat-scheduler-card
```

---

## 6. Central Plant Health Card (`custom:multizone-thermostat-plant-card`)
A glassmorphic card displaying real-time boiler and heat pump telemetry:
- **Auto-Discovery**: Automatically binds to central plant diagnostics.
- **Ignition Frequency**: Tracks burner starts per hour and warns against short-cycling wear (> 5 cycles/h).
- **OpenTherm Telemetry**: Water pressure (Bar), return temperature (°C), flame state, modulation %, and OEM fault codes.
- **Active Anomalies List**: Real-time list of mechanical issues (stuck valves, ghost heating, sensor fallback).

```yaml
type: custom:multizone-thermostat-plant-card
```

---

## 7. Zone Energy Efficiency Card (`custom:multizone-thermostat-zone-energy-card`)
Displays thermal performance and physical building metrics for each room:
- **European Energy Class (A4 → G)**: Derived from building heat loss rates and weather $\Delta T$.
- **Thermal Retention Time**: Hours required for the room to drop by $1.0^\circ\text{C}$.
- **Radiator Sizing**: Evaluation of emitter capacity (undersized, optimal, oversized).
- **Battery Health**: Universal battery indicator across Zigbee2MQTT, ZHA, and Tuya devices.
- **Interactive Toggles**: Cycle zone mode or toggle *Apporto Passivo* (passive heat intake) directly from the card.

```yaml
type: custom:multizone-thermostat-zone-energy-card
entity: climate.multizone_thermostat_salone
```

---

## 8. Auto-Generated Dashboard Strategies

### Thermostats View Strategy (`custom:multizone-thermostat-dashboard`)
Automatically builds a complete responsive climate dashboard with presets, master controls, and zone cards without writing YAML for individual entities:

```yaml
views:
  - title: Clima
    path: clima
    icon: mdi:thermostat
    strategy:
      type: custom:multizone-thermostat-dashboard
      columns: 3 # (Optional: 1, 2, 3, or 4 columns)
```

### Diagnostics View Strategy (`custom:multizone-thermostat-diagnostics`)
Generates a complete building efficiency and plant health view for all zones:

```yaml
views:
  - title: Diagnostica
    path: diagnostica
    icon: mdi:chart-box-outline
    strategy:
      type: custom:multizone-thermostat-diagnostics
      columns: 3
```
