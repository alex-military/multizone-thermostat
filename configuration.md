# Configuration & Documentation

[⬅️ Back to Main Readme](README.md) • [🌿 Hybrid Plant, Split AC & Energy Guide](hybrid_and_energy.md) • [🎨 Cards Guide](cards.md)

> [!TIP]
> 📖 **Interactive Multilingual Wiki Available!**  
> For the complete step-by-step documentation, collapsible configuration flows, settings map, and live simulator, visit:  
> - 🇬🇧 **[English Documentation Wiki](docs/wiki/index.html#/setup_wizard)**
> - 🇮🇹 **[Wiki Documentazione in Italiano](docs/wiki/index.html#/it/setup_wizard)**  
> - 🎮 **[Interactive 3-Dashboard Live Simulator](docs/wiki/index.html#/simulator_view)**

Everything you need to know to set up, configure, and understand how the Multizone Thermostat integration works.

> [!IMPORTANT]
> **Phase 11 (v6.1.0-beta)** adds bivalent central plant configuration (Gas Boiler + Central Heat Pump), per-zone Room Split AC management with real sensor injection, off-grid solar surplus & battery protection, and seasonal dual-track regulation.

---

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
   - **Step 1 (Central Generators Selection)**: Choose whether your home has a **Gas / Fuel Boiler**, a **Central Hydronic Heat Pump (PDC)**, or **Both** (Bivalent Hybrid Plant). You can also configure a pure Full-Electric installation (Heat Pump only).
   - **Step 1a (Gas Boiler Configuration)**: Choose between **Relay (ON/OFF PWM)** or **OpenTherm (Modulating)**.
     - *Relay*: select your central boiler relay / circulator switch.
     - *OpenTherm*: select your OpenTherm gateway entity (`climate`, `water_heater`, or `number`), optional CH enable switch, and Min/Max water flow temperatures (e.g. 35°C – 75°C).
   - **Step 1b (Central Heat Pump Configuration)**: Select control interface:
     - `climate`: Modulates flow temperature and switches between `heat`/`cool`/`off`.
     - `switch`: Contact dry relay / Smart Grid Ready (SG-Ready) activation.
     - `opentherm`: Modulating OpenTherm bus drive.
     - Configure heating temperature range (e.g. 25°C – 55°C), reversible cooling toggle (`heat_pump_cooling`), and chilled water temperature limits (e.g. 7°C – 18°C).
   - **Step 2 (Add Zone)**: Create your thermal zone through intuitive collapsible sections:
     - **Main Settings**: Name, primary Temperature Sensor, and Base Target Temperature.
     - **▶ TRVs (Standard)**: Assign smart thermostatic radiator valves (`climate`) and enable preset sync.
     - **▶ Proportional & 0-10V Valves**: Assign direct-opening actuators (`valve`, `number`) and choose scaling (**Percentage 0–100%** or **Voltage 0.0–10.0 V**).
     - **▶ Relay Actuators (PWM)**: Assign switches/relays for thermal ON/OFF actuators.
     - **▶ Room Split AC (Condizionatori Split)**:
       - Associate an air-to-air split unit (`climate.*`).
       - Set operational role: `heat_cool` (all year), `heating_only` (winter boost), `cooling_only` (summer air conditioning).
       - Enable **Bypass Sonda a Soffitto (Sensor Injection)** to overcome ceiling hot-air pooling by injecting an eye-level room sensor target.
       - Enable **Quick Heat Boost (Thermal Shock)** and configure trigger threshold ($\Delta T \ge 1.5^\circ\text{C}$).
     - **▶ Protections & Advanced**: Assign Window Sensors, adjust Sensor Watchdog Timeout, toggle Summer Anti-seize, or enable Passive Heat intake.
   - **Step 3 (TRV Calibration - Conditional)**: If you assigned *both* TRVs and a pure external Temperature Sensor, you can assign a `Local Temperature Calibration` entity to each TRV for mathematical offset injection.
   - **Step 4 (More Zones)**: Choose whether to add another zone or proceed to global settings.
   - **Step 5 (Solar Self-Consumption & Energy Management - Optional)**:
     - Enable solar energy management.
     - Select **Solar Power Sensor** (PV generation in Watts) and optional **Grid Export Sensor**.
     - Off-grid & zero-export settings: **Battery SoC Sensor** (e.g. $> 95\%$) and **Battery Power Sensor** (Watts).
     - Safeguards: **Battery Minimum Reserve SoC** (e.g. 80-85%) and **Battery Max Discharge Time** (timeout before reverting to gas).
     - External optimizer: **EMHASS / Predbat** deferred load sensor entity.
     - Operational tuning: **Compressor Minimum Run Time** (anti-chatter, default 10 min) and **Solar Overheating Offset** (thermal mass banking, $0.0^\circ\text{C} \dots +3.0^\circ\text{C}$).
   - **Step 6 (Global Calendar)**: Select your Local Calendar entity or leave blank.
   - **Step 7 (Weather Compensation)**: Select an optional outdoor sensor to enable the Feed-Forward heating curve.
   - **Step 8 (Geofencing)**: Select an optional presence sensor (`binary_sensor`, `device_tracker`, or `zone`) and configure Away/Sleep presets.
   - **Step 9**: Confirm and finish.

---

## 🧠 Zone Intelligence & Hardware Aggregation

In the modular architecture, a **Zone** is a powerful virtual aggregator:

- **Pure TRV Room**: Assign one or multiple TRVs. The zone averages their temperatures and syncs their setpoints.
- **Relay / Underfloor Room**: Assign a simple relay switch and a temperature sensor. The zone computes PID and drives the relay via PWM.
- **Proportional / 0-10V Analog Actuators**: Assign motorized valves or 0-10V DAC modules. The zone maps PID demand (0-100%) directly into opening percentage or analog voltage (0-10V).
- **Direct-Pin TRVs**: TRVs exposing an internal valve opening percentage or `valve` entity can be driven directly via proportional regulation without local setpoint fighting.
- **Room Split AC**: Individual air conditioners operate in harmony with radiators. They activate during solar surplus or quick warm-up bursts, while the system automatically suppresses hydronic gas demand to `0.0%` for that room to avoid burning fuel.
- **Hybrid TRV + External Sensor**: Assign your TRVs AND a pure external temperature sensor. The zone intercepts the TRVs and injects a dynamic calibration offset to force the physical TRV to align with the pure external sensor.

---

## Entities Created

> **Note:** Entity IDs are assigned by Home Assistant based on the entity's unique ID and device name. Always copy the exact entity ID from **Settings → Devices & Services → Multizone Thermostat**.

| Entity (example ID) | Platform | Description |
|----------------------|----------|-------------|
| `switch.master_control_heating_master` | Switch | Master on/off for the entire system |
| `switch.master_control_allow_split_heating` | Switch | Global toggle to permit or lock Split AC heating |
| `switch.master_control_allow_split_cooling` | Switch | Global toggle to permit or lock Split AC cooling |
| `switch.master_control_anti_seize_summer_protection` | Switch | Global toggle for Summer Anti-seize protection |
| `switch.master_control_anti_frost_protection` | Switch | Emergency frost protection toggle |
| `switch.time_geofencing_geofencing` | Switch | Geofencing automation toggle |
| `switch.time_geofencing_auto_night_mode` | Switch | Automated night mode toggle |
| `switch.zone_modes_sync_controlli_fisici_[zone]` | Switch | Bidirectional physical TRV button synchronization toggle |
| `switch.zone_modes_apporto_passivo_[zone]` | Switch | Passive heat intake toggle (fancoils without valves / mezzanines) |
| `select.master_control_heat_source_priority` | Select | Heat source priority (`auto`, `hybrid`, `combined`, `electric_only`, `gas_only`) |
| `select.master_control_master_operation_mode` | Select | Seasonal operation mode (`heat`, `cool`) |
| `select.master_control_global_preset` | Select | Global preset selector (`manual`, `eco`, `comfort`, `sleep`, `away`) |
| `select.master_control_demand_strategy` | Select | Demand formula (`max`, `weighted_average`, `sum_capped`) |
| `select.zone_modes_[zone]_mode` | Select | Per-zone mode selector (`primary`, `secondary`, `bypass`) |
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

## 🎛️ Heat Source Priorities Explained

The priority selector (`select.master_control_heat_source_priority`) controls how gas and electric generators cooperate:

1. **`auto`**: The gas boiler covers baseline heating. Whenever free solar surplus is detected, or EMHASS/Predbat calls for boost, or a cold room triggers Quick Boost ($\Delta T \ge 1.5^\circ\text{C}$), splits and heat pumps engage.
2. **`hybrid`**: Rooms with splits use electric heating **only when solar surplus is available**. If solar power is insufficient, they seamlessly fall back to hydronic heating, preserving household batteries.
3. **`combined`**: Gas boiler maintains hydronic baseline, while the Heat Pump and Splits kick in during Solar Surplus or Thermal Shock for accelerated warm-up.
4. **`electric_only`**: Zero gas consumption. Caldaia locked at 0%. 100% of demand is directed to the Heat Pump and Room Splits.
5. **`gas_only`**: Electric splits and heat pumps are turned off in heating mode; all heating is delivered via hydronics and gas.

---

## 🔄 Dual-Track Seasonal Operation (Heat & Cool)

Commutating between Winter and Summer is done via the **Caldo 🔥 / Freddo ❄️** master slider:
- **Dual-Track Presets**: Presets (*Comfort, Eco, Sleep, Away, Manual*) maintain completely separate target temperature memories for heating (`presets_heat`) and cooling (`presets_cool`).
- **Dual-Track PID Loops**: The system automatically switches between independent winter PID gains (`_pids_heat`) and summer cooling PID gains (`_pids_cool`), ensuring stable regulation despite asymmetric heat exchange properties.
- **Passive Cooling Autotuner**: Tunes PID gains automatically using Ziegler-Nichols reaction curves observed during natural room cooling.
- **Dashboard Summer Filter**: Rooms without cooling capability (no split and no reversible heat pump) automatically hide their cards in summer to keep the dashboard clean.

---

## Options (Post-Installation)

Go to **Settings → Devices & Services → Multizone Thermostat → Configure** to:
- Change plant generators (Gas Boiler, Heat Pump, Reversible Cooling)
- Configure Solar Self-Consumption, Battery Safeguards, and EMHASS/Predbat bridge
- Edit Global Calendar (change or remove the calendar entity)
- Edit Weather Compensation (change or remove outdoor sensor)
- Change presence sensor for geofencing
- Add a new zone
- Remove a zone
- Edit a zone (Room Split AC, TRV preset sync, Window Sensor, Anti-seize, Sensor Watchdog, Passive Heat)
